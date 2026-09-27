# CryptoTracker Lab
Plateforme pédagogique pour apprendre l'architecture logicielle à travers différents styles d'API (REST, GraphQL, WebSocket, gRPC, JSON-RPC, Webhooks, SOAP).
## Vision
Projet pédagogique : la valeur n'est pas dans le nombre de fonctionnalités mais dans la justesse de l'architecture qui les supporte.
## Architecture
Monolithe modulaire Django avec Clean Architecture pragmatique (voir [ADR-001](docs/adr/ADR-001-architecture-interne-clean-architecture.md), [ADR-002](docs/adr/ADR-002-monolithe-modulaire.md)).
**Modules** : Identity - Wallet - Market - Trading - Analytics - Notification - Payment
**Découpage interne** : domain/application/infrastructure/interfaces par module
## État d'avancement
### Phase 7 - REST (Terminée)
Endpoints REST implémentés avec Django Ninja :
**Identity**
- `POST /api/auth/register` - Inscription avec JWT
- `POST /api/auth/login` - Connexion avec JWT
**Wallet** (authentifié)
- `GET /api/wallets/me` - Portefeuille utilisateur avec positions d'actifs
- `POST /api/wallets/deposit` - Créditer portefeuille
- `POST /api/wallets/withdraw` - Débiter portefeuille  
- `POST /api/wallets/transfer` - Transférer entre utilisateurs
**Market**
- `GET /api/market/assets/` - Liste tous les actifs
- `GET /api/market/assets/{symbol}` - Détails d'un actif
- `POST /api/market/assets/{symbol}/price` - Mettre à jour le prix (authentifié)
**Trading** (authentifié)
- `POST /api/trading/orders/` - Créer ordre (avec idempotence, header `Idempotency-Key`)
- `POST /api/trading/orders/{id}/execute/` - Exécuter ordre (débit wallet + MAJ position)
- `GET /api/trading/orders/` - Historique ordres (pagination)
- `GET /api/trading/transactions/` - Historique transactions (pagination)
**Notification** (authentifié)
- `POST /api/notifications/alerts/` - Créer alerte de prix
- `DELETE /api/notifications/alerts/{id}` - Supprimer alerte
- `GET /api/notifications/alerts/` - Liste alertes utilisateur
- `GET /api/notifications/notifications/` - Liste notifications utilisateur
- `POST /api/notifications/notifications/{id}/read` - Marquer notification comme lue
### Phase 8 - WebSocket (Terminée)
Flux de prix en temps réel via Redis Pub/Sub et Django Channels (voir [ADR-004](docs/adr/ADR-004-websocket-django-channels.md)).
**Connexion** : `ws://localhost:8000/ws/market/{symbol}/`
**Message serveur -> client** (push sur chaque variation de prix) :
```json
{ "type": "price_update", "symbol": "BTC", "price": "104032.50", "ts": 1234567890 }
```
**Message client -> serveur** (souscription à d'autres symboles sur la même connexion) :
```json
{ "type": "subscribe", "symbols": ["ETH", "SOL"] }
```
Pipeline interne : `POST /api/market/assets/{symbol}/price` -> `UpdatePriceUseCase` -> `RedisMarketPublisher` -> `PriceConsumer` -> Client
### Phase 9 - GraphQL (Terminée)
Dashboard agrégé via GraphQL avec Strawberry + strawberry-graphql-django (voir [ADR-005](docs/adr/ADR-005-graphql-strawberry.md)).
**Endpoint** : `POST /graphql/` (GraphiQL via GET), authentifié par `Authorization: Bearer <jwt>`.
**Schéma** :
```graphql
type Query {
  me: User!
  dashboard: Wallet!
}
```
```graphql
query Dashboard {
  dashboard { balance assets { symbol quantity value } }
}
```
**Anti N+1** : le champ `value` de chaque position est résolu via un DataLoader
(une seule requête `WHERE symbol IN (...)` pour tous les actifs détenus, quel que
soit le nombre de positions, verrouillé par test à 4 requêtes SQL par dashboard).
### Phase 10 - gRPC (Terminée)
Service Order Engine en gRPC, branché sur l'event loop ASGI via `grpcio.aio`, sans FastAPI (voir [ADR-006](docs/adr/ADR-006-grpc-asyncio-order-engine.md)).
**Contrat** : `order_engine/proto/order.proto` (service `OrderService`)
- `CreateOrder` - Créer un ordre (wallet, actif, côté, quantité, prix, idempotence)
- `ExecuteOrder` - Exécuter un ordre (prix, quantité exécutée)
- `GetOrder` - Détail d'un ordre par id
- `ListOrders` - Historique des ordres d'un wallet
Le serveur réutilise les cas d'usage du monolithe (`CreateOrderUseCase`, `ExecuteTradeUseCase`), sans dupliquer la logique métier.
### Phase 11 - JSON-RPC (Terminée)
Service Analytics en JSON-RPC v2 sur le monolithe Django, sans framework externe (voir [ADR-007](docs/adr/ADR-007-json-rpc-analytics.md)).
**Endpoint** : `POST /api/analytics/rpc` (authentifié par JWT)
- `get_portfolio_value` - Valeur du portefeuille de l'utilisateur connecté
- `get_trading_volume` - Volume de trading sur les N derniers jours
- `get_order_statistics` - Statistiques des ordres de l'utilisateur connecté
- `get_market_summary` - Résumé du marché
Conformité JSON-RPC v2 (identifiants, codes d'erreur -32601, -32602, -32603). Le wallet est toujours déduit du JWT, un `wallet_id` étranger est refusé.
## Durcissement sécurité
Passé sur l'ensemble des interfaces déjà livrées :
- **Anti-IDOR** : notification, trading et analytics refusent toute ressource appartenant à un autre utilisateur (404 sans fuite d'existence)
- **GraphQL** : conversion du claim JWT `user_id` conditionnée au type réel du PK (`UUIDField` ou `AutoField`)
- **Câblage URLs** : chaque interface est couverte par un test passant par les vraies routes du projet (`urls.py`), pas seulement le router isolé
## Installation
```bash
# Environment virtuelle
python -m venv .venv
source .venv/bin/activate
# Dépendances
pip install -r requirements.txt
# Base de données
docker-compose up -d postgresql
# Migrations
python manage.py migrate
# Serveur de développement (ASGI via Daphne - HTTP + WebSocket)
python manage.py runserver
```
## Tests
```bash
pytest
```
## Documentation
- [docs/00_vision_roadmap.md](docs/00_vision_roadmap.md) - Vision et feuille de route
- [docs/01_project_definition.md](docs/01_project_definition.md) - Définition du projet
- [docs/02_domain_model.md](docs/02_domain_model.md) - Modèle de domaine
- [docs/03_setup.md](docs/03_setup.md) - Configuration et setup
- [docs/api-contracts.md](docs/api-contracts.md) - Contrats API par protocole
- [docs/adr/](docs/adr/) - Architecture Decision Records
## ADRs
- ADR-001 - Clean Architecture pragmatique
- ADR-002 - Monolithe modulaire
- ADR-003 - API REST avec Django Ninja
- ADR-004 - WebSocket avec Django Channels (`docs/adr/ADR-004-websocket-django-channels-redis.md`)
- ADR-005 - GraphQL avec Strawberry
- ADR-006 - gRPC asynchrone avec grpcio.aio (Order Engine)
- ADR-007 - JSON-RPC pour le service Analytics
