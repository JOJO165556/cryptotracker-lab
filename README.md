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
### Phase 8b - SSE (Terminée)
Notifications en temps réel via Server-Sent Events, sans couche de canaux, alors que le flux est unidirectionnel (voir [ADR-008](docs/adr/ADR-008-sse-notifications.md)).
**Connexion** : `GET /api/notifications/stream` (Bearer token)
**Evenement recu** (alertes et transactions) :
```
event: notification
data: {"type": "ALERT", "asset_symbol": "BTC", "message": "BTC a depasse 105000"}
```
Flux push du nouveau uniquement : l'historique reste servi par `GET /api/notifications/`. Un `: keepalive` maintient la connexion ouverte quand il n'y a rien a emettre. Source : table `Notification`, lue par poll (1s).
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
### Phase 12 - Webhooks (Terminée)
Webhook de paiement entrant, signé en HMAC-SHA256 et traité en asynchrone par Celery (voir [ADR-009](docs/adr/ADR-009-webhooks-inbound-async.md)).
**Endpoint** : `POST /webhooks/payment` (hors `/api`, authentifié par signature)
```json
{ "provider_ref": "pay_123", "wallet_id": "uuid", "amount": "500.00", "status": "CONFIRMED" }
```
La vue vérifie la signature (le timestamp signé bloque le rejeu, tolérance 5 min), enregistre le paiement, empile la tâche et répond 200.
L'idempotence tient à trois niveaux : unicité de `provider_ref`, compare-and-set sur le statut, et clé `payment:<provider_ref>` dans le ledger. Un webhook redélivré crédite une seule fois.
Le traitement asynchrone demande un worker : `celery -A core worker` (file Redis, bases 1 et 2).
Un webhook seul ne prouve rien, d'où `scripts/simulate_payment_provider.py` qui joue 7 scénarios (valide, échec, doublon, mauvaise signature, montant altéré, rejeu, en-têtes absents).
### Phase 13 - SOAP (Terminée)
Service SOAP simulant une banque legacy, implémentation manuelle avec XML (voir [ADR-010](docs/adr/ADR-010-soap-legacy-bank.md)).
**Endpoint** : `POST /legacybank/soap/` (WSDL disponible sur `/legacybank/soap/?wsdl`)
- `CreateAccount` - Créer un compte bancaire
- `GetAccount` - Récupérer les informations d'un compte
- `Deposit` - Effectuer un dépôt
- `Withdraw` - Effectuer un retrait
- `Transfer` - Effectuer un virement entre comptes
- `CheckBalance` - Vérifier le solde d'un compte
L'implémentation manuelle montre la structure SOAP (enveloppe, body, fault) sans dépendance externe problématique. L'application business logic est séparée dans `LegacyBankService`.
### Phase 14 - Frontend (Terminée)
Dashboard moderne en HTML/JS natif pour démonstration REST + GraphQL + JSON-RPC + SOAP + WebSocket + SSE ensemble (voir [ADR-011](docs/adr/ADR-011-frontend-dashboard.md)).
**Endpoints** :
- `GET /` - Dashboard principal
- `GET /login/` - Page de connexion
- `GET /register/` - Page d'inscription
**Fonctionnalités** :
- Interface moderne dark mode style trading
- Navigation sidebar avec sections : Dashboard, Trading, Market, Wallet, Alerts, Legacy Bank
- Authentification JWT via REST (token stocké en localStorage, compromis)
- Solde + actifs détenus via REST (GET /api/wallets/)
- Vue agrégée type tableau de bord via GraphQL (query Dashboard)
- Analytics via JSON-RPC (POST /api/analytics/rpc)
- Opérations bancaires via SOAP (POST /legacybank/soap/ avec XML)
- Prix en direct d'un actif via WebSocket (ws://.../ws/market/BTC)
- Notifications qui arrivent en live via SSE (GET /api/notifications/stream)
- Fichiers JS séparés par protocole (rest.js, graphql.js, jsonrpc.js, soap.js, websocket.js, sse.js, app.js)
- Token passé en query param pour SSE (EventSource ne supporte pas les headers custom)
- Analytics via JSON-RPC
- Opérations bancaires via SOAP
- gRPC : information pédagogique (nécessite proxy pour navigateur)
Frontend sans framework (React/Vue) pour rester simple. Code HTML/JS natif avec Fetch API et WebSocket API.
### Phase 15 - Tests (Terminée)
Tests unitaires et intégration avec pytest et pytest-cov (voir [ADR-012](docs/adr/ADR-012-test-strategy.md)).
**Configuration** :
- pytest avec coverage HTML et terminal
- 241 tests passent en ~2 minutes
- Coverage 88%
**Tests par protocole** :
- REST : 33 tests (identity, wallet, trading, notification, payment)
- GraphQL : 9 tests (schema + câblage URL)
- JSON-RPC : 8 tests (analytics)
- SOAP : 11 tests (service + endpoint)
- SSE : 14 tests (flux async + repository)
- Webhooks : 18 tests (signature + Celery)
- WebSocket : 8 tests (consumer + 4 intégration skip)
- gRPC : 9 tests (handler + 5 intégration skip)
### Phase 16 - Performance (Terminée)
Benchmarks comparatifs entre protocoles (voir [ADR-013](docs/adr/ADR-013-performance.md)).
**Scripts** :
- `scripts/benchmark_rest_vs_grpc.py` - Latence et throughput REST vs gRPC
- `scripts/benchmark_websocket.py` - Latence broadcast Redis
- `scripts/benchmark_graphql_dataloader.py` - Validation DataLoader anti-N+1
**Résultats** :
- REST vs gRPC : gRPC 11.7x plus rapide (338 req/s vs 28 req/s, 295ms vs 3470ms latence)
- WebSocket : 2.74ms latence moyenne (min 0.66ms, max 17.39ms)
- GraphQL DataLoader : 42.74ms latence (anti-N+1 activé)
### Phase 17 - Résilience (Terminée)
Mécanismes de résilience pour gérer les pannes de dépendances externes (voir [ADR-014](docs/adr/ADR-014-resilience.md)).
**Bibliothèques** :
- `tenacity` - Retry avec backoff exponentiel
- `pybreaker` - Circuit breaker pattern
**Implémentation** :
- `core/resilience/` - Module de résilience (retry, circuit breaker)
- `market/infrastructure/publishers.py` - Retry Redis + timeout
- `market/interfaces/consumers/price_consumer.py` - Retry WebSocket + circuit breaker
- `core/celery.py` - Configuration retry par défaut pour tâches
**Configuration** :
- Redis: 3 retries, backoff 0.1s→2s, circuit breaker après 5 échecs
- WebSocket: 5 retries, backoff 0.5s→10s, circuit breaker après 5 échecs
- Celery: 3 retries, 60s entre retries, timeout 30s
- DB: 2 retries, backoff 0.5s→1s, circuit breaker après 10 échecs
**Tests** :
- `scripts/test_resilience.py` - Script de test manuel
- `core/resilience/tests/` - Tests unitaires retry et circuit breaker
### Phase 18 - Sécurité (Terminée)
Contrôles de sécurité multicouche pour protéger contre les attaques courantes (voir [ADR-015](docs/adr/ADR-015-security.md)).
**Bibliothèques** :
- `django-ratelimit==4.1.0` - Rate limiting flexible
- `django-cors-headers==4.3.1` - Configuration CORS
- `django-password-validators==1.5.0` - Validation mot de passe
**Implémentation** :
- `core/middleware.py` - Rate limiting middleware (100 req/min par IP, bypass pour authentifiés)
- `core/settings.py` - CORS, validation mot de passe, security headers
- `core/security/tests/test_ratelimit.py` - Tests unitaires rate limiting
**Configuration** :
- Rate limiting: 100 req/min par IP, 1000 req/min par utilisateur authentifié
- CORS: localhost autorisé pour développement
- Validation mot de passe: 8+ caractères, complexité (majuscule, minuscule, chiffre, spécial)
- Security headers: HSTS, CSP, X-Content-Type-Options, X-Frame-Options
**Tests** :
- `core/security/tests/test_ratelimit.py` - 6 tests (1 skip pour limitation cache test)
## Durcissement sécurité
Passé sur l'ensemble des interfaces déjà livrées :
- **Anti-IDOR** : notification, trading et analytics refusent toute ressource appartenant à un autre utilisateur (404 sans fuite d'existence)
- **GraphQL** : conversion du claim JWT `user_id` conditionnée au type réel du PK (`UUIDField` ou `AutoField`)
- **Câblage URLs** : chaque interface est couverte par un test passant par les vraies routes du projet (`urls.py`), pas seulement le router isolé
- **Webhook** : HMAC-SHA256 sur le timestamp signé et le corps, comparaison en temps constant, rejeu bloqué par la tolérance de 5 min, et 4xx (jamais 5xx) pour que le prestataire n'insiste pas sur un message définitivement refusé
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

# Worker Celery, dans un deuxième terminal, requis par la phase 12 (webhooks)
# Sans lui, les webhooks sont bien reçus et accusés, mais aucun paiement n'est crédité
celery -A core worker
```
## Tests
```bash
# Tous les tests avec coverage
pytest

# Tests sans coverage
pytest --no-cov

# Rapport coverage HTML
pytest --cov-report=html
open htmlcov/index.html

# Tests de résilience
pytest core/resilience/tests/
```
## Performance
```bash
# Benchmark REST vs gRPC
python scripts/benchmark_rest_vs_grpc.py

# Benchmark WebSocket latence
python scripts/benchmark_websocket.py

# Benchmark GraphQL DataLoader
python scripts/benchmark_graphql_dataloader.py
```
## Résilience
```bash
# Test manuel de résilience
python scripts/test_resilience.py --scenario all

# Scénarios manuels
# 1. Arrêter Redis: docker-compose stop redis
#    → Vérifier que le WebSocket retry et envoie message d'erreur
# 2. Arrêter PostgreSQL: docker-compose stop postgresql
#    → Vérifier que les endpoints REST retry et échouent gracieusement
# 3. Redémarrer les services
#    → Vérifier que le circuit breaker se ferme automatiquement
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
- ADR-008 - Server-Sent Events pour les notifications
- ADR-009 - Webhook de paiement entrant traité en Celery (`docs/adr/ADR-009-webhooks-inbound-async.md`)
- ADR-010 - SOAP LegacyBank simulé
- ADR-011 - Frontend Dashboard
- ADR-012 - Stratégie de tests
- ADR-013 - Tests de performance
- ADR-014 - Résilience (retry et circuit breaker)
- ADR-015 - Stratégie de sécurité