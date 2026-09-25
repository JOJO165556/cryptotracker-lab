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
