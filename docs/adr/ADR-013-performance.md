# ADR-013 — Tests de Performance

**Statut** : Acceptée

## Contexte

Le projet implémente 8 styles d'API. La Phase 16 vise à mesurer et comparer leurs performances pour identifier les bottlenecks et valider les choix architecturaux.

## Décision

**Approche KISS** : Scripts Python simples avec timeit et requests, pas de framework de charge complexe.

**Scénarios mesurés** :

1. **REST vs gRPC** : Benchmarks ordres de trading
   - Latence moyenne sur 100 requêtes
   - Throughput (req/s)
   - Payload size comparaison

2. **WebSocket** : Test latence broadcast Redis
   - Temps entre update prix et réception client
   - Messages par seconde avec N connexions

3. **GraphQL N+1** : Validation DataLoader
   - Requêtes SQL pour dashboard avec N positions
   - Comparaison avec vs sans DataLoader

**Outils** :
- `timeit` : Micro-benchmarks Python
- `requests` : Client HTTP
- `grpcio` : Client gRPC
- `websockets` : Client WebSocket

## Alternatives considérées

- **locust** : rejetée, trop complexe pour KISS.
- **k6** : rejetée, moins intégré Python.
- **JMeter** : rejetée, trop lourd pour projet solo.

## Conséquences

- Mesures objectives comparatives entre protocoles
- Identification des bottlenecks (Redis, DB, ORM)
- Validation DataLoader anti-N+1
- Scripts simples et maintenable
