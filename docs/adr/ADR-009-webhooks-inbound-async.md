# ADR-009 : Webhook de paiement entrant traité en asynchrone (Celery + Redis)

* **Statut** : Accepté
* **Contexte** : Phase 12 (Webhooks, paiement simulé)

## 1. Contexte & Problématique

Un prestataire de paiement externe prévient notre système qu'un paiement a abouti. Contrairement à tous les échanges déjà construits dans ce projet, le sens est inversé : c'est lui qui nous appelle, et il ne connaît pas notre API.

Trois propriétés rendent ce flux différent du reste :

* **Il est déclenché par un tiers.** Le message n'est pas la suite d'une action de l'utilisateur, il arrive quand le prestataire veut. On ne maîtrise ni son rythme, ni sa disponibilité, ni son nombre de redeliveries.
* **Sa livraison est en at-least-once.** Tout prestataire redélivre tant qu'il n'a pas reçu un accusé de réception. Le même webhook arrivera donc deux fois, dix fois, et il faut que le crédit n'ait lieu qu'une fois.
* **Il porte de l'argent.** Une notification manquée est gênante, un crédit perdu ou doublé est un incident comptable.

Le flux sortant (nous notifions un service externe) n'est pas traité ici, il arrive en phase 17 avec le retry, le backoff et la dead-letter.

## 2. Décisions prises

### A. Le webhook est authentifié par signature HMAC, pas par jeton

* Le message est authentifié par un HMAC-SHA256 calculé sur le timestamp signé concaténé au corps brut (`X-Signature`, `X-Timestamp`).
* La comparaison utilise `compare_digest`, et la clé vient des settings, jamais du corps.
* Le timestamp signé est vérifié avec une tolérance de 5 minutes. **Signer le timestamp et pas seulement le corps est ce qui bloque le rejeu** : une signature valide rejouée plus tard est refusée.
* Un rejeu reçoit un 4xx et jamais un 5xx : un 5xx ferait redéliver indéfiniment un message qu'on refuse à dessein.

### B. La vue valide et empile, le traitement part en file

* La vue vérifie la signature, valide le corps, enregistre le paiement en `PENDING`, poste un message dans la file, et répond 200. Elle ne crédite rien.
* Le 200 signifie « j'ai pris votre message », pas « j'ai fini le traitement ». C'est la seule lecture que le contrat du prestataire permet de donner.
* Un doublon reçoit aussi un 200, avec `duplicate: true`, et ne réempile rien : sinon chaque redelivery ferait grossir la file de travaux déjà faits.

### C. Le traitement asynchrone est fait par Celery sur Redis, dans un autre processus

* La tâche `payment.process` vit dans un processus séparé du serveur web, alimenté par Redis.
* Celery ne fait qu'un seul triggering côté `interfaces/` : le use case reste une fonction Python pure, il n'importe rien de Celery.
* La file survit à un crash du serveur web. Un paiement reçu mais pas encore traité est déjà dans Redis, donc récupérable.

### D. L'idempotence est garantie à trois niveaux

* `provider_ref` porte une contrainte d'unicité en base, plus une vérification applicative. La base est le seul endroit qui peut départager deux exécutions concurrentes.
* Le changement de statut passe par un compare-and-set : le `WHERE` porte sur le statut attendu, donc deux tâches concurrentes ne peuvent pas confirmer deux fois le même paiement.
* Le crédit passe par `CreditWalletUseCase` avec `payment:<provider_ref>` comme clé d'idempotence, qui réutilise la règle du ledger. C'est le point de vérité unique annoncé dans le contrat.

On ne prétend pas à l'exactly-once : on fait de l'at-least-once plus une opération idempotente, et c'est le seul modèle que Redis et PostgreSQL savent garantir honnêtement.

### E. Une redelivery d'un paiement déjà réglé est un succès, pas une erreur

* Si le paiement est déjà dans l'état demandé, la tâche ne fait rien et réussit.
* Lever une erreur ici serait une faute : la tâche échouerait pour toujours, donc la phase 17 la retenterait indéfiniment et noierait la dead-letter de messages dont l'état recherché est déjà atteint.
* En revanche, une décision qui contredit l'état enregistré est une vraie anomalie, et elle remonte en erreur : le prestataire et nous ne sommes pas d'accord sur l'état du paiement, il faut le savoir.

## 3. Alternatives considérées

* **Créditer directement dans la vue** : Rejetée. Le temps de traitement est à la merci du prestataire, qui timeoute et redélivre. Le 200 doit être rapide et inconditionnel.
* **`asyncio.create_task` dans le processus Django** : Rejetée. La tâche vit en mémoire ; si le process meurt entre l'accusé de réception et le crédit, le paiement est perdu. Un crédit de portefeuille perdu n'est pas acceptable, et il n'y aurait rien sur quoi bâtir le retry de la phase 17.
* **Une interface `TaskQueue` abstraite dans `application/`** : Reportée. Aucun use case n'a besoin d'enqueuer du travail lui-même, Celery n'est qu'un triggering côté `interfaces/`. Une abstraction de plus ne résout aucun problème réel aujourd'hui ; elle s'écrira le jour où un use case devra déclencher une tâche.
* **Une file maison sur Redis** : Rejetée. Celery est déjà une file de tâches éprouvée, battle-tested, avec la sérialisation, le routage et la supervision. Réécrire une partie de cela dans un projet pédagogique n'apprend rien.
* **Un outbox pattern en base** : Reportée. Plus transactions et plus solide sur l'envoi sortant, mais ce problème n'existe pas encore ici, le webhook étant entrant. C'est la bonne réponse si un jour nous devenons l'émetteur.
* **Un jeton Bearer partagé avec le prestataire** : Rejetée. Le secret transite en clair à chaque appel et peut fuiter par un log. La signature prouve l'authenticité du contenu et ne se rejoue pas.
* **mTLS ou OAuth entre le prestataire et nous** : Rejetée pour un prestataire simulé. La charge opérationnelle (certificats, rotation) serait disproportionnée ici. C'est le bon choix pour un vrai prestataire, et une place pour une ADR plus tard.

## 4. Conséquences & Bénéfices

* **Un processus de plus à lancer** : c'est le coût assumé du choix. Un `celery -A core worker` à côté du serveur web, et un déploiement qui doit le monitorer. C'est le prix de la survie au crash, payé volontairement.
* **Redis devient une dépendance dure du paiement**, alors qu'elle ne l'était que du marché temps réel. Si Redis tombe, plus aucun paiement n'est traité, alors que le marché ne fait que du confort.
* **Le 200 ne veut plus dire « crédité »**. Un prestataire satisfait peut masquer des paiements bloqués en file, donc les deux temps doivent rester distinguables : le 200 dans le log d'accès HTTP du serveur, le règlement dans les logs de la tâche Celery. Les `log` applicatifs de la vue existent déjà mais ne sortent qu'à partir du niveau configuré en phase 19 (Observabilité), le projet n'a pas encore de configuration `LOGGING`.
* **Cohérence différée** : entre le 200 et le passage de `PENDING` à `CONFIRMED`, l'état est transitoire. Un test d'intégration doit attendre le worker, il ne peut pas assérer sur le 200 seul.
* **Le webhook seul ne prouve rien**. `scripts/simulate_payment_provider.py` est rendu nécessaire pour tester la chaîne entière : sans un faux prestataire qui signe, un doublon et un rejeu, on ne teste que la moitié du chemin.
* **Le module se lit dans le code** : la vue ne fait que valider et empiler, la tâche ne fait qu'appliquer la décision, le use case porte les règles. Le sens de lecture suit le trajet du message.
