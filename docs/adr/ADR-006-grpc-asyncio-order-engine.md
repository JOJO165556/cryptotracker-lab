# ADR-006 : gRPC asynchrone avec grpcio.aio pour l'Order Engine

**Statut** : Acceptée

## Contexte

La Phase 10 de la roadmap exige un Order Engine en gRPC pour apprendre les protocoles RPC avec contrats stricts Le choix de l'implémentation gRPC est critique car elle déterminera comment ce service s'intègre avec le monolithe Django existant

## Décision

L'implémentation gRPC utilise `grpcio.aio` asynchrone branché directement sur l'event loop ASGI, sans FastAPI

**Choix technique** :
- `grpcio.aio` : Serveur gRPC asynchrone natif
- Protobuf : Contrats stricts pour la définition des services
- Intégration ASGI : Le serveur gRPC partage l'event loop avec Django ASGI
- Pas de FastAPI : Le monolithe Django reste le point d'entrée unique

**Architecture** :
```
Client HTTP (Django Ninja) → Django ASGI → grpcio.aio → Order Engine Service
```

## Alternatives considérées

- **FastAPI + gRPC** : Rejetée — Ajouterait un framework supplémentaire inutile, Django ASGI suffit
- **gRPC synchrone (grpcio)** : Rejetée — Bloquerait l'event loop, mauvaise performance pour I/O
- **Service séparé + FastAPI** : Rejetée — Contre l'ADR-002 (monolithe modulaire), pas justifié pour l'instant

## Conséquences

- L'Order Engine reste intégré au monolithe Django (même processus)
- Performance asynchrone sans overhead de framework supplémentaire
- Apprentissage des contrats Protobuf et du pattern RPC
- Code d'intégration plus simple (partage de l'event loop)
