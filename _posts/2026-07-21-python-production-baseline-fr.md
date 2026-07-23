---
title: "Les exigences minimales pour transformer du code Python en logiciel exploitable en production"
date: 2026-07-21 10:10:00 +0900
categories: [Software Engineering, Python]
tags: [python, packaging, testing, typing, logging, reproducibility]
description: Ce guide présente les critères pratiques pour faire évoluer un script vers une application Python reproductible, testable et observable.
lang: fr-FR
hidden: true
translation_key: python-production-baseline
---

{% include language-switcher.html %}

Exécuter une fois un fichier Python et en faire un logiciel qui s'exécute de façon sûre et répétée dans d'autres environnements sont deux problèmes bien différents. L'essentiel d'un code exploitable ne réside pas dans un framework sophistiqué, mais dans le fait que **ses entrées, ses sorties, ses dépendances et ses échecs soient explicites**.

## 1. Commencer par définir des frontières

Le code le plus difficile à maintenir est celui qui mêle, dans une même fonction, calculs, accès aux fichiers, requêtes réseau, lecture des variables d'environnement et journalisation. Une séparation en trois couches facilite les tests et les remplacements.

1. **Logique métier** : calcul pur produisant la même sortie pour une même entrée
2. **Adaptateurs** : communication avec les fichiers, les bases de données, HTTP et les files de messages
3. **Point d'entrée** : lecture de la configuration, assemblage des objets et choix du code de sortie

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Reading:
    value: float
    lower: float
    upper: float


def classify(reading: Reading) -> str:
    if reading.lower > reading.upper:
        raise ValueError("lower must not exceed upper")
    if reading.value < reading.lower:
        return "low"
    if reading.value > reading.upper:
        return "high"
    return "normal"
```

Cette fonction ne consulte ni fichier, ni horloge, ni réseau. Les valeurs limites peuvent donc être vérifiées rapidement et les causes d'échec restent circonscrites.

## 2. Commencer par une petite structure de projet, tout en séparant les rôles

```text
project/
├── pyproject.toml
├── README.md
├── src/
│   └── app/
│       ├── __init__.py
│       ├── domain.py
│       ├── adapters.py
│       └── cli.py
└── tests/
    ├── unit/
    └── integration/
```

La disposition `src` réduit le risque que la racine du dépôt devienne par hasard un chemin d'importation et masque ainsi des erreurs de packaging. Le fichier `pyproject.toml` centralise le système de construction, les métadonnées du projet, les dépendances d'exécution et la configuration des outils de développement.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "example-app"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27,<1"]

[project.optional-dependencies]
dev = ["pytest>=8,<9", "ruff>=0.5,<1", "mypy>=1.10,<2"]
```

Ces plages de versions ne sont que des exemples. Dans un projet réel, il faut choisir une version de Python prise en charge et une stratégie unique de verrouillage, puis les appliquer à l'identique dans la CI et lors du déploiement.

## 3. Séparer la configuration des secrets

Il existe trois types de configuration.

| Type | Exemple | Emplacement de stockage |
|---|---|---|
| Valeur par défaut du code | Taille de lot, délai d'attente par défaut | Code ou fichier de configuration public |
| Configuration propre à l'environnement | Adresse de l'API, niveau de journalisation | Variable d'environnement ou configuration de déploiement |
| Secret | Jeton, mot de passe, clé privée | Gestionnaire de secrets |

Même une valeur telle que `DEBUG=true` est une chaîne de caractères. Au lieu de compter sur une conversion implicite, on la valide une fois au démarrage.

```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    timeout_seconds: float


def load_settings() -> Settings:
    base_url = os.environ["API_BASE_URL"]
    timeout = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
    if timeout <= 0:
        raise ValueError("HTTP_TIMEOUT_SECONDS must be positive")
    return Settings(api_base_url=base_url, timeout_seconds=timeout)
```

Ne laissez aucune valeur secrète dans les messages d'exception, les arguments de CLI, Git, les fixtures de test ou les sorties de notebooks. Les masquer avec `***` ne suffit pas : il est plus sûr de ne jamais les inclure dans les champs des journaux.

## 4. Les types décrivent le contrat, ils ne remplacent pas l'exécution

Les annotations de type communiquent rapidement l'intention des entrées et des sorties et réduisent les erreurs de refactorisation. Cependant, les données JSON ou CSV et les variables d'environnement venues de l'extérieur ne sont pas validées par de simples annotations. Deux couches sont nécessaires : **une validation à l'exécution à la frontière de confiance**, puis une vérification des types en interne.

