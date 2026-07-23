---
title: "Une stratégie de vérification logicielle fondée sur les risques, au-delà de la pyramide des tests"
date: 2026-07-21 10:40:00 +0900
categories: [Software Engineering, Testing]
tags: [testing, pytest, contract-testing, property-testing, integration-testing, quality]
description: Ce guide explique comment combiner tests unitaires, d'intégration, de contrat et E2E selon les risques, et comment concevoir de bons oracles et invariants.
lang: fr-FR
hidden: true
translation_key: software-testing-strategy
---

{% include language-switcher.html %}

Le but des tests n'est pas d'exécuter des lignes de code, mais de **détecter les défaillances importantes avant la publication et de produire la preuve que les contrats restent respectés après une modification**. Même avec une couverture élevée, la confiance reste faible si les assertions sont faibles ou si les risques réels ne sont pas exercés.

## Concevoir les tests à rebours à partir des risques

Commencez par consigner les modes de défaillance.

| Mode de défaillance | Impact | Vérification adaptée |
|---|---|---|
| Erreur de classement d'une valeur limite | Décision erronée | Tests unitaires et de valeurs limites |
| Incompatibilité du schéma de la base de données | Échec de toute la requête | Tests d'intégration et de migration |
| Rupture du contrat client/serveur | Échec de l'intégration après déploiement | Tests de contrat |
| Contournement de l'authentification | Accès non autorisé | Tests de sécurité et d'intégration |
| Configuration de déploiement manquante | Échec au démarrage du service | Test de fumée |
| Rupture d'un long parcours utilisateur | Interruption d'une activité essentielle | Petit nombre de tests E2E |

Automatisez d'abord les éléments dont la probabilité, l'impact et la difficulté de détection sont élevés. Les montants, les autorisations, les transitions d'état et les chemins pouvant entraîner une perte de données sont prioritaires par rapport aux accesseurs anodins.

## Chaque couche de tests répond à une question différente

### Tests unitaires

Ils vérifient rapidement si « une petite règle est correcte pour toutes les entrées importantes ». Ils isolent les E/S et se concentrent sur les valeurs limites, les exceptions et les invariants.

### Tests d'intégration

Ils vérifient si « les composants réels communiquent selon le même contrat ». Ils mettent à l'épreuve les différences que les simulations peuvent masquer, notamment celles liées au véritable moteur de base de données, au format de fichier, au sérialiseur ou à l'adaptateur HTTP.

### Tests de contrat

Ils vérifient si « le schéma et la sémantique convenus entre le fournisseur et le consommateur sont préservés ». Ils contrôlent le type des champs, leur caractère obligatoire ou facultatif, les codes d'erreur et la rétrocompatibilité.

### Tests E2E

Ils vérifient si « l'utilisateur obtient le résultat essentiel attendu dans le système déployé ». Comme ils sont lents et fragiles, commencez par trois à cinq parcours à forte valeur plutôt que d'automatiser chaque écran.

### Vérification après déploiement

Ne vous contentez pas de vérifier qu'un point de terminaison de santé renvoie 200. Contrôlez, au moyen d'une transaction synthétique sûre, la connexion aux dépendances essentielles, un minimum de lectures et d'écritures, les autorisations, les versions et l'état des workers en arrière-plan.

## Un bon test distingue clairement Arrange–Act–Assert

```python
def test_cancelled_job_cannot_restart() -> None:
    # Arrange
    job = Job.cancelled(id="job-example")

    # Act
    result = job.start()

    # Assert
    assert result.is_error
    assert result.code == "INVALID_STATE_TRANSITION"
    assert job.status == "cancelled"
```

Quand un test enchaîne trop d'actions, il devient difficile de savoir où se situe l'échec. À l'inverse, figer jusqu'aux méthodes privées de l'implémentation casse même les refactorisations légitimes. Vérifiez les résultats observables de l'extérieur et les invariants essentiels.

## Combiner tests par l'exemple et tests fondés sur les propriétés

Les tests par l'exemple sont faciles à lire, mais ne couvrent que les cas imaginés par les développeurs. Les tests fondés sur les propriétés vérifient, dans un vaste espace d'entrées, les caractéristiques qui doivent toujours être respectées.

Pour une fonction de normalisation, on peut par exemple envisager les propriétés suivantes.

