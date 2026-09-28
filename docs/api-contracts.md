# API Contracts — Vue globale avec détails d'implémentation

> Contrats réels (requêtes/réponses) pour tous les protocoles, sur l'ensemble du
> projet. Sert de référence directe à l'implémentation — s'enrichit si un détail
> manque, mais la structure ci-dessous est stable.

## REST

### POST /api/v1/auth/register
```json
// Request
{ "email": "jo@example.com", "username": "jo", "password": "***" }
// 201 Response
{ "id": "uuid", "email": "jo@example.com", "username": "jo" }
// Erreurs: 400 (validation), 409 (email déjà utilisé)
```

### POST /api/v1/auth/login
```json
// Request
{ "email": "jo@example.com", "password": "***" }
// 200 Response
{ "access_token": "jwt", "refresh_token": "jwt", "expires_in": 3600 }
// Erreurs: 401 (identifiants invalides)
```

### GET /api/v1/wallet   (auth requise, Bearer token)
```json
// 200 Response
{ "balance": "12420.00", "currency": "USD",
  "assets": [ { "symbol": "BTC", "quantity": "0.024", "value": "2496.00" } ] }
```

### GET /api/v1/assets/{symbol}
```json
// 200 Response
{ "symbol": "BTC", "name": "Bitcoin", "price": "104000.00", "updated_at": "..." }
// Erreurs: 404 (actif inconnu)
```

### POST /api/v1/orders   (Idempotency-Key en header, requis)
```json
// Request
{ "asset_symbol": "BTC", "side": "BUY", "quantity": "0.001" }
// 201 Response
{ "id": "uuid", "status": "EXECUTED", "price_at_order": "104000.00" }
// Erreurs: 400, 401, 409 (solde insuffisant OU rejeu de idempotency-key), 422
```

### GET /api/v1/orders / GET /api/v1/transactions / POST /api/v1/alerts / DELETE /api/v1/alerts/{id}
Même structure : pagination (`?page=`, `?page_size=`), format standard
`{ "count", "next", "previous", "results": [...] }`.

## WebSocket

```
Connexion : wss://.../ws/market/{symbol}
Handshake : Sec-WebSocket-Protocol: v1

// Message serveur → client (push, toutes les ~1s ou sur variation)
{ "type": "price_update", "symbol": "BTC", "price": "104032.50", "ts": 1234567890 }

// Message client → serveur (souscription à d'autres symboles sur la même connexion)
{ "type": "subscribe", "symbols": ["ETH", "SOL"] }

// Fermeture propre
{ "type": "close", "reason": "client_disconnect" }
```

Pipeline interne : Market Provider → Market Service → Redis Pub/Sub → WebSocket Gateway → Client.

## SSE : Notifications (flux serveur vers client uniquement)

```
GET /api/v1/notifications/stream   (auth requise, Bearer token)
Content-Type: text/event-stream

event: notification
data: {"type": "ALERT", "asset_symbol": "BTC", "message": "BTC a dépassé 105000"}

event: notification
data: {"type": "TRANSACTION", "order_id": "uuid", "message": "Achat exécuté"}
```

Contrairement au marché (WebSocket, bidirectionnel : le client souscrit et se désouscrit), les notifications sont un flux à sens unique : SSE suffit, plus simple qu'un WebSocket (HTTP standard, reconnexion automatique native côté navigateur).

Le flux est un push du nouveau uniquement : à la connexion, il démarre à l'instant présent et ne rejoue pas les notifications déjà existantes, que `GET /api/v1/notifications/` sert. Un commentaire `: keepalive` est envoyé quand il n'y a rien à émettre, pour maintenir la connexion ouverte à travers les proxys.

## GraphQL

```graphql
type Wallet { balance: Decimal!, assets: [WalletAsset!]! }
type WalletAsset { symbol: String!, quantity: Decimal!, value: Decimal! }
type Query {
  me: User!
  dashboard: Wallet!
}
```
```graphql
query Dashboard {
  dashboard { balance assets { symbol quantity value } }
}
```
Résolveur `dashboard` doit utiliser un DataLoader pour éviter le N+1 sur `assets → asset`.

## gRPC — Order Engine (proto sketch)

```protobuf
service OrderEngine {
  rpc ExecuteOrder (OrderRequest) returns (OrderResult);
  rpc GetOrderStatus (OrderId) returns (OrderStatus);
}
message OrderRequest { string wallet_id = 1; string asset_symbol = 2; string side = 3; string quantity = 4; string idempotency_key = 5; }
message OrderResult { string order_id = 1; string status = 2; }
```
Appelé en interne par Django (pas exposé publiquement). Timeout côté client : 2s, retry x1.

## JSON-RPC — Analytics

```json
// Request
{ "jsonrpc": "2.0", "method": "calculate_rsi", "params": {"symbol": "BTC", "period": 14}, "id": 1 }
// Response
{ "jsonrpc": "2.0", "result": {"rsi": 62.4}, "id": 1 }
```

## Webhooks

**Entrant** — `POST /webhooks/payment`

La route est hors du préfixe `/api` : elle est appelée par le prestataire, pas par un client de l'API.

```json
Header: X-Timestamp: 1759000000
Header: X-Signature: hmac_sha256(secret, "<X-Timestamp>." + corps)
{ "provider_ref": "pay_123", "wallet_id": "uuid", "amount": "500.00", "status": "CONFIRMED" }
```

La signature porte le timestamp, pas seulement le corps : c'est ce qui empêche de rejouer une capture. Tolérance de 5 minutes sur le timestamp.

Réponses :
| Code | Sens |
|---|---|
| 200 | message pris en charge, traitement lancé en file (`duplicate: true` si déjà vu) |
| 400 | corps invalide, ou timestamp absent / hors tolérance (rejeu) |
| 401 | signature invalide |

Le 200 signifie « message reçu », pas « argent crédité » : le crédit est fait par une tâche Celery dans un autre processus. Un `provider_ref` déjà connu reçoit un 200 mais ne réempile pas de tâche. Le webhook en double crédite une seule fois, garantie par la contrainte d'unicité sur `provider_ref` et par la clé d'idempotence `payment:<provider_ref>` dans le ledger.

Voir [ADR-009](adr/ADR-009-webhooks-inbound-async.md).

**Sortant** (ex. notification externe) : prévu en phase 17, avec retry en backoff exponentiel (1s, 2s, 4s...), 5 tentatives max, puis dead-letter queue.

## SOAP — LegacyBank (simulation, squelette)

```xml
<soap:Envelope>
  <soap:Header/>
  <soap:Body>
    <CheckBalanceRequest><AccountId>...</AccountId></CheckBalanceRequest>
  </soap:Body>
</soap:Envelope>
```
WSDL minimal avec 2 opérations (`CheckBalance`, `TransferFunds`), fautes remontées via `<soap:Fault>`.

## Cohérence transverse

- L'idempotence (`Idempotency-Key` REST, `idempotency_key` gRPC, `provider_ref` webhook) suit
  la même règle domaine : `Order.execute()` refuse toute ré-exécution — un seul point de vérité.
- Les erreurs métier (solde insuffisant, actif inconnu) sont levées dans la couche `domain`
  et traduites différemment selon le protocole (HTTP 409, gRPC status `FAILED_PRECONDITION`,
  JSON-RPC `error.code`) — jamais réimplémentées.
