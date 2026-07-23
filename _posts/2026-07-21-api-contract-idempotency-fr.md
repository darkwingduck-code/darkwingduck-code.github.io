---
title: "Conception d'API contract-first : erreurs, versions, idempotence et tâches asynchrones"
date: 2026-07-21 10:30:00 +0900
categories: [Software Engineering, API Design]
tags: [api, openapi, idempotency, schema, pagination, versioning]
description: "Considérer une API comme un contrat durable qui évolue, plutôt que comme un ensemble de fonctions, et concevoir en conséquence ses requêtes, réponses, erreurs, nouvelles tentatives et versions."
lang: fr-FR
hidden: true
translation_key: api-contract-idempotency
---

{% include language-switcher.html %}

La qualité d'une API ne doit pas se mesurer au nombre d'endpoints, mais à la capacité de **ses appelants à prévoir les succès, les échecs et les nouvelles tentatives**. L'implémentation du serveur évolue, tandis que le contrat subsiste longtemps dans de multiples clients et systèmes automatisés.

## Un contrat ne se limite pas à la réponse en cas de succès

Le contrat d'une opération comprend au minimum les éléments suivants.

- Méthode et chemin
- Exigences d'authentification et d'autorisation
- Schémas du chemin, de la requête, des en-têtes et du corps
- Unités, fuseaux horaires, plages de valeurs et règles de nullabilité
- Codes de statut de succès et schémas de réponse
- Codes d'erreur et possibilité de réessayer
- Règles d'idempotence et de concurrence
- Limitation du débit et pagination
- Timeout ou mode de traitement asynchrone

Une spécification lisible par une machine, telle qu'OpenAPI, ne sert pas uniquement à générer de la documentation. C'est le point de référence qui relie la validation des schémas, la génération des clients, les tests de contrat et la détection des changements incompatibles.

## Distinguer les ressources des tâches

Les ressources désignées par des noms représentent un état, tandis que les méthodes HTTP expriment une intention.

```text
GET    /v1/jobs/{job_id}
POST   /v1/jobs
PATCH  /v1/jobs/{job_id}
DELETE /v1/jobs/{job_id}
```

Ne laissez pas une connexion HTTP synchrone ouverte jusqu'à l'achèvement d'une tâche qui dure plusieurs minutes.

1. `POST /v1/jobs` valide les données d'entrée et enregistre une tâche.
2. Le serveur renvoie `202 Accepted`, un `job_id` et une URL de statut.
3. Le client interroge périodiquement le statut ou reçoit un webhook ou un événement.
4. Les états sont explicités, par exemple `queued → running → succeeded | failed | cancelled`.

Les transitions d'état doivent être unidirectionnelles et distinguer le motif de l'échec de la possibilité de relancer la tâche.

## Valider strictement les entrées à la frontière

```yaml
components:
  schemas:
    CreateJobRequest:
      type: object
      additionalProperties: false
      required: [source_uri, mode]
      properties:
        source_uri:
          type: string
          format: uri
        mode:
          type: string
          enum: [quick, full]
```

Ce qui compte, ce n'est pas la syntaxe YAML, mais la politique appliquée.

- Décidez si les champs inconnus doivent être rejetés ou ignorés.
- Distinguez une omission d'un `null` explicite.
- Faites apparaître les unités numériques et les plages autorisées dans les noms, les descriptions et la validation.
- Échangez les instants dans un format standard comportant un décalage et définissez la référence interne.
- Lors de l'ajout d'une valeur d'énumération, réfléchissez à la réaction des anciens clients.

## Les erreurs ont elles aussi un schéma stable

