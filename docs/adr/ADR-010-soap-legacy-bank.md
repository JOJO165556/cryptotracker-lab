# ADR-010 : SOAP pour l'intégration LegacyBank

**Statut** : Acceptée

## Contexte

La Phase 13 de la roadmap exige une intégration avec une banque legacy simulée en utilisant le protocole SOAP. SOAP est un protocole plus ancien que REST, encore utilisé dans de nombreux systèmes bancaires et d'entreprise.

## Décision

L'implémentation SOAP utilise une approche manuelle avec lxml, car les bibliothèques SOAP Python (spyne, zeep) ont des problèmes de compatibilité avec Python 3.12.

**Choix technique** :
- Implémentation manuelle de l'enveloppe SOAP avec xml.etree.ElementTree
- WSDL simplifié pour documentation
- Endpoint Django qui parse et route les requêtes SOAP
- Application business logic séparée (LegacyBankService)

**Architecture** :
```
Client → Django View → Parsing XML → LegacyBankService (business logic) → Réponse SOAP
```

## Alternatives considérées

- **spyne** : Rejetée - Problèmes de compatibilité avec Python 3.12 (syntax errors)
- **zeep** : Rejetée - C'est un client SOAP, pas un serveur. Utile seulement pour consommer un webservice SOAP tiers externe
- **suds** : Rejetée - Projet abandonné, non maintenu
- **Zato** : Rejetée - Plateforme ESB complète, surdimensionnée
- **Microservice séparé** : Rejetée - Pas justifié pour une simulation pédagogique

## Sécurité du parsing XML

Utilisation de `defusedxml.ElementTree` plutôt que `xml.etree.ElementTree` pour prévenir les attaques XXE (entités externes) sur les requêtes SOAP entrantes. C'est un choix de parseur sécurisé, pas une fonctionnalité de sécurité à ajouter plus tard.

## Conséquences

- Apprentissage du format XML et WSDL
- Comparaison SOAP vs REST vs GraphQL
- Code plus verbeux (XML vs JSON)
- Validation stricte via schéma XSD
- Intégration moderne avec systèmes legacy
- WSDL disponible sur `/legacybank/soap/?wsdl`
- Implémentation pédagogique montrant la structure SOAP
