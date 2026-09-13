# 01 — Définition du projet (Cahier des charges)

## 1. Vision

CryptoTracker est une plateforme permettant à un utilisateur de suivre des actifs
numériques, gérer un portefeuille virtuel, effectuer des transactions simulées et
recevoir des informations de marché en temps réel.

Projet pédagogique : la valeur n'est pas dans le nombre de fonctionnalités mais dans
la justesse de l'architecture qui les supporte.

## 2. Objectifs

- Comprendre les différents styles d'API (REST, GraphQL, WebSocket, gRPC, JSON-RPC, Webhooks, SOAP) et leurs cas d'usage réels
- Pratiquer l'architecture modulaire (monolithe modulaire, couches domain/application/infrastructure/interfaces)
- Expérimenter la communication synchrone et asynchrone, interne et externe
- Construire un système testé, mesuré et documenté (ADR)

## 3. Hors périmètre

- Vrai trading, vrai argent, vraie banque
- Sécurité financière niveau production
- Blockchain
- Kubernetes / architecture cloud complexe
- Microservices dès le départ

## 4. Acteurs

| Acteur | Type | Rôle |
|---|---|---|
| Utilisateur | Principal | Gère son portefeuille, achète/vend, consulte le marché |
| Administrateur | Secondaire | Supervision (optionnel, tardif) |
| Market Data Provider | Système externe | Fournit les prix (réel ou mock) |
| Payment Provider | Système externe | Simule les dépôts/paiements |

## 5. Cas d'utilisation (vue globale)

```
Utilisateur
 ├── créer un compte
 ├── se connecter
 ├── consulter son portefeuille
 ├── consulter un actif / le marché
 ├── acheter virtuellement
 ├── vendre virtuellement
 ├── consulter son historique de transactions
 ├── créer une alerte de prix
 └── recevoir des notifications
```

### Détail — Acheter un actif (exemple représentatif)
- **Acteur** : utilisateur authentifié, portefeuille actif, solde suffisant
- **Scénario** : demande d'achat → validation → vérification solde → exécution → création transaction → mise à jour portefeuille
- **Exceptions** : solde insuffisant, actif inexistant, prix indisponible, service indisponible, double requête (idempotence)

Les autres cas d'utilisation (vente, alerte, historique) suivent le même schéma
(acteur / précondition / scénario / résultat / exceptions) — à détailler au moment
de leur implémentation, pas maintenant.

## 6. Modèle de domaine (vue globale)

**Entités** : User, Wallet, Asset, WalletAsset, Order, Transaction, Price, PriceAlert, Notification, Payment

```
User
 └── Wallet
       ├── WalletAsset ── Asset
       └── Order ── Transaction
```

**Règles métier clés**
- Un utilisateur ne peut pas acheter au-delà du solde disponible dans son portefeuille
- Une transaction exécutée ne peut pas être exécutée une seconde fois (idempotence)
- Une alerte déclenchée ne doit pas être renvoyée indéfiniment

Ces règles appartiennent au domaine — pas à Django REST, GraphQL ou gRPC (elles ne
doivent jamais être dupliquées ou réinterprétées différemment selon le protocole).

## 7. Découpage fonctionnel (modules du monolithe modulaire)

Identity · Wallet · Market · Trading · Analytics · Notification · Payment

## 8. Contraintes non fonctionnelles (repères, pas de cible chiffrée figée)

- Les prix de marché doivent être reçus sans rechargement de page → temps réel (WebSocket)
- Le système doit rester testable module par module (pas de couplage fort entre domaines)
- Chaque décision structurante doit être traçable (ADR)

## 9. Livrables du projet

- Code source (monolithe modulaire Django)
- `api-contracts.md` (contrats par protocole)
- Suite de tests (unitaires, intégration, par protocole)
- `docs/adr/` (décisions d'architecture)
- README de synthèse + mesures de performance/résilience