Renvoyer uniquement une phrase destinée aux humains oblige le client à analyser du texte.

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "The request failed validation.",
    "details": [
      {"field": "mode", "reason": "unsupported_value"}
    ],
    "request_id": "req-example",
    "retryable": false
  }
}
```

- `code` est un identifiant stable qui permet à la machine de choisir une branche de traitement.
- `message` est destiné aux utilisateurs ou aux opérateurs.
- `details` structure les problèmes champ par champ.
- `request_id` relie les demandes d'assistance aux traces.
- Ne renvoyez pas à l'extérieur les stack traces, requêtes SQL, chemins ou secrets internes.

## Les nouvelles tentatives de POST exigent une clé d'idempotence

Si la connexion est interrompue après l'envoi d'une requête par le client, mais avant la réception de la réponse, celui-ci ne peut pas savoir si la tâche a été créée. Réenvoyer systématiquement le POST peut créer un doublon.

```text
Idempotency-Key: client-generated-unique-key
```

Le déroulement de base côté serveur est le suivant.

1. Rechercher un enregistrement existant à partir de la combinaison de l'identité authentifiée et de la clé.
2. Lors de la première requête, stocker le résultat avec un hash normalisé du corps de la requête.
3. Pour la même clé et le même corps, renvoyer le résultat stocké.
4. Pour la même clé et un corps différent, rejeter la requête comme un conflit.
5. Documenter la durée de conservation et les règles de traitement des requêtes concurrentes.

Se contenter d'une « vérification préalable » dans l'application, sans contrainte d'unicité dans la base de données, crée une condition de concurrence.

## Les modifications concurrentes exigent des requêtes conditionnelles

Lorsque deux utilisateurs lisent et modifient la même ressource, la dernière écriture peut écraser le changement précédent. Le contrôle de concurrence optimiste au moyen d'un numéro de version ou d'un `ETag` constitue une solution courante.

```text
GET /v1/items/42
ETag: "version-7"

PATCH /v1/items/42
If-Match: "version-7"
```

Si la version a changé, le serveur signale un conflit afin que le client relise l'état le plus récent.

## La pagination doit résister aux changements de données

Ne renvoyez pas une longue liste en une seule fois. La pagination par offset est simple, mais des insertions ou suppressions en début de liste peuvent entraîner des doublons ou des omissions. Pour les grandes listes qui changent souvent, une pagination par curseur fondée sur une clé de tri stable est plus adaptée.

```json
{
  "items": [],
  "next_cursor": "opaque-cursor",
  "has_more": false
}
```

Traitez le curseur comme une valeur opaque et inscrivez dans le contrat l'ordre de tri, la taille maximale d'une page et les règles de combinaison des filtres avec le curseur.

## Le versionnement est une politique de changement, pas un dernier recours

Classez les changements en trois catégories.

- Compatibles : ajout d'un champ facultatif ou d'un nouvel endpoint
- Compatibles sous conditions : ajout d'une valeur d'énumération ou assouplissement d'une restriction
- Incompatibles : suppression d'un champ ou modification de son type ou de sa signification

Déplacez les changements incompatibles vers une nouvelle version explicite ou une opération parallèle. Gérez ensemble les avis d'obsolescence, les périodes d'observation, l'utilisation par les clients et le calendrier de retrait. Ajouter un numéro de version à l'URL ne suffit pas à gérer les changements.

## Tests de contrat et portes de déploiement

- Vérifier que la spécification est valide.
- Tester que les réponses du serveur sont conformes à la spécification.
- Vérifier que des clients représentatifs peuvent être générés et compilés à partir de la nouvelle spécification.
- Rechercher les changements incompatibles par rapport à la version précédente.
- Tester l'absence d'authentification, l'insuffisance des autorisations, la limitation du débit et les erreurs de validation.
- Tester des requêtes concurrentes portant la même clé d'idempotence.
- Effectuer un smoke test des endpoints essentiels après le déploiement.

## Liste de vérification

- [ ] Les schémas d'erreur sont précisés au même titre que les schémas de requête et de réponse.
- [ ] Les politiques relatives aux unités, aux fuseaux horaires, aux valeurs nullables et à l'extension des énumérations sont claires.
- [ ] Une stratégie de prévention des doublons existe pour les requêtes POST à effets de bord.
- [ ] Les traitements longs sont séparés dans une ressource de statut.
- [ ] Les pertes de mises à jour dues aux modifications concurrentes sont évitées.
- [ ] L'ordre de pagination est déterministe et le curseur est opaque.
- [ ] La CI détecte les changements incompatibles.
- [ ] Les stack traces et les détails d'implémentation internes ne sont pas exposés dans les erreurs externes.

## Échecs courants

- Renvoyer tous les résultats avec `200 OK` et du JSON sans structure imposée.
- Ne pas distinguer les erreurs temporaires, qui autorisent une nouvelle tentative, des erreurs définitives.
- Créer une tâche après le timeout du client sans empêcher les doublons.
- Employer des unités ou des fuseaux horaires différents pour un même champ selon l'endpoint.
- Supprimer un champ de réponse et « ne modifier que la documentation ».
- Omettre des données lorsqu'elles changent au cours d'une pagination par offset.

Une bonne API masque les détails d'implémentation tout en **décrivant suffisamment son comportement pour permettre aux appelants d'échouer et de réessayer en toute sécurité**.

## Références

- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)
- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
