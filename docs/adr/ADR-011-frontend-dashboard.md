# ADR-011 : Frontend Dashboard moderne

**Statut** : Acceptée

## Contexte

La Phase 14 de la roadmap exige un dashboard pour montrer différents protocoles API ensemble. L'objectif est de démontrer comment différents protocoles API peuvent être utilisés dans une même application : REST, GraphQL, WebSocket, SSE, JSON-RPC et SOAP. La valeur est d'afficher 6 sources de données différentes sur une seule page avec 6 mécanismes réellement différents, avec une interface moderne et professionnelle de type trading.

## Décision

L'implémentation frontend utilise HTML/JS natif sans framework, pour rester simple tout en offrant une UX moderne.

**Choix technique** :
- HTML/JS natif (pas de React, Vue, etc.)
- Interface moderne dark mode style trading
- Pages séparées : login, register, dashboard
- Navigation sidebar avec sections : Dashboard, Trading, Market, Wallet, Alerts, Legacy Bank
- Fetch API pour REST (Wallet API)
- Fetch API pour GraphQL (Dashboard query)
- Fetch API pour JSON-RPC (Analytics)
- Fetch API pour SOAP (LegacyBank avec XML)
- WebSocket API pour prix temps réel
- EventSource API pour SSE (Notifications)
- Fichiers JS séparés par protocole (rest.js, graphql.js, jsonrpc.js, soap.js, websocket.js, sse.js, app.js)
- Token JWT stocké en localStorage (compromis, voir sécurité)
- Token passé en query param pour SSE (EventSource ne supporte pas les headers custom)
- Fichiers statiques servis par Django
- CSS moderne avec variables CSS, dark mode, layout responsive

**Structure** :
```
frontend/
├── templates/
│   ├── index.html      # Dashboard principal
│   ├── login.html      # Page de connexion
│   └── register.html   # Page d'inscription
└── static/
    ├── style.css       # CSS moderne dark mode
    └── js/
        ├── rest.js        # fetch GET /api/wallets/
        ├── graphql.js      # fetch POST /graphql
        ├── jsonrpc.js      # fetch POST /api/analytics/rpc
        ├── soap.js         # fetch POST /legacybank/soap/ (XML)
        ├── websocket.js    # new WebSocket(...)
        ├── sse.js           # new EventSource(...)
        └── app.js           # Orchestration globale
```

**Architecture** :
```
Browser → Django templates (login/register/index.html) + fichiers JS séparés
  ↓
  ├─ REST API (fetch GET /api/wallets/ avec Authorization header)
  ├─ GraphQL API (fetch POST /graphql avec Authorization header)
  ├─ JSON-RPC API (fetch POST /api/analytics/rpc avec Authorization header)
  ├─ SOAP API (fetch POST /legacybank/soap/ avec XML)
  ├─ WebSocket (ws://.../ws/market/BTC avec token en query param)
  └─ SSE (EventSource /api/notifications/stream avec token en query param)
```

## Sécurité

**Token JWT en localStorage** : Compromis explicite. En production, localStorage est vulnérable au XSS. Pour ce projet, ce compromis est acceptable mais doit être documenté. Aucune donnée PII (nom d'utilisateur, email) n'est stockée dans localStorage.

**Token SSE en query param** : EventSource ne supporte pas les headers custom (comme Authorization). Le token est passé en query param (?token=...). En production, servir le frontend sur le même domaine avec un cookie de session serait préférable.

## Alternatives considérées

- **React** : Rejetée - Surdimensionné pour ce projet
- **Vue.js** : Rejetée - Surdimensionné pour ce projet
- **Next.js** : Rejetée - Contre l'ADR-002 (monolithe modulaire), pas justifié
- **HTMX** : Rejetée - Intéressant mais ajouterait une dépendance inutile pour ce cas d'usage
- **Single script fourre-tout** : Rejetée - Les fichiers séparés rendent visible que ce sont 6 mécanismes différents

## Conséquences

- Code simple et compréhensible
- Pas de build step ou dépendance frontend complexe
- Démonstration claire des différences entre protocoles API
- Structure (1 fichier JS par protocole)
- Interface de type trading avec KPIs, tableaux, temps réel