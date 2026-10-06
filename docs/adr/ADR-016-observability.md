# ADR-016: Stratégie d'Observabilité

## Contexte

Le système a actuellement des logs basiques dans quelques fichiers (WebSocket, resilience, Celery, webhooks), mais manque une stratégie d'observabilité cohérente:
- Pas de configuration LOGGING centralisée
- Logs non structurés (texte brut)
- Pas de moyen de suivre une requête de bout en bout (pas de request ID)
- Pas de métriques pour surveiller la santé du système
- Pas de tracing distribué pour comprendre les performances

## Problème

Sans observabilité, il est difficile de:
- **Déboguer en production**: impossible de suivre une requête à travers les composants
- **Surveiller la santé**: pas de métriques pour détecter les anomalies
- **Comprendre les performances**: pas de mesure de latence par endpoint
- **Identifier les erreurs**: logs dispersés et non corrélés

## Alternatives

### Option 1: Logs Django standard (non structurés)
- **Avantages**: Configuration simple, pas de dépendances externes
- **Inconvénients**: Logs non structurés, pas de request ID, pas de métriques
- **Rejeté**: Insuffisant pour suivre une requête de bout en bout

### Option 2: Observabilité minimale (logs basiques)
- **Avantages**: Simple, résout le problème de débogage basique
- **Inconvénients**: Pas de métriques, pas de corrélation entre logs
- **Rejeté**: Insuffisant pour un projet pédagogique sur les systèmes distribués

### Option 3: Observabilité complète (Logs structurés + Request ID + Metrics)
- **Avantages**: Couvre tous les besoins pédagogiques, patterns standard
- **Inconvénients**: Plus complexe, dépendances supplémentaires
- **Choisi**: Meilleur compromis pédagogique et pratique

### Option 4: Observabilité complète avec Tracing distribué
- **Avantages**: Tracing bout-en-bout avec opentelemetry
- **Inconvénients**: Très complexe, nécessite infrastructure (Jaeger, Tempo)
- **Rejeté**: Trop complexe pour un projet pédagogique Django monolithe

## Décision

Implémenter une stratégie d'observabilité pragmatique avec:
1. **Logs structurés** avec `structlog`
2. **Request ID** avec middleware Django
3. **Metrics de base** avec `django-prometheus`

### Bibliothèques ajoutées
- `structlog` - Logs structurés JSON
- `django-request-id` - Request ID middleware
- `django-prometheus` - Metrics de base (optionnel)

## Conséquences

### Positives
- Débogage facilité en production avec logs structurés
- Suivi de requête bout-en-bout avec request ID
- Surveillance de la santé avec métriques
- Apprentissage des patterns d'observabilité (logs, metrics, correlation)
- Compréhension des performances par endpoint

### Négatives
- Complexité accrue du code
- Dépendances supplémentaires
- Configuration logging à ajuster pour chaque environnement
- Overhead minimal en performance (logs structurés, metrics)
