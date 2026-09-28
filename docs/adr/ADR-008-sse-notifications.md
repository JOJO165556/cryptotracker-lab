# ADR-008 : Diffusion des notifications en Server-Sent Events (SSE)

* **Statut** : Accepté
* **Contexte** : Phase 8b (Flux de notifications push)

## 1. Contexte & Problématique

Le module Notification doit informer l'utilisateur en temps réel lorsqu'une alerte de prix se déclenche ou qu'une transaction est exécutée, en complément de la consultation REST de l'historique.

Le flux de marché (Phase 8) a déjà posé un précédent : les prix sont diffusés en WebSocket via Django Channels et Redis Pub/Sub (voir [ADR-004](ADR-004-websocket-django-channels-redis.md)). La question est de savoir si les notifications doivent emprunter le même chemin.

La réponse est non, pour une raison de sens du flux :

* Le flux de prix est **bidirectionnel** : le client souscrit un symbole, se désouscrit, et peut durcir son canal.
* Le flux de notifications est **unidirectionnel** : le serveur produit, le client consomme. Le client n'a rien à envoyer, ni à souscrire, ni à négocier.

Appliquer un mécanisme bidirectionnel à un besoin unidirectionnel coûte un `Consumer`, une layer de channels, un cycle de vie de connexion à gérer, pour un flux que le client n'exploite qu'en lecture.

## 2. Décisions prises

### A. Adoption de Server-Sent Events sur HTTP classique
* **SSE** est retenu pour la diffusion des notifications (`text/event-stream`).
* La vue Django renvoie un `StreamingHttpResponse` qui émet les événements au fil de l'eau, sans couche de canaux supplémentaire.
* Le format est celui de la spécification SSE : une ligne `event:`, une ligne `data:` JSON, une ligne vide de séparation.

### B. Source des événements : la table Notification
* Le générateur relit `NotificationRepository.list_after_id` à intervalle régulier et n'émet que les notifications créées depuis le dernier envoi, mémorisé par `last_id`.
* Chaque ligne est filtrée par `user_id` : un client ne peut recevoir que ses propres notifications.
* Un commentaire SSE (`: keepalive`) est envoyé tous les cinq polls inactifs, pour que le timeout de lecture du proxy ne coupe pas une connexion légitime sans trafic.
* **Démarrage à l'instant présent** : à la connexion, `last_id` est positionné sur la notification la plus récente de l'utilisateur (`get_latest_id`) au lieu de `None`. Un client qui se connecte ne reçoit donc pas en push son historique, que l'API REST lui sert déjà par ailleurs.
* **Générateur asynchrone** : la boucle est un générateur `async`, la lecture en base passe par `sync_to_async` et l'attente par `asyncio.sleep`. Un générateur synchrone avec `time.sleep` retiendrait le thread de l'exécuteur pendant toute la durée du flux et sérialiserait derrière lui toutes les autres vues.

### C. Authification
* Le flux réutilise l'authentification JWT du reste de l'API REST (`identity.infrastructure.auth`), aucun token n'est validé deux fois.
* Un `Bearer` absent ou invalide renvoie un 401 avant l'ouverture du flux.

## 3. Alternatives considérées

* **WebSocket via Django Channels** : Rejetée. Le client n'émet jamais de message sur ce flux, la bidirectionnalité et le `Consumer` sont inutiles ici. Ce choix reste pertinent pour le marché (ADR-004), il ne l'est pas pour les notifications.
* **Polling REST (le client interroge la liste)** : Rejetée. Aucune latence, et surtout aucune notification sans action du client : le rappel d'une alerte dépendrait de l'ouverture périodique d'une requête.
* **Redis Pub/Sub comme source du flux SSE** : Reportée. Redis est justifié quand plusieurs instances de serveurs doivent se coordonner. Ici un seul monolithe écrit et lit la même base ; ajouter un broker pour transporter un changement déjà persisté serait une indirection inutile. Le passage à Redis se fera si le SSE est porté par plusieurs instances.
* **Webhooks** : Rejetée. Le webhook est une notification entrante (le serveur reçoit), pas une diffusion sortante vers un navigateur.

## 4. Conséquences & Bénéfices

* **Simplicité** : une vue Django et un générateur, contre un `Consumer` et une layer de channels pour le marché. Le contraste entre les deux implémentations est directement lisible dans le code.
* **Standard et natif** : SSE est du HTTP. Pas de handshake, pas de sous-protocole, pas de library côté client, et reconnexion automatique gérée nativement par `EventSource` côté navigateur.
* **Découplage préservé (Clean Architecture)** : la couche domaine ignore le SSE. `CreateNotificationUseCase` persiste une notification, le flux s'en sert comme source. Le jour où l'on branche Redis, seul le générateur change.
* **Coût assumé** : la notification est lue par poll et non poussée par événement, ce qui introduit jusqu'à `POLL_INTERVAL` (1s) de latence et une lecture en base par connexion inactive. Acceptable à l'échelle d'un monolithe pédagogique, et c'est le compromis à remettre en question si le trafic de notifications devient significatif.
* **Fenêtre de perte connue** : en démarrant sur la dernière notification connue, une notification créée entre le moment où le client consulte l'historique et le moment où il ouvre le flux ne lui est pas poussée. Le remède standard est l'en-tête `Last-Event-ID` de la spécification SSE, qui permet au client de reprendre depuis son dernier identifiant reçu ; il n'est pas implémenté ici, l'endpoint REST d'historique servant de filet de sécurité.
