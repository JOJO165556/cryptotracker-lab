# 02 — Modèle de domaine (détail d'implémentation)

> Vue globale mais avec les champs, types et contraintes réels — sert de base directe
> aux modèles Django. Les règles métier sont ici, pas dans les vues/serializers.

## Diagramme relationnel

```
User 1───1 Wallet 1───* WalletAsset *───1 Asset
                 │
                 1───* Order 1───1 Transaction
                 │
                 1───* PriceAlert
User 1───* Notification
Order *───1 Payment (optionnel, si dépôt requis avant achat)
Asset 1───* Price (historique)
```

## Entités

### User
| Champ | Type | Contrainte |
|---|---|---|
| id | UUID | PK |
| email | string | unique, requis |
| username | string | unique |
| password_hash | string | — |
| created_at | datetime | auto |

### Wallet
| Champ | Type | Contrainte |
|---|---|---|
| id | UUID | PK |
| user_id | FK → User | 1-1 |
| balance | decimal(18,2) | ≥ 0 (contrainte au niveau domaine, pas juste DB) |
| currency | string | défaut "USD" |
| updated_at | datetime | auto |

### Asset
| Champ | Type | Contrainte |
|---|---|---|
| id | UUID | PK |
| symbol | string | unique, ex. "BTC" |
| name | string | ex. "Bitcoin" |
| is_active | bool | défaut true |

### WalletAsset (position détenue)
| Champ | Type | Contrainte |
|---|---|---|
| id | UUID | PK |
| wallet_id | FK → Wallet | — |
| asset_id | FK → Asset | — |
| quantity | decimal(24,8) | ≥ 0 |
| unique_together | (wallet_id, asset_id) | une ligne par actif détenu |

### Order
| Champ | Type | Contrainte |
|---|---|---|
| id | UUID | PK |
| wallet_id | FK → Wallet | — |
| asset_id | FK → Asset | — |
| side | enum | BUY / SELL |
| quantity | decimal(24,8) | > 0 |
| price_at_order | decimal(18,8) | prix figé au moment de l'ordre |
| status | enum | PENDING / EXECUTED / FAILED |
| idempotency_key | string | unique, requis (évite le double achat) |
| created_at | datetime | auto |

### Transaction
| Champ | Type | Contrainte |
|---|---|---|
| id | UUID | PK |
| order_id | FK → Order | 1-1 |
| amount | decimal(18,2) | — |
| executed_at | datetime | auto |

### Price (historique marché)
| Champ | Type | Contrainte |
|---|---|---|
| id | UUID | PK |
| asset_id | FK → Asset | — |
| value | decimal(18,8) | — |
| recorded_at | datetime | indexé (requêtes temporelles fréquentes) |

### PriceAlert
| Champ | Type | Contrainte |
|---|---|---|
| id | UUID | PK |
| user_id | FK → User | — |
| asset_id | FK → Asset | — |
| target_price | decimal(18,8) | — |
| direction | enum | ABOVE / BELOW |
| triggered_at | datetime\|null | null tant que non déclenchée ; une fois posée, ne se redéclenche pas |

### Notification
| Champ | Type | Contrainte |
|---|---|---|
| id | UUID | PK |
| user_id | FK → User | — |
| type | enum | ALERT / TRANSACTION / SYSTEM |
| payload | JSON | — |
| read_at | datetime\|null | — |

### Payment
| Champ | Type | Contrainte |
|---|---|---|
| id | UUID | PK |
| wallet_id | FK → Wallet | — |
| amount | decimal(18,2) | > 0 |
| provider_ref | string | référence externe (idempotence webhook) |
| status | enum | PENDING / CONFIRMED / FAILED |

## Règles métier (implémentées dans la couche `domain`, testées indépendamment de Django)

1. `Wallet.can_afford(order)` → refuse si `quantity * price_at_order > balance`
2. `Order.execute()` → idempotent via `idempotency_key` (contrainte unique DB + vérif applicative)
3. `PriceAlert.trigger()` → une fois `triggered_at` renseigné, ne se redéclenche jamais tant qu'elle n'a pas été réinitialisée par l'utilisateur

## Découpage par module (rappel)

| Module | Entités portées |
|---|---|
| Identity | User |
| Wallet | Wallet, WalletAsset, Payment |
| Market | Asset, Price |
| Trading | Order, Transaction |
| Analytics | (lit Price, ne stocke rien de nouveau) |
| Notification | Notification, PriceAlert |
