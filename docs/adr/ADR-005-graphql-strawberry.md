# ADR-005 : Dashboard agrégé via GraphQL (Strawberry)

**Statut** : Acceptée

## Contexte

La phase 9 de la roadmap vise à ajouter une interface GraphQL pour exposer un
**dashboard agrégé** : un client frontend veut récupérer en une seule requête le
profil de l'utilisateur connecté et l'état complet de son portefeuille (solde,
positions et valeur de chaque position au prix courant du marché).

Cette décision s'inscrit dans le cadre du monolithe modulaire défini par
[ADR-002](ADR-002-monolithe-modulaire.md) et de la séparation des couches
exposée dans [ADR-001](ADR-001-architecture-interne-clean-architecture.md).

Avec REST, il faudrait multiplier les appels ou construire des endpoints spécifiques.
GraphQL répond nativement à ce besoin : le client décrit exactement la forme de la réponse attendue.

La vraie difficulté de ce style d'API est le **problème N+1** : résoudre la
valeur de N positions exige trivialement N requêtes SQL sur les actifs si chaque
résolveur interroge la base indépendamment. Ce piège structurel doit être traité
au moment de la conception, c'est le cœur pédagogique de la phase.

## Décision

### A. Strawberry + strawberry-graphql-django

- **Strawberry** (schéma défini en types Python, moderne et typé) est retenu
  comme bibliothèque GraphQL, avec l'extension **strawberry-graphql-django**
  pour l'intégration Django (vue HTTP, IDE GraphiQL, contexte).
- **Graphene** est écarté : l'esquisse du schéma était déjà posée en
  Strawberry et son modèle de types est plus proche de la clean architecture
  (on reste libre de brancher des use cases et non des modèles ORM).

### B. Couche interface qui appelle les use cases, pas l'ORM

- `Query.dashboard` et `Query.me` passent par les cas d'usage applicatifs
  (`GetWalletUseCase`) et les repositories, comme les interfaces REST.
  La couche `domain/` et `application/` ne sait rien de GraphQL.
- La vue est **asynchrone** (`AsyncGraphQLView`) : les résolveurs et la
  permission sont `async` et enveloppent les appels ORM synchrones dans
  `sync_to_async`, ce qui évite le blocage de l'event loop et les
  `SynchronousOnlyOperation`.

### C. DataLoader pour éliminer le N+1 sur `assets → asset`

- Le champ `WalletAssetType.value` est résolu via un **DataLoader**
  (`strawberry.dataloader`) qui regroupe tous les symboles des positions du
  dashboard en une seule requête `WHERE symbol IN (...)`.
- Une instance de loader est créée **par requête GraphQL** et injectée dans le
  contexte (`GraphQLContext.loaders`) pour garantir l'isolation entre les
  clients.
- Le chargement batch passe par `AssetRepository.list_by_symbols()`, le
  repository du module Market : l'interface GraphQL ne touche jamais directement
  les modèles ORM.

### D. Authentification

- Réutilisation de la logique JWT existante (SimpleJWT) reproduite dans une
  permission Strawberry (`IsAuthenticated`), cohérente avec le `JWTAuth` REST.
  Un token invalide ou absent est traduit en erreur GraphQL.

## Alternatives considérées

* **Graphene-Django** :
  * *Pour* : maturité, écosystème Django historique.
  * *Contre* : périmètre réécrit par rapport à l'esquisse, types moins rigoureux.
* **Sans DataLoader (résolveur naïf)** :
  * *Contre* : N requêtes SQL par dashboard ; c'est précisément le problème
    que cette phase doit apprendre à résoudre. Les tests verrouillent le
    comportement : 4 requêtes SQL pour un dashboard à N positions (user +
    wallet + positions + batch actifs).

## Conséquences

- **Anti N+1 prouvé par les tests** : `django_assert_num_queries(4)` reste
  stable quel que soit le nombre de positions, une seule requête par lot
  d'actifs.
- **Cohérence d'architecture** : GraphQL n'est qu'une nouvelle interface du même
  monolithe ; rien du domaine n'a été modifié pour GraphQL.
- **Bénéfice pédagogique** : le schéma (types et résolveurs) vit à part dans
  `core/graphql_api/`, isolé des modules métiers, et documente le pattern
  DataLoader réutilisable pour la suite (gRPC, JSON-RPC).
- **Coût** : une bibliothèque de plus à maintenir ; l'asynchronisme de la vue
  impose `sync_to_async` systématique sur tout accès ORM.
- **Détail d'implémentation, claim utilisateur** : SimpleJWT sérialise
  toujours `user_id` en chaîne (ex. `"3"` pour un AutoField, `"a0eebc99-…"`
  pour un UUIDField). La permission ne convertit en `uuid.UUID` que si le PK
  du modèle user est réellement un `UUIDField`, pour éviter `uuid.UUID("3")`
  (ValueError) sur le `auth.User` par défaut à PK entier.

## Contrat exposé

Endpoint unique : `POST /graphql/` (ou sur une seule requête GET avec
GraphiQL). Authentification : header `Authorization: Bearer <jwt>`.

```graphql
type Wallet { balance: Decimal!, assets: [WalletAsset!]! }
type WalletAsset { symbol: String!, quantity: Decimal!, value: Decimal! }
type Query {
  me: User!
  dashboard: Wallet!
}
```