# CryptoTracker Lab
Plateforme pédagogique pour apprendre l'architecture logicielle à travers différents styles d'API (REST, GraphQL, WebSocket, SSE, gRPC, JSON-RPC, Webhooks, SOAP)

---

## Vision
Projet pédagogique : la valeur n'est pas dans le nombre de fonctionnalités mais dans la justesse de l'architecture qui les supporte.

---

## Architecture
Monolithe modulaire Django avec Clean Architecture pragmatique (voir [ADR-001](docs/adr/ADR-001-architecture-interne-clean-architecture.md), [ADR-002](docs/adr/ADR-002-monolithe-modulaire.md)).

- **Modules**: Identity - Wallet - Market - Trading - Analytics - Notification - Payment
- **Découpage interne**: domain / application / infrastructure / interfaces par module

---

## Etat d'avancement

| Phase | Sujet | Statut | ADR |
|-------|--------|--------|-----|
| 7 | REST API | Terminée | ADR-003 |
| 8 | WebSocket (Redis Pub/Sub) | Terminée | ADR-004 |
| 8b | SSE (Notifications) | Terminée | ADR-008 |
| 9 | GraphQL (DataLoader) | Terminée | ADR-005 |
| 10 | gRPC (Order Engine) | Terminée | ADR-006 |
| 11 | JSON-RPC (Analytics) | Terminée | ADR-007 |
| 12 | Webhooks (Celery) | Terminée | ADR-009 |
| 13 | SOAP (LegacyBank) | Terminée | ADR-010 |
| 14 | Frontend Dashboard | Terminée | ADR-011 |
| 15 | Tests (pytest) | Terminée | ADR-012 |
| 16 | Performance (benchmarks) | Terminée | ADR-013 |
| 17 | Résilience (retry/circuit breaker) | Terminée | ADR-014 |
| 18 | Sécurité (rate limiting/CORS) | Terminée | ADR-015 |
| 19 | Observabilité (logs/metrics) | Terminée | ADR-016 |
| 20 | Documentation (continue) | Terminée | - |

**Tests**: 256 tests passent, 11 skipped, coverage 85%

---

## Installation

```bash
# Environment virtuelle
python -m venv .venv
source .venv/bin/activate

# Dépendances
pip install -r requirements.txt

# Base de données (Docker)
docker-compose up -d postgresql redis

# Migrations
python manage.py migrate

# Serveur de développement (ASGI via Daphne - HTTP + WebSocket)
python manage.py runserver

# Worker Celery (pour webhooks), dans un deuxième terminal
celery -A core worker
```

---

## Tests

```bash
# Tous les tests avec coverage
pytest

# Tests sans coverage
pytest --no-cov

# Rapport coverage HTML
pytest --cov-report=html
open htmlcov/index.html
```

---

## Performance

```bash
# Benchmark REST vs gRPC
python scripts/benchmark_rest_vs_grpc.py

# Benchmark WebSocket latence
python scripts/benchmark_websocket.py

# Benchmark GraphQL DataLoader
python scripts/benchmark_graphql_dataloader.py
```

**Résultats**:
- REST vs gRPC: gRPC 11.7x plus rapide (338 req/s vs 28 req/s, 295ms vs 3470ms latence)
- WebSocket: 2.74ms latence moyenne (min 0.66ms, max 17.39ms)
- GraphQL DataLoader: 42.74ms latence (anti-N+1 activé)

---

## Résilience

```bash
# Test manuel de résilience
python scripts/test_resilience.py --scenario all

# Scénarios manuels
# 1. Arrêter Redis: docker-compose stop redis
#    -> Vérifier que le WebSocket retry et envoie message d'erreur
# 2. Arrêter PostgreSQL: docker-compose stop postgresql
#    -> Vérifier que les endpoints REST retry et échouent gracieusement
# 3. Redémarrer les services
#    -> Vérifier que le circuit breaker se ferme automatiquement
```

---

## Observabilité

- **Logs structurés**: format console en dev, JSON en production avec structlog
- **Request ID**: injecté automatiquement pour suivre une requête de bout en bout
- **Metrics**: endpoint `/metrics` avec métriques Django (DB, cache, requêtes)

**Note**: La documentation est continue (ADR + README) à chaque phase, donc la phase 20 est implicitement terminée.

---

## Durcissement sécurité

- **Anti-IDOR**: notification, trading et analytics refusent toute ressource appartenant à un autre utilisateur (404 sans fuite d'existence)
- **GraphQL**: conversion du claim JWT `user_id` conditionnée au type réel du PK (`UUIDField` ou `AutoField`)
- **Câblage URLs**: chaque interface est couverte par un test passant par les vraies routes du projet (`urls.py`)
- **Webhook**: HMAC-SHA256 sur le timestamp signé et le corps, comparaison en temps constant, rejeu bloqué par la tolérance de 5 min

---

## Documentation

- [docs/00_vision_roadmap.md](docs/00_vision_roadmap.md) - Vision et feuille de route
- [docs/01_project_definition.md](docs/01_project_definition.md) - Définition du projet
- [docs/02_domain_model.md](docs/02_domain_model.md) - Modèle de domaine
- [docs/03_setup.md](docs/03_setup.md) - Configuration et setup
- [docs/api-contracts.md](docs/api-contracts.md) - Contrats API par protocole
- [docs/adr/](docs/adr/) - Architecture Decision Records

---

## ADRs (Architecture Decision Records)

- ADR-001 - Clean Architecture pragmatique
- ADR-002 - Monolithe modulaire
- ADR-003 - API REST avec Django Ninja
- ADR-004 - WebSocket avec Django Channels
- ADR-005 - GraphQL avec Strawberry
- ADR-006 - gRPC asynchrone avec grpcio.aio (Order Engine)
- ADR-007 - JSON-RPC pour le service Analytics
- ADR-008 - Server-Sent Events pour les notifications
- ADR-009 - Webhook de paiement entrant traité en Celery
- ADR-010 - SOAP LegacyBank simulé
- ADR-011 - Frontend Dashboard
- ADR-012 - Stratégie de tests
- ADR-013 - Tests de performance
- ADR-014 - Résilience (retry et circuit breaker)
- ADR-015 - Stratégie de sécurité
- ADR-016 - Stratégie d'observabilité
