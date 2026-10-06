# ADR-015: Stratégie de Sécurité

## Contexte

Le système a déjà une authentification JWT et des middleware Django standard, mais manque plusieurs couches de sécurité importantes:
- Pas de rate limiting (risque d'abus/DoS)
- Pas de configuration CORS (problème pour frontend sur domaine différent)
- Validation mot de passe faible (accepte "testpass123")
- Security headers incomplets

## Problème

Sans couches de sécurité supplémentaires, le système est vulnérable à:
- **Attaques par force brute** sur login (pas de rate limiting)
- **Abus d'API** (spam de requêtes, épuisement de ressources)
- **Cross-Origin attacks** (CORS non configuré)
- **Mots de passe faibles** (facilement crackables)
- **Manque de security headers** (pas de HSTS, CSP, etc.)

## Alternatives

### Option 1: Ignorer la sécurité
- **Avantages**: Code simple, pas de dépendances
- **Inconvénients**: Système très vulnérable, inacceptable même en dev
- **Rejeté**: En contradiction avec la pédagogie (apprendre la sécurité)

### Option 2: Sécurité minimaliste (CORS uniquement)
- **Avantages**: Simple, résout le problème cross-origin
- **Inconvénients**: Rate limiting et validation toujours manquants
- **Rejeté**: Insuffisant pour un projet pédagogique

### Option 3: Sécurité complète (Rate limiting + CORS + Validation + Headers)
- **Avantages**: Couvre toutes les vulnérabilités connues, patterns standard
- **Inconvénients**: Plus complexe, dépendances supplémentaires
- **Choisi**: Meilleur compromis pédagogique et pratique

## Décision

Implémenter une stratégie de sécurité multicouche avec:
1. **Rate limiting** avec `django-ratelimit`
2. **CORS** avec `django-cors-headers`
3. **Validation mot de passe** avec `django-password-validators`
4. **Security headers** via Django settings

### Bibliothèques ajoutées
- `django-ratelimit==4.1.0` - Rate limiting flexible
- `django-cors-headers==4.3.1` - Configuration CORS
- `django-password-validators==1.5.0` - Validation mot de passe

### Configuration par composant

| Composant | Limite | Scope |
|-----------|--------|-------|
| API REST | 100 req/min par IP | Global |
| API REST | 1000 req/min par utilisateur | Authentifié |
| GraphQL | 100 req/min par IP | Global |
| WebSocket | 10 connexions par IP | Global |
| Login | 5 tentatives par IP par 15 min | Auth |
| Inscription | 3 tentatives par IP par heure | Auth |

### Implémentation

**Rate limiting:**
- Middleware Django Ratelimit
- Décorateurs sur endpoints sensibles
- Limites différentes par type d'utilisateur

**CORS:**
- django-cors-headers middleware
- Autoriser localhost pour développement
- Configuration stricte pour production

**Validation mot de passe:**
- Django password validators dans settings
- 8 caractères minimum
- Complexité: majuscule, minuscule, chiffre, spécial

**Security headers:**
- HSTS (HTTP Strict Transport Security)
- CSP (Content Security Policy)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Referrer-Policy: same-origin

## Conséquences

### Positives
- Protection contre les attaques par force brute
- Protection contre l'abus d'API
- Mots de passe plus robustes
- Cross-origin correctement géré
- Security headers standards
- Apprentissage des patterns de sécurité (rate limiting, CORS, headers)

### Négatives
- Complexité accrue du code
- Dépendances supplémentaires
- Configuration CORS à ajuster pour production
