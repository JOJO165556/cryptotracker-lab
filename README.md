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
- `GET /api/wallets/me` - Portefeuille utilisateur
- `POST /api/wallets/deposit` - Créditer portefeuille
- `POST /api/wallets/withdraw` - Débiter portefeuille  
- `POST /api/wallets/transfer` - Transférer entre utilisateurs

**Market**
- `GET /api/market/assets/` - Liste tous les actifs
- `GET /api/market/assets/{symbol}` - Détails d'un actif

**Trading** (authentifié)
- `POST /api/trading/orders/` - Créer ordre (avec idempotence)
- `POST /api/trading/orders/{id}/execute/` - Exécuter ordre
- `GET /api/trading/orders/` - Historique ordres (pagination)
- `GET /api/trading/transactions/` - Historique transactions (pagination)

**Notification** (authentifié)
- `POST /api/notifications/alerts/` - Créer alerte de prix
- `DELETE /api/notifications/alerts/{id}` - Supprimer alerte
- `GET /api/notifications/alerts/` - Liste alertes utilisateur
- `GET /api/notifications/notifications/` - Liste notifications utilisateur
- `POST /api/notifications/notifications/{id}/read` - Marquer notification comme lue

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

# Serveur de développement
python manage.py runserver
```

## Tests

```bash
pytest
```

92 tests couvrant domain, infrastructure, application et interfaces.

## Documentation

- [docs/00_vision_roadmap.md](docs/00_vision_roadmap.md) - Vision et feuille de route
- [docs/01_project_definition.md](docs/01_project_definition.md) - Définition du projet
- [docs/02_domain_model.md](docs/02_domain_model.md) - Modèle de domaine
- [docs/03_setup.md](docs/03_setup.md) - Configuration et setup
- [docs/api-contracts.md](docs/api-contracts.md) - Contrats API par protocole
- [docs/adr/](docs/adr/) - Architecture Decision Records

## ADRs

- ADR-001 — Clean Architecture pragmatique
- ADR-002 — Monolithe modulaire
- ADR-003 — API REST avec Django Ninja
