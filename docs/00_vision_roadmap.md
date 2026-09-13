# CryptoTracker Lab — Vision & Feuille de route

> Ce document est ton fil conducteur. Il ne détaille pas chaque étape à l'avance —
> il te dit **où tu vas**, **quels choix sont déjà fixés**, et **ce qu'il te reste à décider
> au moment venu**. Relis-le à chaque nouvelle phase.

---

## 1. Vision

CryptoTracker est une plateforme permettant à un utilisateur de suivre des actifs
numériques, gérer un portefeuille virtuel, effectuer des transactions simulées et
recevoir des informations de marché en temps réel.

**But réel du projet** : apprendre pourquoi et comment on construit un système —
pas livrer un produit. La fonctionnalité doit rester simple ; l'architecture doit
rester réaliste.

## 2. Périmètre

**Dans le périmètre**
- Suivi de portefeuille virtuel, achats/ventes simulés
- Marché en temps réel, alertes, notifications
- Plusieurs styles de communication (REST, WebSocket, GraphQL, gRPC, JSON-RPC, Webhooks, SOAP)

**Hors périmètre (à ne jamais réintroduire en cours de route)**
- Vrai trading / vrai argent / vraie banque
- Sécurité financière niveau production
- Blockchain, Kubernetes, cloud complexe
- Microservices dès le départ

## 3. Principe directeur (à appliquer à CHAQUE décision technique)

```
Problème → Besoin → Contrainte → Solution → Compromis → Implémentation → Mesure
```

Si tu ne peux pas remplir ces 7 cases pour une techno que tu veux ajouter
(Kafka, gRPC, GraphQL...), c'est qu'elle n'est pas encore justifiée. Tu ne l'ajoutes pas.

## 4. Décisions déjà fixées (ne pas rediscuter à chaque phase)

| Sujet | Décision | Pourquoi |
|---|---|---|
| Socle | Django | Cœur du système, ORM + admin + écosystème mature |
| Architecture | Monolithe modulaire | Apprendre la séparation des responsabilités avant de payer le coût des microservices |
| Découpage interne | domain / application / infrastructure / interfaces par module | Inversion de dépendances, testabilité |
| Base de données | PostgreSQL | Relationnel, transactions, cohérent avec le domaine (wallet, ordres) |
| Cache / pub-sub | Redis | Prix en temps réel, WebSocket |
| FastAPI | Seulement si un service séparé le justifie (ex. Order Engine en gRPC) | Jamais "parce que c'est à la mode" |
| Microservices | Non, pas au départ | Le monolithe modulaire suffit à apprendre le découplage |
| SOAP | Simulé via un faux "LegacyBank" | Objectif pédagogique, pas d'intégration réelle |

## 5. Feuille de route (vue d'ensemble — le détail se fait phase par phase, pas maintenant)

| Phase | Ce qu'on produit | Ce qu'on apprend |
|---|---|---|
| 0 — Définition | `01_project_definition.md` | Cadrer vision / hors périmètre |
| 1-2 — Besoins | Cas d'utilisation, spécifications | Analyse fonctionnelle, cas d'exception |
| 3 — Domaine | Entités, relations, règles métier | Le métier ne doit rien à Django |
| 4 — Architecture | Diagramme cible, découpage modulaire | Modularité, couplage/cohésion |
| 5 — Contrats API | `api-contracts.md` (REST, puis GraphQL, gRPC...) | Concevoir avant d'implémenter |
| 6 — Socle | Repo, Django, Postgres, Docker, CI | Fondations propres |
| 7 — REST | Premier module complet (Wallet) | HTTP, statelessness, sécurité API |
| 8 — WebSocket | Flux de prix temps réel | Event-driven, Redis pub/sub |
| 9 — GraphQL | Dashboard agrégé | Schema, resolvers, N+1 |
| 10 — gRPC | Order Engine (service séparé) | RPC, contrats stricts, éventuellement FastAPI |
| 11 — JSON-RPC | Service Analytics | Comparaison des paradigmes RPC |
| 12 — Webhooks | Paiement simulé | Idempotence, retry, async |
| 13 — SOAP | LegacyBank simulé | XML, WSDL, intégration legacy |
| 14 — Frontend | Dashboard minimal | Montrer REST + GraphQL + WebSocket ensemble |
| 15 — Tests | Unitaires, intégration, par protocole | Prouver que ça marche, pas juste "ça marche chez moi" |
| 16 — Performance | Mesures REST vs gRPC, charge WebSocket | Scalabilité, bottlenecks |
| 17 — Résilience | Pannes provoquées (Redis down, retry...) | Timeout, circuit breaker, fallback |
| 18 — Sécurité | Auth, validation, rate limiting | Frontières de confiance |
| 19 — Observabilité | Logs, metrics, tracing | Suivre une requête de bout en bout |
| 20 — Documentation | README + ADR | Justifier chaque choix |

**Règle d'usage de ce tableau** : tu n'ouvres jamais deux phases en parallèle.
Une phase se termine (code + test + ADR si décision structurante) avant de passer
à la suivante.

## 6. Règles à respecter tout du long

1. Un pattern ou une techno n'apparaît que si un problème concret l'exige — jamais en préventif.
2. Chaque décision structurante (protocole, techno, style d'architecture) donne lieu à un
   **ADR** court dans `docs/adr/` (contexte, alternatives, décision, conséquences).
3. Le domaine métier (règles, entités) ne dépend jamais d'un framework.
4. On mesure avant de dire qu'un choix est "meilleur" (latence, charge, complexité).
5. Si une phase prend trop d'ampleur, on la découpe — on ne saute pas la suivante en attendant.

## 7. Comment utiliser ce document avec moi

Quand tu es prêt à avancer, dis simplement :
> "On attaque la phase [X] de CryptoTracker."

Je reviens alors à la feuille de route ci-dessus pour te guider depuis le besoin
jusqu'à l'implémentation, sans qu'on ait à retout re-décider depuis zéro à chaque fois.

**Prochaine étape suggérée** : Phase 0 — rédiger `01_project_definition.md`.
