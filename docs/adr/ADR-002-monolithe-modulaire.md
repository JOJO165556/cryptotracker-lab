# ADR-002 — Monolithe modulaire comme architecture système

**Statut** : Acceptée

## Contexte

Le projet doit expérimenter plusieurs styles de communication (REST, GraphQL,
WebSocket, gRPC, JSON-RPC, Webhooks, SOAP) et plusieurs patterns d'architecture,
dans un but pédagogique. Le risque principal identifié dès la phase 0 : viser une
architecture microservices "pour le portfolio" sans qu'aucun problème réel
(scalabilité, déploiement indépendant, équipes séparées) ne le justifie.

## Décision

Le système est un **monolithe modulaire** : un seul déploiement Django, découpé en
modules métier (`identity`, `wallet`, `market`, `trading`, `analytics`,
`notification`, `payment`), chacun structuré en couches internes
(voir ADR-001 — Clean Architecture pragmatique).

Seule exception ponctuelle : un service séparé (`Order Engine`) pourra être extrait
en gRPC/FastAPI à la phase 10, mais uniquement pour expérimenter la communication
inter-services — pas parce que le monolithe serait devenu un problème réel.

## Alternatives considérées

- **Microservices dès le départ** : rejetée — aucun problème réel (charge, équipes,
  déploiement indépendant) ne le justifie ; le coût (réseau, observabilité distribuée,
  cohérence des données) serait payé sans bénéfice pédagogique proportionnel.
- **Monolithe non modulaire (tout mélangé)** : rejetée — empêche d'apprendre la
  séparation des responsabilités, qui est un objectif explicite du projet.

## Conséquences

- Un seul processus/déploiement à gérer pendant l'essentiel du projet — moins de
  friction infra, plus de temps consacré à l'architecture applicative elle-même.
- Le découplage entre modules doit être maintenu par discipline (pas d'import direct
  d'un module à un autre via son `infrastructure/` ou son `models.py` — passage par
  des interfaces explicites si besoin).
- Si un jour un module devait être extrait en service séparé, la frontière modulaire
  déjà posée rend cette extraction possible sans réécriture complète — mais ce n'est
  pas un objectif du projet, juste une conséquence positive du choix.
