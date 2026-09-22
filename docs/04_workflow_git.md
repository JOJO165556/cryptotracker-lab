# 04 — Workflow Git : tickets, branches, commits, PR (post-setup)

> Règle de base : **1 ticket = 1 branche = 1 responsabilité**. Une branche ne mélange
> jamais deux couches (domain + interface) ni deux modules. Si une branche touche
> plus de ~5-6 fichiers de nature différente, elle est trop grosse : on la scinde.

## Conventions générales

**Nommage des branches**
```
<type>/<module>-<sujet>
```
Types : `feat`, `fix`, `test`, `docs`, `refactor`, `chore`, `perf`.
Exemples : `feat/wallet-domain-model`, `test/trading-idempotence`, `docs/adr-websocket`.

**Format des commits** (Conventional Commits)
```
<type>(<module>): <résumé impératif court>
```
Exemples : `feat(wallet): add Wallet domain entity`, `test(wallet): cover insufficient balance rule`.
2 à 5 commits par branche en moyenne — pas un seul commit fourre-tout, pas 15 micro-commits.

**Template de description de PR**
```
## Quoi
[ce qui a été ajouté/modifié, en 1-2 phrases]

## Pourquoi
[le besoin/problème qui justifie ce changement — lien vers le ticket]

## Comment tester
[commande(s) ou scénario manuel]

## Lié à
Ticket #, ADR-00X si décision structurante, dépend de PR #...
```

---

## Phase 1-2 — Besoins

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Rédiger les cas d'utilisation détaillés (achat, vente, transfert, dépôt, alerte) | `docs/use-cases-detail` | `docs: detail wallet use cases (deposit, transfer)`, `docs: detail trading and alert use cases` | Formalise acteur/précondition/scénario/exceptions pour chaque cas métier |

## Phase 3 — Domaine (par module, un ticket = un module)

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Modéliser Wallet + Transaction + règles métier | `feat/wallet-domain-model` | `feat(wallet): add Wallet entity`, `feat(wallet): add Transaction entity`, `test(wallet): cover deposit and transfer idempotency rules` | Entités domain pures pour les mouvements d'argent, testées sans Django |
| Modéliser Order / Trade Execution | `feat/trading-domain-model` | `feat(trading): add Order entity`, `feat(trading): add Trade execution`, `test(trading): cover order matching logic` | Entités domain pures pour les ordres d'achat/vente et leur exécution |
| Modéliser Asset/Price | `feat/market-domain-model` | `feat(market): add Asset and Price entities` | — |
| Modéliser PriceAlert | `feat/notification-domain-model` | `feat(notification): add PriceAlert entity`, `feat(notification): prevent re-trigger` | — |

## Phase 5 — Contrats API (déjà en grande partie fait via `api-contracts.md`)

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Ajuster les contrats REST/GraphQL avant implémentation module Wallet | `docs/api-contracts-wallet` | `docs(api): finalize wallet endpoints` | Verrouille le contrat avant code |

## Phase 7 — REST (module Wallet, un ticket par couche)

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Persistence Wallet (ORM + repository) | `feat/wallet-infrastructure` | `feat(wallet): add Django model`, `feat(wallet): add WalletRepository`, `test(wallet): repository integration test` | Traduction domain ↔ ORM |
| Cas d'usage Wallet (application) | `feat/wallet-application` | `feat(wallet): add GetWalletUseCase`, `feat(wallet): add ExecuteOrderUseCase` | Orchestration, dépend du domaine seul |
| API Ninja Wallet (interfaces) | `feat/wallet-interfaces-rest` | `feat(wallet): add ninja router`, `feat(wallet): add schemas`, `test(wallet): api tests` | Endpoints REST exposés, testés end-to-end |
| Auth JWT | `feat/identity-auth-jwt` | `feat(identity): add register endpoint`, `feat(identity): add jwt login` | Prérequis pour sécuriser les endpoints Wallet |

*(Le module Trading suit exactement le même découpage en 3 PR : infrastructure → application → interfaces.)*

## Phase 8 — WebSocket

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Redis pub/sub côté Market | `feat/market-price-publisher` | `feat(market): publish price updates to redis` | Producteur seul, testable isolément |
| Gateway WebSocket | `feat/market-websocket-gateway` | `feat(market): add websocket consumer`, `test(market): consumer subscribe/unsubscribe` | Dépend de la PR précédente déjà mergée |
| ADR décision WebSocket | `docs/adr-websocket` | `docs: add ADR-003 websocket for market data` | Rédigée seulement une fois le besoin réel mesuré |

