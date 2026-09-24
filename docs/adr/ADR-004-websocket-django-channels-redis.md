# ADR-004 : Architecture de diffusion en temps réel via WebSocket, Django Channels et Redis Pub/Sub

* **Statut** : Accepté

* **Contexte** : Phase 8 (Diffusion des flux de marché en temps réel)

## 1. Contexte & Problématique

Pour offrir une expérience de trading réactive, l'application doit notifier immédiatement les clients de toute variation des prix du marché. 

L'approche REST polling classique présente plusieurs inconvénients majeurs :
* Une surcharge inutile des requêtes HTTP (overhead réseau et serveur).
* Un délai de latence important entre la modification d'un prix et son affichage côté client.
* Un manque de scalabilité lorsque le nombre d'utilisateurs simultanés augmente.

Nous avions besoin d'un mécanisme de push bidirectionnel et asynchrone capable de diffuser les prix instantanément dès que l'événement `UpdatePriceUseCase` est exécuté.

## 2. Décisions prises

### A. Adoption de WebSocket & Django Channels (Interface Async)
* **WebSocket** est retenu comme protocole de communication principal pour les flux en temps réel (`wss://`).
* **Django Channels** (avec le serveur ASGI **Daphne**) est utilisé pour étendre Django au-delà du protocole HTTP standard et gérer les connexions asynchrones persistantes via des `Consumers`.

### B. Couplage via Redis Pub/Sub (`Channel Layer`)
* Le cas d'usage REST/Domaine `UpdatePriceUseCase` déclenche une publication vers **Redis Pub/Sub** via `RedisMarketPublisher`.
* Redis agit comme courtier d'événements (Event Bus) découplé.
* Le `MarketPriceConsumer` de Django Channels est abonné aux canaux Redis `market_price_{symbol}` et redistribue immédiatement le message JSON à l'ensemble des clients connectés sur le WebSocket correspondant (`ws/market/{symbol}/`).

## 3. Alternative évaluée

* **Server-Sent Events (SSE)** :
  * *Avantage* : Unidirectionnel, très simple à implémenter sur du HTTP classique.
  * *Inconvénient* : Support natif limité pour le découplage bidirectionnel futur et intégration moins fluide avec l'écosystème asynchrone Django comparé à Channels.

## 4. Conséquences & Bénéfices

* **Découplage strict (Clean Architecture)** : La couche domaine/use-case ignore l'existence des WebSockets. Elle se contente d'émettre sur Redis Pub/Sub.
* **Performance** : Latence quasi nulle (inférieure à 10ms en local) entre l'exécution REST du changement de prix et sa réception par le client WebSocket.
* **Scalabilité horizontale** : L'utilisation de Redis en tant que `Channel Layer` permet d'exécuter plusieurs instances de serveurs ASGI/Channels sans perte de synchronisation des messages.