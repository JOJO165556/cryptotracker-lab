# ADR-007 : JSON-RPC pour le service Analytics

**Statut** : Acceptée

## Contexte

La Phase 11 de la roadmap exige un service Analytics en JSON-RPC pour comparer les paradigmes RPC avec l'implémentation gRPC de la Phase 10. JSON-RPC utilise JSON comme format de données au lieu de Protobuf, ce qui permet d'expérimenter différentes approches RPC.

## Décision

L'implémentation JSON-RPC utilise le framework Django natif sans framework JSON-RPC externe, pour rester simple et pédagogique.

**Choix technique** :
- JSON-RPC v2 (spécification standard)
- Endpoints Django Ninja existants adaptés au format JSON-RPC
- Format JSON standard pour les requêtes/réponses
- Pas de framework JSON-RPC externe (simple reste pédagogique)

**Architecture** :
```
Client → Django Ninja → JSON-RPC Service Analytics → Repositories
```

## Alternatives considérées

- **jsonrpclib** : Rejetée — Ajouterait une dépendance inutile, Django Ninja suffit
- **FastAPI + JSON-RPC** : Rejetée — Contre l'ADR-002 (monolithe modulaire)
- **Microservice séparé** : Rejetée — Pas justifié pour un service de comparaison

## Conséquences

- Comparaison directe possible entre gRPC (Protobuf) et JSON-RPC (JSON)
- Apprentissage des différences de formats de données RPC
- Code intégré au monolithe Django existant
- Pas de dépendance externe supplémentaire