- La sortie se trouve dans la plage autorisée.
- Normaliser deux fois la même entrée donne le même résultat.
- Modifier l'ordre des entrées ne change pas le résultat d'une agrégation indépendante de l'ordre.
- Une sérialisation suivie d'une désérialisation préserve la signification.

En calcul numérique, la tolérance d'erreur doit être justifiée. Un `epsilon` systématiquement élevé masque les erreurs, tandis qu'une égalité bit à bit rend le test instable face aux différences de plateforme. Combinez erreur absolue et erreur relative en fonction de l'échelle des valeurs et des conditions du problème.

## Choisir précisément le doublon de test

- stub : renvoie une valeur prédéfinie.
- fake : offre une implémentation de remplacement simple, mais fonctionnelle.
- spy : permet d'observer l'historique des appels.
- mock : spécifie les interactions attendues.

Une simulation du réseau est utile pour tester les règles métier. Mais simuler jusqu'aux frontières réelles, comme le dialecte SQL, les transactions ou la sérialisation, fait manquer les erreurs d'intégration. Distinguez « ce qu'il faut isoler rapidement » de « ce qu'il faut vérifier dans les conditions réelles ».

## Maîtriser le non-déterminisme

Les tests instables détruisent la confiance. Transformez le temps, l'aléatoire, le réseau, le parallélisme et l'état global en dépendances contrôlables.

```python
from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=timezone.utc)
```

Enregistrer uniquement la graine aléatoire ne garantit pas un déterminisme complet. Les versions des bibliothèques, l'exécution parallèle, les calculs propres au matériel et l'ordre des entrées peuvent aussi influer sur le résultat. Définissez d'abord le niveau de reproductibilité requis.

## Points essentiels des tests de base de données

- Chaque test utilise ses propres données et son propre espace de noms.
- Les migrations sont appliquées à la fois à une base vide et à une base de la version précédente.
- On vérifie que les contraintes d'unicité, de clé étrangère et de contrôle empêchent réellement les données invalides.
- On ne se fie pas uniquement à l'annulation de transaction : il faut aussi prendre en compte les workers en arrière-plan et les connexions distinctes.
- Les données de production ne sont pas copiées dans les fixtures de test.

## Rendre les échecs analysables

En cas d'échec dans la CI, conservez au minimum les éléments suivants.

- Nom du test et graine
- Fixture d'entrée ou entrée minimale permettant de reproduire le problème
- Version de l'application ou de la logique
- Informations sur l'environnement et le verrouillage des dépendances
- Journaux, traces et captures d'écran pertinents
- Distinction entre la première cause d'échec et les échecs qui en découlent

Une politique qui relance systématiquement les tests jusqu'à obtenir du vert dissimule les tests instables. Ceux-ci doivent être isolés et classés par cause, puis attribués à un responsable avec un délai de correction.

## Liste de contrôle de la vérification

- [ ] Chaque mode de défaillance le plus coûteux est associé au test qui le détecte.
- [ ] La valeur juste en dessous de la limite, la limite elle-même et la valeur juste au-dessus sont testées.
- [ ] On vérifie non seulement l'exception, mais aussi la préservation de l'état après l'échec.
- [ ] Des tests d'intégration couvrent les véritables frontières de base de données, de sérialisation et HTTP.
- [ ] Les ruptures de schéma sont détectées dans la CI.
- [ ] Seuls les parcours utilisateur essentiels sont maintenus sous forme de tests E2E stables.
- [ ] Le non-déterminisme lié au temps, à l'aléatoire et aux dépendances externes est maîtrisé.
- [ ] Les tests instables ne sont pas masqués par une simple relance automatique.
- [ ] Un test de fumée après déploiement et des critères de décision pour le retour arrière sont définis.

## Échecs fréquents

- Prendre le taux de couverture pour un objectif de qualité.
- Répéter le même cas nominal tout en négligeant les limites, les erreurs et la concurrence.
- Figer jusqu'au nombre d'appels internes et augmenter ainsi le coût des refactorisations.
- Partager l'ordre d'exécution et l'état global entre les tests.
- Simuler toutes les frontières externes et manquer les erreurs réelles de schéma et de transaction.
- Dépendre, dans les tests E2E, de temporisations arbitraires et de coordonnées à l'écran.

La question ultime d'une stratégie de test n'est pas « combien de tests avons-nous écrits ? », mais **« quels risques avons-nous maîtrisés, et par quelles preuves ? »**.