## Phase 9 — GraphQL

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Schema + resolver Dashboard | `feat/dashboard-graphql-schema` | `feat(dashboard): add graphql schema`, `feat(dashboard): add resolver` | — |
| DataLoader (anti N+1) | `feat/dashboard-graphql-dataloader` | `feat(dashboard): add dataloader for wallet assets`, `test: verify query count` | Séparée pour isoler la correction de perf |

## Phase 10 — gRPC (Order Engine)

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Définir le .proto | `feat/order-engine-proto` | `feat(order-engine): define grpc contract` | Contrat avant implémentation |
| Service Order Engine (FastAPI) | `feat/order-engine-service` | `feat(order-engine): implement ExecuteOrder`, `test(order-engine): grpc service test` | Service séparé, dépôt ou dossier isolé |
| Client gRPC côté Django | `feat/trading-grpc-client` | `feat(trading): add grpc client`, `test(trading): mock grpc call` | — |

## Phase 11 — JSON-RPC (Analytics)

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Endpoints JSON-RPC analytics | `feat/analytics-jsonrpc` | `feat(analytics): add calculate_rsi`, `feat(analytics): add calculate_sma`, `test(analytics): rpc methods` | — |

## Phase 12 — Webhooks

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Webhook entrant + vérif HMAC | `feat/payment-webhook-inbound` | `feat(payment): verify hmac signature`, `feat(payment): idempotent processing` | — |
| Traitement async Celery | `feat/payment-webhook-async` | `feat(payment): add celery task`, `test(payment): retry on failure` | Dépend de la PR précédente |

## Phase 13 — SOAP (LegacyBank simulé)

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| WSDL + opérations simulées | `feat/legacybank-soap-stub` | `feat(legacybank): add wsdl`, `feat(legacybank): add CheckBalance stub` | Étiqueté clairement comme simulation dans la PR |

## Phase 14 — Frontend

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Dashboard minimal (REST + GraphQL) | `feat/frontend-dashboard` | `feat(frontend): wallet view`, `feat(frontend): market view` | — |
| Prix temps réel (WebSocket) | `feat/frontend-realtime-prices` | `feat(frontend): connect websocket`, `feat(frontend): live price update` | Séparée pour isoler la logique temps réel |

## Phase 15 — Tests (transverses, par type)

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Scénario bout-en-bout achat | `test/e2e-buy-flow` | `test: e2e create wallet to buy btc` | Un scénario = une PR, pas tous les scénarios ensemble |

## Phase 16 — Performance

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Bench REST vs gRPC | `chore/bench-rest-vs-grpc` | `chore: add benchmark script`, `docs: record results` | Résultats documentés, pas juste le script |
| Bench charge WebSocket | `chore/bench-websocket-load` | `chore: add load test script` | — |

## Phase 17 — Résilience

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Circuit breaker sur appel gRPC | `feat/trading-circuit-breaker` | `feat(trading): add circuit breaker`, `test(trading): simulate grpc outage` | — |
| Retry + dead-letter webhook | `feat/payment-retry-dlq` | `feat(payment): exponential backoff retry`, `feat(payment): dead letter queue` | — |

## Phase 18 — Sécurité

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Rate limiting API | `feat/security-rate-limiting` | `feat(core): add rate limiting middleware` | — |
| CORS pour le frontend | `feat/security-cors` | `feat(core): configure cors` | Ajoutée seulement quand le frontend existe (phase 14 faite) |

## Phase 19 — Observabilité

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| Logging structuré | `feat/observability-logging` | `feat(core): structured logging` | — |
| Trace ID bout-en-bout | `feat/observability-tracing` | `feat(core): add trace id middleware`, `feat(order-engine): propagate trace id` | Touche deux services → bien expliquer dans "Comment tester" |

## Phase 20 — Documentation

| Ticket | Branche | Commits | PR (résumé) |
|---|---|---|---|
| README de synthèse | `docs/final-readme` | `docs: write project readme` | — |
| ADR restantes non rédigées en cours de route | `docs/adr-cleanup` | `docs: add missing ADRs` | Vérifier qu'aucune décision structurante n'est restée non documentée |

---

## Rappel d'usage

- On n'ouvre jamais deux branches de la même phase en parallèle sans raison — merge
  puis on enchaîne, pour garder un historique linéaire et des PR petites à relire.
- Une branche `infrastructure` dépend souvent d'un `domain` déjà mergé — ne pas
  commencer une couche avant que la précédente soit revue et intégrée.
- Une PR sans "Comment tester" rempli n'est pas prête à être proposée à relecture.
