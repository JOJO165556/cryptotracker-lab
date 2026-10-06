# ADR-012 — Stratégie de Tests

**Statut** : Acceptée

## Contexte

Le projet implémente 8 styles d'API (REST, WebSocket, GraphQL, gRPC, JSON-RPC, Webhooks, SOAP, SSE). Les tests existants couvrent les fonctionnalités mais manquent de configuration de coverage pour mesurer la couverture de code et de tests d'intégration avec stack réelle pour certains protocoles.

La Phase 15 de la roadmap vise à établir une base de tests mesurable et documentée.

## Décision

Configuration pytest avec pytest-cov et pytest-asyncio :

**pytest.ini :**
```ini
[pytest]
DJANGO_SETTINGS_MODULE = core.settings
python_files = test_*.py *_tests.py
asyncio_mode = auto
norecursedirs = .git .venv build dist scripts
addopts =
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --cov-config=.coveragerc
```

**.coveragerc :** Exclusions standard (migrations, tests, manage.py, proto, .venv, build, dist)

Tests WebSocket et gRPC intégration marqués `@pytest.mark.skip` car nécessitent infrastructure externe (Redis running, serveur gRPC). Exécution manuelle quand infrastructure disponible.

## Alternatives considérées

- **Markers personnalisés (unit/integration/slow)** : rejetée, maintenance supplémentaire sans valeur ajoutée (KISS).
- **Playwright E2E** : rejetée, frontend simple (HTML/JS natif), effort disproportionné.
- **100% coverage** : rejetée, effort disproportionné, vanity metric.

## Conséquences

- 241 tests passent en ~2 minutes
- Coverage 88% (objectif : ≥70%)
- Configuration minimaliste et maintenable
- Tous les protocoles testés
- Pas de classification explicite unit/integration
- Tests WebSocket/gRPC intégration non exécutés par défaut
- Pas de tests E2E navigateur
