# ADR-014: Stratégie de Résilience

## Contexte

Le système dépend de plusieurs services externes (Redis, PostgreSQL) qui peuvent subir des pannes ou des dégradations temporaires. L'implémentation actuelle ne gère pas ces cas:
- RedisMarketPublisher n'a aucun retry en cas d'échec
- PriceConsumer a un retry basique sans backoff ni circuit breaker
- Les tâches Celery n'ont pas de retry configuré
- Les repositories n'ont pas de timeout ni retry

## Problème

Sans mécanismes de résilience, une panne temporaire d'une dépendance externe peut:
- Causer des erreurs 500 visibles par l'utilisateur
- Faire crasher des composants critiques
- Entraîner une cascade de défaillances
- Perdre des données (ex: webhooks non traités)

## Alternatives

### Option 1: Ignorer la résilience
- **Avantages**: Code simple, pas de dépendances supplémentaires
- **Inconvénients**: Système fragile, mauvaise expérience utilisateur
- **Rejeté**: En contradiction avec la pédagogie (apprendre les patterns de résilience)

### Option 2: Retry simple (fixe)
- **Avantages**: Simple à implémenter
- **Inconvénients**: Pas de backoff, peut surcharger le service en panne
- **Rejeté**: Ne gère pas les pannes prolongées

### Option 3: Retry avec backoff + Circuit Breaker
- **Avantages**: Gère les pannes temporaires et prolongées, pattern standard
- **Inconvénients**: Plus complexe, nécessite des bibliothèques externes
- **Choisi**: Meilleur compromis pédagogique et pratique

## Décision

Implémenter une stratégie de résilience avec:
1. **Retry avec backoff exponentiel** (bibliothèque `tenacity`)
2. **Circuit breaker pattern** (bibliothèque `pybreaker`)
3. **Timeouts de connexion** adaptés
4. **Fallbacks gracieux** (log + message utilisateur)

### Bibliothèques ajoutées
- `tenacity==9.0.0` - Retry avec backoff exponentiel
- `pybreaker==2.1.1` - Circuit breaker pattern

### Configuration par composant

| Composant | Retry max | Backoff | Circuit breaker | Timeout |
|-----------|----------|---------|-----------------|---------|
| RedisMarketPublisher | 3 | 0.1s → 2s | Oui (5 échecs) | 5s |
| PriceConsumer | 5 | 0.5s → 10s | Oui (5 échecs) | 3s |
| Celery Tasks | 3 | 60s | Non | 30s |
| Repositories DB | 2 | 0.5s → 1s | Oui (10 échecs) | 10s |



## Conséquences

### Positives
- Système plus robuste aux pannes temporaires
- Meilleure expérience utilisateur (messages clairs)
- Protection contre les cascades de défaillances
- Apprentissage des patterns de résilience (retry, circuit breaker)

### Négatives
- Complexité accrue du code
- Dépendances supplémentaires
- Besoin de tests supplémentaires

### Tests
- Tests unitaires des décorateurs de retry (10 tests, tous passants)
- Tests du circuit breaker (3 tests, tous passants)
- Test manuel: `scripts/test_resilience.py`
- Note: 1 test WebSocket skipped (mock async à réécrire)

## Références

- [Retry Pattern - Microsoft](https://docs.microsoft.com/en-us/azure/architecture/patterns/retry)
- [Circuit Breaker Pattern - Martin Fowler](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Tenacity Documentation](https://tenacity.readthedocs.io/)
- [Pybreaker Documentation](https://pybreaker.readthedocs.io/)
