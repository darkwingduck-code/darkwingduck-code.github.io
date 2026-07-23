---
title: "Fondements de l’orchestration avec Airflow 3 : concevoir le temps, l’état et la réexécution"
date: 2026-07-21 10:10:00 +0900
categories: [Data Engineering, Orchestration]
tags: [airflow, orchestration, data-pipelines, idempotency, observability]
description: Concevoir XCom, Connections, Variables, les nouvelles tentatives, les backfills, les capteurs différables, la planification par actifs et la vérification opérationnelle autour des DAG, tâches et intervalles de données d’Airflow 3.
lang: fr-FR
hidden: true
translation_key: airflow-3-orchestration-foundations
---

{% include language-switcher.html %}

## Le problème : enchaîner des tâches dans l’ordre ne suffit pas à rendre un pipeline exploitable

Airflow est un orchestrateur destiné à développer, planifier et observer des workflows par lots. Il ne remplace ni le moteur de calcul effectif ni un moyen de transport de données à haut débit. Méconnaître cette frontière entraîne les problèmes suivants.

- Le temps d’exécution est confondu avec la période traitée, et la mauvaise partition est lue.
- Une nouvelle tentative de tâche répète un ajout et duplique les données.
- Le passage d’un dataframe par XCom gonfle la base de métadonnées.
- Un capteur occupe longtemps un slot de worker.
- `catchup=False` est interprété à tort comme une interdiction de retraiter les données historiques.
- Les secrets et la configuration d’exécution sont écrits directement dans le code source du DAG.
- Le DAG réussit alors que la fraîcheur et la qualité de l’artefact échouent.

Un workflow Airflow exploitable doit répondre clairement à trois questions.

1. **Quel intervalle de données** cette exécution du DAG traite-t-elle ?
2. La réexécution de la même tâche produit-elle **le même état final** ?
3. Après un échec, comment vérifier non seulement l’état Airflow, mais aussi **que l’artefact destiné aux utilisateurs est sain** ?

