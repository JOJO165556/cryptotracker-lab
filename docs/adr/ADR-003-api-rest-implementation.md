# ADR-003 — API REST avec Django Ninja

**Statut** : Acceptée

## Contexte

La phase 7 de la roadmap exige une implémentation REST complète pour permettre aux utilisateurs d'interagir avec le système via HTTP. Le choix du framework REST est critique car il influencera toute la couche interfaces et servira de base pour les autres protocoles (GraphQL, WebSocket, etc).

## Décision

Le framework Django Ninja est choisi pour l'implémentation REST pour les raisons suivantes :

- **Intégration native Django** : Fonctionne directement avec les modèles Django, authentification, middleware
- **Schemas Pydantic** : Validation automatique, typage fort, cohérence avec le reste du projet
- **Auto-documentation** : Génération automatique de la documentation OpenAPI/Swagger
- **Performance** : Basé sur ASGI, plus rapide que DRF pour les cas simples
- **Simplicité** : Moins de boilerplate que DRF, adapté à un projet pédagogique

**Endpoints implémentés** :
- Identity : `POST /api/auth/register`, `POST /api/auth/login`
- Wallet : `GET /api/wallets/me`, `POST /api/wallets/deposit`, `POST /api/wallets/withdraw`, `POST /api/wallets/transfer`
- Market : `GET /api/market/assets/`, `GET /api/market/assets/{symbol}`
- Trading : `POST /api/trading/orders/`, `POST /api/trading/orders/{id}/execute/`, `GET /api/trading/orders/`, `GET /api/trading/transactions/`
- Notification : `POST /api/notifications/alerts/`, `DELETE /api/notifications/alerts/{id}`, `GET /api/notifications/alerts/`, `GET /api/notifications/notifications/`

**Authentification** : JWT via rest_framework_simplejwt, authentification Bearer token sur les endpoints protégés

## Alternatives considérées

- **Django REST Framework (DRF)** : Rejetée — plus verbeux, plus de boilerplate, Django Ninja plus moderne
- **FastAPI** : Rejetée, nécessiterait un service séparé, contraire au choix monolithe modulaire (ADR-002)
- **Fonctions vues Django natives** : Rejetées, pas de validation automatique, pas de schemas typés, plus d'erreurs potentielles

## Conséquences

- La couche interfaces reste cohérente avec l'architecture Clean Architecture (voir [ADR-001](ADR-001-architecture-interne-clean-architecture.md))
- Les schemas Pydantic servent de contrat d'interface, réutilisables pour d'autres protocoles
- L'auto-documentation facilite le développement et la collaboration
- Le choix d'un framework moderne (Django Ninja) reflète les pratiques actuelles plutôt que les standards historiques (DRF)
