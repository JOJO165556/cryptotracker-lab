# ADR-001 — Architecture interne des modules : Clean Architecture pragmatique

**Statut** : Acceptée

## Contexte

Le projet est un monolithe modulaire (voir vision globale). Il faut décider comment
structurer l'intérieur de chaque module (`wallet`, `market`, `trading`...) pour que
la logique métier reste indépendante de Django, testable seule, et que Django reste
un détail d'implémentation plutôt que le centre du système.

Django impose par convention un fichier `models.py` à la racine de chaque app pour
les migrations — cette contrainte technique ne doit pas dicter où vit la logique métier.

## Décision

Chaque module est structuré en 4 dossiers :

- `domain/` — entités et règles métier pures. **Aucun import Django.** C'est le
  centre du module ; rien n'en dépend, il ne dépend de rien.
- `application/` — cas d'usage qui orchestrent le domaine (ex. "exécuter un ordre").
  Dépend uniquement du domaine.
- `infrastructure/` — détails techniques : ORM Django, clients externes, repositories.
  Dépend du domaine, jamais l'inverse.
- `interfaces/` — points d'entrée : routers Django Ninja, schemas, consumers WebSocket.
  Dépend de `application/`/`domain/`, jamais l'inverse.

**Règle de dépendance** : toutes les dépendances pointent vers `domain/`, jamais
l'inverse. C'est le principe d'inversion de dépendances.

**Place de `models.py`** : reste à la racine du module (contrainte Django pour les
migrations) mais n'est **pas** l'objet métier. C'est un détail d'`infrastructure/`.
L'objet métier réel (ex. `Wallet` avec ses règles) vit dans `domain/`.
`infrastructure/` fait la traduction entre les deux (ex. un `WalletRepository` qui
charge un `models.Wallet` et construit/persiste un `domain.Wallet`).

## Alternatives considérées

- **Hexagonale stricte (ports/adapters explicites)** : rejetée — trop de cérémonie
  pour la taille du projet, sans bénéfice pédagogique supplémentaire par rapport à
  la version pragmatique.
- **Clean Architecture à la lettre (4 cercles concentriques, use cases/boundaries
  formalisés)** : rejetée — surdimensionné pour un projet solo d'apprentissage.
- **Tout dans `models.py`/vues Django classiques (pas de séparation)** : rejetée —
  c'est justement le couplage que le projet doit servir à comprendre et éviter.

## Conséquences

- Chaque nouvelle entité métier s'écrit d'abord dans `domain/`, sans se soucier de Django.
- Toute logique métier trouvée dans un `models.py`, un router Ninja ou une vue est un
  signal qu'elle doit être déplacée vers `domain/` ou `application/`.
- Léger surcoût d'écriture (traduction modèle ORM ↔ objet domaine dans `infrastructure/`),
  accepté comme coût pédagogique volontaire.
- Le test de validité de cette architecture : `domain/` doit pouvoir être testé et
  compris sans jamais lancer Django.