Les API et comportements d’Airflow 3 décrits dans cet article suivent la [documentation stable officielle d’Apache Airflow 3.x](https://airflow.apache.org/docs/apache-airflow/stable/) disponible au moment de sa rédaction. Les API publiques et les arguments des opérateurs peuvent varier selon la version mineure et celle du provider ; épinglez donc également la documentation de la version déployée.

## Modèle mental : une exécution de DAG est une instance d’orchestration correspondant à un intervalle de temps ou à un événement

### Distinguer DAG, tâche, instance de tâche et exécution de DAG

- **DAG** : définition d’un workflow contenant planifications, tâches, dépendances et callbacks
- **tâche** : modèle de travail déclaré avec un Operator, un Sensor, une fonction TaskFlow `@task` ou une interface similaire
- **exécution de DAG** : exécution d’un DAG pour un intervalle logique ou un événement donné
- **instance de tâche** : exécution réelle d’une tâche dans une exécution de DAG donnée

Si la même définition de tâche s’exécute chaque jour, il n’existe qu’une tâche, mais une instance de cette tâche dans l’exécution de DAG de chaque journée. Une nouvelle tentative est une autre tentative de la même instance de tâche ; un backfill crée de nouvelles exécutions de DAG pour des intervalles historiques.

L’interface publique de création d’Airflow 3 s’articule autour de `airflow.sdk`. Les fichiers de DAG doivent utiliser les API publiques et les opérateurs des providers au lieu de manipuler les modèles de métadonnées internes. Pour les principes de base, consultez la documentation officielle [DAGs et tâches](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/).

### La date logique n’est pas le temps d’exécution réel

Une planification temporelle possède un **intervalle de données**. Si une exécution quotidienne de DAG traite `[2026-01-01 00:00, 2026-01-02 00:00)`, le planificateur crée généralement l’exécution après la fin de l’intervalle. Sa date logique représente le début de l’intervalle de données, et non l’heure réelle de démarrage.

La documentation officielle sur les [exécutions de DAG](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html) explique qu’une exécution planifiée est créée après la fin de son intervalle de données et que la date logique représente le début de cet intervalle. Choisir une partition avec `now()` peut donc conduire à lire des données différentes après un délai en file d’attente, une nouvelle tentative ou un backfill.

Les tâches fondées sur le temps doivent utiliser :

- `data_interval_start` : début inclusif de l’intervalle
- `data_interval_end` : fin exclusive de l’intervalle
- `run_id` : distingue les réexécutions manuelles ou les instances de backfill d’un même intervalle

Standardiser les intervalles semi-ouverts `[start, end)` réduit les événements dupliqués ou manquants aux frontières.

### Une dépendance exprime un ordre d’exécution, pas un transport de données

`extract >> transform` exprime une dépendance de contrôle : transform peut s’exécuter après la réussite d’extract. Cela ne signifie pas que de gros volumes de données circulent entre les mémoires des workers.

Plan de données recommandé :

```text
task A -> object/table/stream에 데이터 기록
       -> XCom에는 URI, partition, row count, checksum만 기록
task B -> 해당 URI와 metadata를 받아 외부 저장소에서 읽기
```

La base de métadonnées Airflow est destinée à l’état de l’orchestration. Stockez les jeux de données réels, les binaires de modèles et les dataframes dans un stockage objet, une base de données ou un moteur de calcul approprié.

## Modèle pratique : commencer par construire des tâches idempotentes fondées sur les intervalles

### Comprendre les intervalles de données et la publication atomique avec un exemple local sûr

Le DAG suivant crée un fichier par intervalle sous `/tmp` et remplace atomiquement la même cible lorsque l’intervalle est réexécuté. Il sert à l’apprentissage et aux tests locaux ; en production, adaptez-le aux écritures conditionnelles du stockage objet, aux transactions de table ou à une sémantique de renommage atomique.

```python
from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.sdk import DAG, Asset, get_current_context, task


OUTPUT_ROOT = Path("/tmp/airflow-orchestration-example")
PUBLISHED_ASSET = Asset("local-example://orchestration/partitions")


with DAG(
    dag_id="interval_aware_example",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
    },
) as dag:

    @task(outlets=[PUBLISHED_ASSET])
    def publish_partition() -> dict[str, str]:
        context = get_current_context()
        interval_start = context["data_interval_start"]
        interval_end = context["data_interval_end"]
        run_id = context["run_id"]

        partition = interval_start.format("YYYY-MM-DD")
        target = OUTPUT_ROOT / f"date={partition}" / "result.json"
        target.parent.mkdir(parents=True, exist_ok=True)

        # run_id를 그대로 파일명에 쓰지 않고 안정된 제한 길이 ID로 만든다.
        attempt_id = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:12]
        staging = target.with_name(f".{target.name}.{attempt_id}.tmp")

        payload = {
            "data_interval_start": interval_start.isoformat(),
            "data_interval_end": interval_end.isoformat(),
        }
        staging.write_text(
            json.dumps(payload, sort_keys=True),
            encoding="utf-8",
        )
        staging.replace(target)

        # XCom에는 작은 metadata만 반환한다.
        return {
            "path": str(target),
            "partition": partition,
        }

    @task
    def verify_partition(metadata: dict[str, str]) -> None:
        path = Path(metadata["path"])
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"published partition is invalid: {metadata['partition']}")

    verify_partition(publish_partition())


if __name__ == "__main__":
    dag.test()
```

La documentation officielle sur le [débogage des DAG](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/debug.html) propose `dag.test()` pour exécuter rapidement les tâches en échec dans un seul processus. Une réussite locale ne valide ni l’exécuteur, ni le réseau, ni les autorisations, ni le backend de secrets ; un environnement d’intégration distinct reste donc nécessaire.

### L’idempotence est un prérequis pour les nouvelles tentatives et les backfills

Une tâche idempotente produit le même état final après des exécutions répétées avec la même entrée logique. C’est une exigence plus forte que la simple affirmation « la deuxième exécution réussit ».

Modèles pratiques :

- dériver les clés de sortie de `data_interval_start/end`, et non de l’horloge murale
- utiliser, selon le cas, l’écrasement de partition, merge/upsert ou replace plutôt qu’append
- terminer dans une zone de staging avant la publication atomique
- envoyer des clés d’idempotence déterministes aux API externes
- combiner les effets de bord et les marqueurs d’achèvement au moyen d’une transaction ou d’un compare-and-set
- préciser le point de reprise et le responsable du nettoyage après un achèvement partiel

L’envoi d’e-mails, les paiements et la création de tickets externes peuvent produire des effets de bord dupliqués lors d’une simple nouvelle tentative. Ne vous fiez pas uniquement aux paramètres de nouvelle tentative d’Airflow ; utilisez la clé d’idempotence et l’API de consultation des résultats du système externe.

Pour la reproductibilité, journalisez les entrées suivantes en excluant les secrets.

- ID du DAG, ID de la tâche, ID de l’exécution et numéro de tentative
- début et fin de l’intervalle de données
- partition/version source et URI de sortie
- révision du code/de l’image
- nombre de lignes, somme de contrôle et résultats de qualité des données

### Ne relancer que les erreurs transitoires

Erreurs adaptées à une nouvelle tentative :

- délai d’attente réseau temporaire
- limitation de débit avec un délai explicite avant nouvelle tentative
- dépendance temporairement indisponible
- préemption d’un worker ou plantage de processus

Erreurs qu’une nouvelle tentative ne peut pas corriger :

- incompatibilité entre schéma et code
- identifiants ou autorisations invalides
- entrée invalide
- bogue déterministe
- dépassement persistant du quota de stockage

Définissez un nombre limité de tentatives, un backoff exponentiel, un délai maximal et un timeout d’exécution de la tâche. Appliquer un nombre élevé de tentatives à toutes les tâches retarde la détection des incidents et provoque des tempêtes de nouvelles tentatives sur les dépendances.

Si la bibliothèque propre à une tâche effectue des nouvelles tentatives avant Airflow, le nombre total de tentatives peut se multiplier. Déterminez quelle couche gère les nouvelles tentatives réseau rapides et laquelle gère les réexécutions au niveau du workflow.

## Séparer les rôles de XCom, Connections, Variables et Params

| Outil | Portée et objectif | Valeurs adaptées | Valeurs à éviter |
|---|---|---|---|
| XCom | communication au sein d’une instance de tâche/exécution de DAG | URI, partition, petite métadonnée JSON | dataframe, gros binaire, point de reprise |
| Connection | endpoint et authentification d’un système externe | hôte, schéma, conn ID, référence d’identifiant | résultat de tâche, paramètre métier |
| Variable | configuration d’exécution propre à l’installation ou à l’équipe | commutateur d’urgence, petit paramètre par déploiement | constante versionnée, entrée par exécution, gros JSON |
| Params | entrée validée par exécution de DAG | mode de traitement, dates/options bornées | secret durable, résultat entre tâches |

La documentation officielle sur [XCom](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/xcoms.html) indique que XCom est destiné aux petites valeurs sérialisables, pas aux gros objets tels que les dataframes. Airflow 3 exige `task_ids` pour récupérer le XCom d’une autre tâche, et les XCom peuvent être effacés avant une nouvelle tentative d’une tâche en échec ; ne les utilisez donc pas comme points de reprise durables.

Un retour TaskFlow est pratique, mais l’objet entier peut être sérialisé dans XCom. Renvoyez un manifeste comme celui-ci plutôt que le résultat réel du travail externe.

```python
{
    "uri": "object://<BUCKET>/<KEY>",
    "partition": "2026-01-01",
    "checksum": "sha256:<DIGEST>",
    "row_count": 1234,
}
```

Une Connection référence une connexion externe par un `conn_id` logique, tandis que les Hooks/providers gèrent les identifiants réels. Ne placez pas d’URI bruts ni de mots de passe dans le code source des DAG. Suivez la documentation sur les [Connections et Hooks](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/connections.html).

Une Variable est un magasin clé/valeur global d’exécution. La documentation officielle sur les [Variables](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/variables.html) recommande de placer, lorsque c’est possible, la configuration dans le code source versionné du DAG et de réserver les Variables aux valeurs réellement dépendantes de l’exécution. Des appels répétés à `Variable.get()` au niveau supérieur couplent les performances et la disponibilité du parsing aux consultations des métadonnées/du backend de secrets ; lisez-les au moment d’exécuter la tâche ou dans les templates.

## Gérer les secrets dans l’identité d’exécution et un backend de secrets, pas dans les DAG

L’emploi d’un nom d’Airflow Connection ou Variable ne sécurise pas automatiquement une valeur. Examinez les chemins d’exposition à travers la base de métadonnées, les variables d’environnement, les journaux, les DAG sérialisés et les environnements de tâche.

Principes recommandés :

- ne consigner dans les DAG que le `conn_id` et les noms logiques des secrets
- utiliser un backend de secrets externe ou une identité de workload
- séparer les portées de secrets nécessaires au scheduler, au processeur de DAG, au serveur d’API et au worker
- minimiser les rôles cloud et les autorisations de namespace pour chaque tâche de worker
- préférer les identifiants à courte durée de vie aux clés d’accès durables
- ne jamais journaliser les secrets bruts, les URI de Connection ou l’environnement complet

Airflow 3 permet de configurer un backend de secrets distinct pour les workers. Puisque l’ordre de consultation et les collisions de clés ont de l’importance, assurez-vous qu’un même nom ne figure pas dans plusieurs backends pendant une migration. Suivez la documentation officielle sur les [backends de secrets](https://airflow.apache.org/docs/apache-airflow/stable/security/secrets/secrets-backend/index.html).

Le chiffrement Fernet et le masquage dans l’interface ne protègent pas l’intégralité du cycle de vie d’un secret. Le processus worker détient le texte en clair dès que le code de la tâche lit une valeur. Il faut également isoler les workers, expurger les journaux, restreindre les sorties réseau, effectuer des rotations et mener des audits.

## Séparer l’attente des slots de worker

### Modes poke, reschedule et différable

| Mode | Slot de worker pendant l’attente | Situation adaptée | Principal compromis |
|---|---:|---|---|
| sensor `poke` | occupé en continu | attentes très courtes nécessitant des vérifications fréquentes | gaspille des workers lors des longues attentes |
| sensor `reschedule` | libéré entre les vérifications | attentes autorisant un polling toutes les quelques minutes | surcharge de replanification par le scheduler |
| opérateur différable | confié au triggerer et libéré | longues attentes d’événements externes | exploitation du triggerer et prise en charge par le provider requises |

La documentation officielle sur les [Sensors](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/sensors.html) explique la différence d’utilisation des slots entre `poke` et `reschedule`. Selon [Deferrable Operators & Triggers](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/deferring.html), pendant la mise en attente, un trigger asynchrone effectue le polling dans le triggerer tandis que la tâche libère son slot de worker.

Consultez la documentation de la version du provider pour savoir si un capteur prend en charge `deferrable=True` ; cet argument ne peut pas être ajouté arbitrairement à tous les capteurs. N’effectuez pas d’E/S bloquante ni de calcul CPU dans les triggers personnalisés. Un seul trigger qui bloque la boucle d’événements peut retarder de nombreuses tâches différées.

Chaque tâche en attente doit posséder :

- un `timeout` global
- un intervalle de polling ou une sémantique de trigger
- la décision de traiter le timeout comme un échec léger ou dur
- un critère distinguant les événements obsolètes des nouveaux
- une réussite immédiate si la condition externe est déjà satisfaite
- une surveillance de la santé du triggerer et de l’âge des tâches différées

Si le polling est inévitable, vérifiez non seulement l’existence d’un fichier, mais aussi sa partition attendue, sa somme de contrôle/son marqueur d’achèvement et l’horodatage de l’événement. Ne prenez pas un ancien fichier d’une exécution précédente pour une nouvelle réussite.

## Catchup et backfill sont deux contrôles distincts des intervalles historiques

### Catchup

Avec `catchup=True` sur une planification temporelle, le scheduler peut créer des exécutions de DAG pour les intervalles de données non créés depuis `start_date`. Le déploiement d’un nouveau DAG avec une ancienne `start_date` peut créer de nombreuses exécutions simultanément.

`catchup=False` empêche le scheduler courant de créer automatiquement les intervalles historiques manquants. Cela ne signifie ni que les tâches peuvent utiliser `now()`, ni que le retraitement historique est impossible.

### Backfill

Un backfill crée des exécutions de DAG pour une plage de dates historiques explicite. La documentation officielle d’Airflow 3 sur le [backfill](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/backfill.html) propose un comportement de retraitement, un `max_active_runs` indépendant, un ordre d’exécution et des simulations.

Commencez par examiner les intervalles qui seraient créés.

```bash
export DAG_ID='interval_aware_example'
export FROM_DATE='2026-01-01'
export TO_DATE='2026-01-07'

airflow backfill create \
  --dag-id "$DAG_ID" \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --reprocess-behavior failed \
  --max-active-runs 2 \
  --dry-run
```

Avant de les créer, vérifiez :

- La rétention de la source conserve-t-elle encore l’intervalle historique ?
- Le code actuel est-il compatible avec le schéma historique ?
- L’écrasement de la sortie peut-il entrer en conflit avec des travaux aval simultanés ?
- Les quotas d’API, la charge de la base de données et la capacité du pool sont-ils suffisants ?
- Le comportement de retraitement correspond-il à l’intention pour les exécutions déjà réussies ?
- Les dépendances permettent-elles de traiter du plus récent au plus ancien, ou inversement ?

Utilisez un pool ou un quota distinct afin que la concurrence du backfill ne rivalise pas sans limite avec le trafic de production. Évaluez la réussite à partir des nombres de partitions, des sommes de contrôle, de la qualité des données et de la fraîcheur en aval, en plus de l’état des tâches.

## Quand utiliser les actifs et la planification événementielle

Une planification temporelle exprime clairement « traiter l’intervalle de la veille après cette heure chaque jour ». Si l’achèvement en amont varie beaucoup ou qu’il faut exprimer les dépendances entre plusieurs producteurs, une planification sensible aux actifs peut être plus directe.

Un producteur déclare un actif de sortie ; après sa réussite, il peut planifier un DAG consommateur.

```python
import pendulum
from airflow.sdk import DAG, Asset, task


CURATED_ASSET = Asset("object://<BUCKET>/curated/<DATASET>")


with DAG(
    dag_id="asset_producer_example",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
):
    @task(outlets=[CURATED_ASSET])
    def publish() -> None:
        # 실제 구현은 output을 완전히 검증한 뒤 atomic publish해야 한다.
        pass

    publish()


with DAG(
    dag_id="asset_consumer_example",
    schedule=[CURATED_ASSET],
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
):
    @task
    def consume() -> None:
        pass

    consume()
```

Selon la documentation officielle sur la [planification sensible aux actifs](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/asset-scheduling.html), une mise à jour d’actif est enregistrée lorsque la tâche productrice réussit, et le DAG consommateur est planifié. Les conditions AND/OR entre actifs et les combinaisons avec des planifications temporelles sont possibles, mais pour une logique complexe, définissez d’abord l’ordre, la duplication, la fusion et la sémantique de replay des événements.

La [planification événementielle](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/event-scheduling.html) d’Airflow 3 peut relier des événements externes aux mises à jour d’actifs. Tous les `BaseTrigger` ne conviennent pas ; un trigger compatible est nécessaire. Si une file de messages garantit une livraison au moins une fois, concevez les ID d’événement et l’idempotence afin qu’une livraison en double ne duplique pas les résultats.

Les actifs ne créent pas automatiquement un catalogue de données complet. Gérez séparément le nommage des URI, le propriétaire, le schéma, la fraîcheur, la partition et les contrats de qualité. Ne placez pas d’identifiants ni de données personnelles dans les URI d’actifs ou `extra` ; la documentation officielle considère qu’ils peuvent ne pas être chiffrés et recommande des identifiants publiquement sûrs.

## Séparer le parsing des DAG de la logique métier

Le scheduler et le processeur de DAG importent régulièrement les fichiers de DAG. Les actions suivantes au niveau supérieur rendent le parsing lent et peu fiable.

- appels à des API externes et à des bases de données
- chargement de gros dataframes
- consultations répétées de Variable/Connection
- import de bibliothèques lourdes de machine learning
- modification non déterministe de la structure des tâches en fonction de l’heure actuelle

Gardez les fichiers de DAG centrés sur la déclaration du graphe et sur de minces adaptateurs. Placez la logique métier dans un package Python ordinaire et testez-la unitairement sans Airflow.

```text
repository/
├── dags/
│   └── curated_pipeline.py
├── src/
│   └── pipeline_core/
│       ├── extract.py
│       ├── transform.py
│       └── contracts.py
└── tests/
    ├── test_dag_structure.py
    └── test_transform.py
```

Si les conflits de dépendances entre providers et Airflow sont importants ou que les calculs sont lourds, faites soumettre par la tâche un conteneur ou un job distinct. Installer toutes les dépendances des workloads sur les workers Airflow grossit les images et augmente les conflits entre DAG ainsi que le risque des mises à niveau.

## Observabilité : surveiller ensemble le plan de contrôle Airflow et le produit de données

### Signaux du plan de contrôle

- heartbeats du scheduler et du processeur de DAG
- erreurs d’import de DAG et durée de parsing
- âge des tâches en file d’attente/planifiées
- slots d’exécuteur et de pool ouverts/en attente/en cours d’exécution
- nombre de tâches différées et santé du triggerer
- latence, connexions et croissance du stockage de la base de métadonnées
- échecs de livraison des journaux de tâches distants

La documentation officielle sur les [métriques Airflow](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/logging-monitoring/metrics.html) présente `scheduler_heartbeat`, `dag_processor_heartbeat`, `dag_processing.import_errors` ainsi que les métriques des pools, de l’exécuteur et des états de tâche. Vérifiez les noms et les tags pour l’exécuteur et le backend de télémétrie installés.

### Signaux du workflow

- réussite/échec et durée des exécutions de DAG
- nouvelle tentative, timeout, zombie et échec de heartbeat des tâches
- délai de planification : de la fin de l’intervalle au début de l’exécution
- délai de file d’attente : du moment où la tâche devient planifiable à son démarrage effectif
- achèvement de bout en bout : de la fin de l’intervalle à la publication de la sortie

### Signaux du produit de données

- fraîcheur et dernière partition réussie
- nombres de lignes attendus/réels et anomalies de volume
- violations de schéma/de contrat
- valeurs nulles, doublons et intégrité référentielle
- rapprochement et sommes de contrôle entre source et sortie

Un DAG peut réussir après avoir publié un fichier vide, tandis que le produit de données échoue. À l’inverse, le SLO utilisateur peut être respecté si une tâche est relancée et produit tout de même la bonne sortie à temps. Reliez les alertes d’astreinte aux effets sur la fraîcheur et la justesse des artefacts importants plutôt qu’au nombre de tâches en échec.

Structurez les journaux avec DAG/tâche/exécution/tentative/intervalle de données/révision de sortie. Ne journalisez ni secrets, ni URI de Connection, ni enregistrements source complets. Configurez une journalisation distante pour les workers jetables et surveillez les échecs du backend de journaux. Consultez la documentation officielle sur le [déploiement en production](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/production-deployment.html).

## Liste de contrôle des tests locaux et de la vérification CI

### Couches de vérification rapide

1. Tester unitairement la logique métier Python ordinaire.
2. Vérifier chaque import de DAG et chaque erreur de parsing.
3. Tester structurellement les ID de DAG, ID de tâches, dépendances, planifications et politiques de nouvelles tentatives.
4. Exécuter localement un intervalle représentatif avec `dag.test()`.
5. Tester en staging les véritables Connections, le backend de secrets, l’exécuteur et l’intégration au stockage.
6. Observer un DAG synthétique et la fraîcheur après le déploiement en production.

La section officielle [Bonnes pratiques : tester un DAG](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html#testing-a-dag) distingue les tests de chargement de DAG, les tests unitaires, les autocontrôles et la vérification en staging.

Exemple de test DagBag en CI :

```python
from airflow.dag_processing.dagbag import DagBag


def test_all_dags_import_without_errors() -> None:
    dagbag = DagBag(dag_folder="dags", include_examples=False)
    assert dagbag.import_errors == {}


def test_critical_dag_contract() -> None:
    dagbag = DagBag(dag_folder="dags", include_examples=False)
    dag = dagbag.get_dag("interval_aware_example")

    assert dag is not None
    assert dag.catchup is False
    assert set(dag.task_ids) == {"publish_partition", "verify_partition"}
    assert dag.get_task("publish_partition").downstream_task_ids == {
        "verify_partition"
    }
```

`airflow.dag_processing.dagbag` apparaît dans les exemples de tests officiels, mais il s’agit d’un chemin de package interne ; vérifiez donc les imports de tests lors des mises à niveau mineures d’Airflow. Préférez l’interface publique d’Airflow 3 dans le code des DAG de production.

Exemples de commandes CI :

```bash
python -m compileall -q dags src tests
python -m pytest -q
airflow dags list
airflow dags list-import-errors
```

Utilisez dans la CI le même verrou de dépendances du cœur Airflow, des providers et de Python qu’en production. Airflow se comporte à la fois comme une application et comme une bibliothèque ; combinez donc les contraintes officielles avec la stratégie de verrouillage de l’organisation et vérifiez en staging la compatibilité du cœur et des providers.

Revue du DAG :

- [ ] La planification, le fuseau horaire, `start_date` et la sémantique de catchup sont clairs.
- [ ] Les tâches dérivent les partitions de `data_interval_start/end`.
- [ ] Les nouvelles tentatives et les backfills ne dupliquent pas la sortie.
- [ ] Les timeouts, nouvelles tentatives, pools et limites de concurrence correspondent à la capacité des dépendances.
- [ ] XCom ne transporte que de petites métadonnées.
- [ ] Connections, Variables et Params sont séparés par rôle.
- [ ] Aucun secret brut n’apparaît dans le code source, les journaux, XCom ou les URI d’actifs.
- [ ] Les longues attentes sont retirées des workers au moyen de reschedule, de la mise en attente ou d’événements.
- [ ] Le parsing au niveau supérieur n’effectue aucun appel réseau/BD/import lourd.
- [ ] Les tâches feuilles et les règles de déclenchement ne déforment pas l’état global de l’exécution du DAG.

Revue des opérations :

- [ ] La simulation du backfill, sa concurrence et son comportement de retraitement ont été examinés.
- [ ] La rétention des sources et la compatibilité des schémas historiques ont été vérifiées.
- [ ] Le scheduler, le processeur de DAG, le triggerer, l’exécuteur et la BD de métadonnées sont observés.
- [ ] Des alertes sur la fraîcheur et la justesse des artefacts utilisateurs existent.
- [ ] Des politiques de rétention des journaux et de nettoyage de la base de métadonnées existent.
- [ ] La sauvegarde des métadonnées, la migration, la compatibilité des providers et le staging sont testés avant les mises à niveau.
- [ ] Les autorisations d’effacement/de nouvelle tentative/de backfill des tâches et les journaux d’audit sont restreints.

## Cas d’échec et limites

### Utiliser Airflow comme moteur de traitement de données

Traiter de gros dataframes dans la mémoire des workers et les faire passer par XCom compromet la scalabilité et l’isolation. Laissez Airflow orchestrer des calculs externes comme Spark, les entrepôts de données et les jobs conteneurisés tout en suivant de petites métadonnées.

### Utiliser `now()` comme clé de partition

Les nouvelles tentatives, les délais en file d’attente, les exécutions manuelles et les backfills peuvent lire ou écrire des partitions différentes. Dérivez les entrées logiques des intervalles de données et de Params explicites.

### Marquer la tâche comme réussie avant le commit de la sortie

Si une tâche soumet un job externe asynchrone et réussit avant d’avoir vérifié son achèvement, les travaux en aval lisent des données incomplètes. Utilisez un opérateur différable ou un capteur distinct pour vérifier l’état terminal et la qualité de la sortie avant de déclarer la réussite.

### Utiliser XCom comme magasin d’état durable

XCom sert à communiquer de petites valeurs entre tâches et peut être effacé lors d’une nouvelle tentative. Stockez les points de reprise durables et les grandes charges utiles avec leurs versions dans un stockage externe, en ne plaçant que leurs références dans XCom.

### Masquer l’instabilité en augmentant le nombre de nouvelles tentatives

Les nouvelles tentatives atténuent les erreurs transitoires, mais retardent la détection des échecs déterministes et augmentent la charge sur les dépendances. Définissez une taxonomie des erreurs et un budget de tentatives, puis, quand celui-ci est épuisé, échouez avec un contexte exploitable.

### Exprimer toutes les dépendances par le polling de capteurs

Cela augmente la charge des workers et du scheduler ainsi que la latence du polling. Si la source émet des événements, envisagez les planifications par actifs/événements ; si le polling est nécessaire, utilisez un capteur différable et un timeout.

### Prendre les événements d’actifs pour une livraison exactement une fois

Les réexécutions de producteurs, les événements externes dupliqués et le retraitement du consommateur après un échec sont tous possibles. Un actif exprime une dépendance, pas une transaction métier. Les sorties comme les consommateurs doivent être idempotents.

### Croire qu’Airflow remplace le streaming

Airflow convient à l’orchestration par lots. Lorsque le traitement continu d’événements à faible latence, l’état par événement et la contre-pression sont centraux, confiez le plan de données à un processeur de flux et à un système de messagerie, tandis qu’Airflow gère le rapprochement par lots et les workflows d’administration.

Le cœur de l’exploitation d’Airflow n’est pas un graphe de DAG sophistiqué. Il consiste à définir précisément les intervalles de traitement, à rendre les tâches réexécutables, à séparer les petites métadonnées d’orchestration du véritable plan de données et à concevoir dès le départ le retraitement historique et la réponse aux incidents.