- Limitez `Any` aux seules zones de migration progressive.
- Préférez une `dataclass`, un `TypedDict` ou un type de modèle porteur de sens à `dict[str, object]`.
- Précisez si `None` représente un état normal ou un état d'erreur.
- Distinguez les nombres exprimés dans des unités différentes par leur nom ou par des types distincts.

## 5. Un journal n'est pas une phrase, mais la structure d'un événement

Les journaux d'exploitation doivent pouvoir être filtrés et agrégés ultérieurement.

```python
import logging

logger = logging.getLogger(__name__)


def handle(job_id: str) -> None:
    logger.info("job_started", extra={"job_id": job_id})
    try:
        run_job(job_id)
    except TimeoutError:
        logger.exception("job_timed_out", extra={"job_id": job_id})
        raise
```

Les champs communs minimaux sont `event`, `timestamp`, `severity`, `service`, `request_id` ou `job_id`, `duration` et `outcome`. N'enregistrez pas en bloc le corps brut d'une requête ni ses en-têtes d'authentification.

## 6. Organiser les tests selon les couches de risque

```python
import pytest

from app.domain import Reading, classify


@pytest.mark.parametrize(
    ("value", "expected"),
    [(9.0, "low"), (10.0, "normal"), (20.0, "normal"), (21.0, "high")],
)
def test_classify_boundaries(value: float, expected: str) -> None:
    assert classify(Reading(value=value, lower=10.0, upper=20.0)) == expected
```

- Tests unitaires : logique pure, valeurs limites, invariants
- Tests d'intégration : adaptateurs de base de données, de fichiers et HTTP
- Tests de contrat : schémas de requête et de réponse, format des erreurs
- Tests de fumée : disponibilité des parcours essentiels après le déploiement

Simuler tous les détails d'implémentation fait passer à côté des erreurs de connexion réelles. À l'inverse, transformer tous les tests en E2E les rend lents et complique le diagnostic. Répartissez-les en couches selon le coût des échecs et la fréquence des changements.

## 7. L'arrêt et les nouvelles tentatives font aussi partie de l'API

Une CLI ou une tâche par lots doit distinguer la réussite de l'échec à l'aide de son code de sortie. Les nouvelles tentatives réseau exigent un nombre maximal, un backoff exponentiel, une gigue et une échéance globale. Ne relancez pas automatiquement une opération ayant des effets de bord sans garantie d'idempotence.

```python
def main() -> int:
    try:
        settings = load_settings()
        execute(settings)
    except ConfigurationError as exc:
        logger.error("invalid_configuration", extra={"reason": str(exc)})
        return 2
    except Exception:
        logger.exception("unhandled_failure")
        return 1
    return 0
```

## Liste de contrôle avant la mise en production

- [ ] Dans un nouvel environnement, les seules commandes de la documentation suffisent à installer et exécuter l'application.
- [ ] La version de Python et les dépendances sont déclarées, et une stratégie de verrouillage existe.
- [ ] Le schéma des entrées, leurs unités, leur plage et la politique relative aux valeurs manquantes sont validés.
- [ ] Aucun secret ne figure dans le code, l'historique Git, les journaux ou les données de test.
- [ ] La logique métier essentielle est testée sans E/S externe.
- [ ] Les délais d'attente, le budget de nouvelles tentatives et les codes de sortie sont explicites.
- [ ] Les journaux structurés permettent de suivre une requête ou une tâche.
- [ ] L'artefact de publication peut être reconstruit dans un environnement propre.

## Échecs fréquents

- Le projet ne fonctionne que dans un notebook, tandis que les importations du paquet et la CLI sont défaillantes.
- À cause d'un état global et d'effets de bord à l'importation, le résultat dépend de l'ordre des tests.
- `except Exception: pass` fait passer un échec pour une réussite.
- L'installation systématique de la version la plus récente empêche de reproduire l'environnement de la veille.
- Les journaux sont abondants, mais l'absence d'identifiants et de noms d'événements les rend impossibles à rechercher.

L'exploitabilité ne se juge pas au nombre de lignes de code, mais à **la capacité à réinstaller le logiciel, à reproduire ses échecs et à le rétablir en toute sécurité**.

## Références

- [Python Packaging User Guide — Writing `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [Python Packaging User Guide — Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
