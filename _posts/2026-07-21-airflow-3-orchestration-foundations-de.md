---
title: "Grundlagen der Orchestrierung mit Airflow 3: Zeit, Zustand und Wiederholbarkeit gestalten"
date: 2026-07-21 10:10:00 +0900
categories: [Data Engineering, Orchestration]
tags: [airflow, orchestration, data-pipelines, idempotency, observability]
description: XCom, Connections, Variables, Retries, Backfills, deferrable Sensors, Asset-Scheduling und Betriebsprüfungen rund um DAGs, Tasks und Datenintervalle in Airflow 3 entwerfen.
lang: de-DE
hidden: true
translation_key: airflow-3-orchestration-foundations
---

{% include language-switcher.html %}

## Das Problem: Eine Abfolge von Tasks ergibt noch keine betreibbare Pipeline

Airflow ist ein Orchestrator zum Entwickeln, Planen und Beobachten von Batch-Workflows. Es ersetzt weder die eigentliche Compute Engine noch einen Datentransport für hohe Volumina. Wird diese Grenze übersehen, entstehen folgende Probleme.

- Ausführungszeit und verarbeiteter Zeitraum werden verwechselt, sodass die falsche Partition gelesen wird.
- Bei einem Task-Retry wird erneut angehängt und Daten werden dupliziert.
- Ein über XCom übertragener Dataframe bläht die Metadatenbank auf.
- Ein Sensor belegt über lange Zeit einen Worker-Slot.
- `catchup=False` wird fälschlich als Verbot verstanden, historische Daten erneut zu verarbeiten.
- Secrets und Laufzeitkonfiguration stehen direkt im DAG-Quellcode.
- Der DAG ist erfolgreich, obwohl Aktualität oder Qualität des Artefakts fehlschlagen.

Ein betreibbarer Airflow-Workflow muss drei Fragen eindeutig beantworten.

1. **Welches Datenintervall** verarbeitet dieser DAG Run?
2. Erzeugt die erneute Ausführung desselben Tasks **denselben Endzustand**?
3. Wie prüfen wir nach einem Fehler nicht nur den Airflow-Zustand, sondern auch, **ob das für Benutzer bestimmte Artefakt intakt ist**?

Die hier beschriebenen APIs und Verhaltensweisen von Airflow 3 folgen der zum Zeitpunkt der Veröffentlichung verfügbaren [offiziellen stabilen Apache-Airflow-3.x-Dokumentation](https://airflow.apache.org/docs/apache-airflow/stable/). Öffentliche APIs und Operatorargumente können je nach Minor- und Provider-Version abweichen; fixieren Sie daher auch die Dokumentation der bereitgestellten Version.

## Denkmodell: Ein DAG Run ist eine Orchestrierungsinstanz für ein Zeitintervall oder Ereignis

### DAGs, Tasks, Task Instances und DAG Runs unterscheiden

- **DAG**: eine Workflow-Definition mit Zeitplänen, Tasks, Abhängigkeiten und Callbacks
- **Task**: eine Arbeitsvorlage, die über einen Operator, Sensor, TaskFlow-`@task` oder eine ähnliche Schnittstelle deklariert wird
- **DAG Run**: Ausführung eines DAG für ein bestimmtes logisches Intervall oder Ereignis
- **Task Instance**: konkrete Ausführung eines Tasks innerhalb eines bestimmten DAG Run

Wird dieselbe Task-Definition täglich ausgeführt, gibt es einen Task, aber in jedem täglichen DAG Run eine eigene Task Instance. Ein Retry ist ein neuer Versuch derselben Task Instance; ein Backfill erstellt neue DAG Runs für historische Intervalle.

Die öffentliche Authoring-Schnittstelle von Airflow 3 konzentriert sich auf `airflow.sdk`. DAG-Dateien sollten öffentliche APIs und Provider-Operatoren verwenden, statt interne Metadatenmodelle zu manipulieren. Grundlagen finden Sie in der offiziellen [Dokumentation zu DAGs und Tasks](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/).

### Logical Date ist nicht die tatsächliche Ausführungszeit

Ein zeitbasierter Zeitplan besitzt ein **Datenintervall**. Verarbeitet ein täglicher DAG Run `[2026-01-01 00:00, 2026-01-02 00:00)`, erstellt der Scheduler den Run gewöhnlich erst nach Ende des Intervalls. Seine Logical Date bezeichnet den Beginn des Datenintervalls, nicht die tatsächliche Startzeit nach Wanduhr.

Die offizielle [Dokumentation zu DAG Runs](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html) erläutert, dass ein geplanter Run nach Ende seines Datenintervalls erstellt wird und die Logical Date den Intervallbeginn repräsentiert. Eine mit `now()` gewählte Partition kann deshalb nach Warteschlangenverzögerungen, Retries oder Backfills andere Daten lesen.

Zeitbasierte Tasks sollten Folgendes verwenden:

- `data_interval_start`: inklusiver Intervallbeginn
- `data_interval_end`: exklusives Intervallende
- `run_id`: unterscheidet manuelle Wiederholungen oder Backfill-Instanzen desselben Intervalls

Eine Standardisierung auf halboffene Intervalle `[start, end)` reduziert doppelte und fehlende Ereignisse an Intervallgrenzen.

### Eine Abhängigkeit definiert Ausführungsreihenfolge, keinen Datentransport

`extract >> transform` drückt eine Steuerungsabhängigkeit aus: `transform` darf nach einem erfolgreichen `extract` laufen. Das bedeutet nicht, dass große Datenmengen zwischen den Arbeitsspeichern der Worker verschoben werden.

Empfohlene Datenebene:

```text
task A -> object/table/stream에 데이터 기록
       -> XCom에는 URI, partition, row count, checksum만 기록
task B -> 해당 URI와 metadata를 받아 외부 저장소에서 읽기
```

Die Airflow-Metadatenbank dient dem Orchestrierungszustand. Legen Sie tatsächliche Datensätze, Modellbinärdateien und Dataframes in geeigneten Objektspeichern, Datenbanken oder Compute Engines ab.

## Praxismuster: Zuerst intervallbasierte idempotente Tasks bauen

### Datenintervalle und atomare Veröffentlichung an einem sicheren lokalen Beispiel verstehen

Der folgende DAG erstellt unter `/tmp` je Intervall eine Datei und ersetzt bei einer erneuten Intervallausführung dasselbe Ziel atomar. Das Beispiel dient dem Lernen und lokalen Tests; in der Produktion ist es an bedingte Schreibvorgänge im Objektspeicher, Tabellentransaktionen oder atomare Rename-Semantik anzupassen.

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

Die offizielle [Dokumentation zur DAG-Diagnose](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/debug.html) stellt `dag.test()` zur schnellen, fehlerorientierten Ausführung von Tasks in einem Prozess bereit. Lokaler Erfolg validiert weder Executor, Netzwerk und Berechtigungen noch das Secret Backend; dafür ist eine eigene Integrationsumgebung erforderlich.

### Idempotenz ist Voraussetzung für Retries und Backfills

Ein idempotenter Task erzeugt bei wiederholter Ausführung mit derselben logischen Eingabe denselben Endzustand. Das ist eine stärkere Zusage als lediglich „der zweite Lauf ist erfolgreich“.

Praxismuster:

- Ausgabeschlüssel aus `data_interval_start/end` statt aus der Wanduhr ableiten
- je nach Bedarf Partition Overwrite, Merge/Upsert oder Replace statt Append verwenden
- Verarbeitung im Staging abschließen, bevor atomar veröffentlicht wird
- deterministische Idempotenzschlüssel an externe APIs senden
- Seiteneffekte und Abschlussmarkierungen über eine Transaktion oder Compare-and-Set verbinden
- nach teilweisem Abschluss Neustartposition und Zuständigkeit für die Bereinigung festlegen

E-Mail-Versand, Zahlungen und externe Ticketerstellung können bei einem einfachen Retry doppelte Seiteneffekte erzeugen. Verlassen Sie sich nicht allein auf Airflows Retry-Einstellungen, sondern nutzen Sie Idempotenzschlüssel und Ergebnisabfrage-API des externen Systems.

Protokollieren Sie für die Reproduzierbarkeit folgende Eingaben, jedoch keine Secrets.

- DAG-ID, Task-ID, Run-ID und Versuchsnummer
- Beginn und Ende des Datenintervalls
- Quellpartition/-version und Ausgabe-URI
- Code-/Image-Revision
- Zeilenanzahl, Prüfsumme und Ergebnisse der Datenqualitätsprüfung

### Nur vorübergehende Fehler erneut versuchen

Für einen Retry geeignete Fehler:

- vorübergehender Netzwerk-Timeout
- Ratenbegrenzung mit explizitem Retry-After
- zeitweilig nicht verfügbare Abhängigkeit
- Verdrängung eines Workers oder Prozessabsturz

Fehler, die ein Retry nicht beheben kann:

- Schema-/Code-Inkompatibilität
- ungültige Zugangsdaten oder Berechtigungen
- ungültige Eingabe
- deterministischer Fehler
- dauerhaft überschrittenes Speicherkontingent

Legen Sie eine begrenzte Anzahl von Versuchen, exponentielles Backoff, maximale Verzögerung und einen Task-Ausführungs-Timeout fest. Eine hohe Retry-Anzahl für jeden Task verzögert die Störungserkennung und erzeugt Retry-Stürme gegen Abhängigkeiten.

Führt die Bibliothek eines Tasks bereits eigene Retries vor Airflow aus, kann sich die Gesamtzahl der Versuche vervielfachen. Legen Sie fest, welche Ebene schnelle Netzwerk-Retries und welche Wiederholungen auf Workflow-Ebene übernimmt.

## XCom, Connections, Variables und Params nach Aufgabe trennen

| Werkzeug | Geltungsbereich und Zweck | Geeignete Werte | Zu vermeidende Werte |
|---|---|---|---|
| XCom | Kommunikation innerhalb einer Task Instance/eines DAG Run | URI, Partition, kleine JSON-Metadaten | Dataframe, große Binärdatei, Retry-Checkpoint |
| Connection | Endpunkt und Authentifizierung eines externen Systems | Host, Schema, Conn-ID, Zugangsdatenreferenz | Task-Ergebnis, Geschäftsparameter |
| Variable | installations- oder teamweite Laufzeitkonfiguration | Notfall-Laufzeitschalter, kleine Einstellung je Deployment | versionierte Konstante, Eingabe je Run, großes JSON |
| Params | validierte Eingabe je DAG Run | Verarbeitungsmodus, begrenzte Datumswerte/Optionen | langlebiges Secret, Ergebnis zwischen Tasks |

Die offizielle [XCom-Dokumentation](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/xcoms.html) stellt klar, dass XCom für kleine serialisierbare Werte und nicht für große Objekte wie Dataframes vorgesehen ist. Airflow 3 verlangt beim Abrufen des XCom eines anderen Tasks `task_ids`; außerdem können XComs vor dem Retry eines fehlgeschlagenen Tasks gelöscht werden. Verwenden Sie sie daher nicht als dauerhafte Checkpoints.

Ein TaskFlow-Rückgabewert ist praktisch, doch das gesamte Objekt kann in XCom serialisiert werden. Geben Sie statt des tatsächlichen externen Arbeitsergebnisses ein Manifest wie dieses zurück.

```python
{
    "uri": "object://<BUCKET>/<KEY>",
    "partition": "2026-01-01",
    "checksum": "sha256:<DIGEST>",
    "row_count": 1234,
}
```

Eine Connection verweist über eine logische `conn_id` auf eine externe Verbindung; Hooks beziehungsweise Provider verarbeiten die tatsächlichen Zugangsdaten. Speichern Sie weder ungeschützte URIs noch Passwörter im DAG-Quellcode. Beachten Sie die [Dokumentation zu Connections und Hooks](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/connections.html).

Eine Variable ist ein globaler Schlüssel-Wert-Speicher zur Laufzeit. Die offizielle [Variables-Dokumentation](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/variables.html) empfiehlt, Konfiguration möglichst im versionsverwalteten DAG-Quellcode abzulegen und Variables auf tatsächlich laufzeitabhängige Werte zu beschränken. Wiederholte `Variable.get()`-Aufrufe auf oberster Ebene koppeln Parsing-Leistung und Verfügbarkeit an Abfragen der Metadatenbank beziehungsweise des Secret Backends; lesen Sie diese Werte zur Task-Laufzeit oder in Templates.

## Secrets in Ausführungsidentität und Secret Backend verwalten, nicht in DAGs

Allein die Verwendung des Namens einer Airflow Connection oder Variable macht einen Wert nicht automatisch sicher. Prüfen Sie Offenlegungspfade über Metadatenbank, Umgebungsvariablen, Logs, serialisierte DAGs und Task-Umgebungen.

Empfohlene Grundsätze:

- in DAGs nur `conn_id` und logische Secret-Namen erfassen
- ein externes Secret Backend oder eine Workload Identity verwenden
- die von Scheduler, DAG Processor, API Server und Worker benötigten Secret-Geltungsbereiche trennen
- Cloud-Rollen und Namespace-Berechtigungen je Worker-Task minimieren
- kurzlebige Zugangsdaten gegenüber langlebigen Zugriffsschlüsseln bevorzugen
- niemals ungeschützte Secrets, Connection-URIs oder die vollständige Umgebung protokollieren

Airflow 3 kann ein separates Secret Backend für Worker konfigurieren. Da Abfragereihenfolge und Schlüsselkollisionen relevant sind, darf derselbe Name während einer Migration nicht in mehreren Backends vorhanden sein. Beachten Sie die offizielle [Dokumentation zu Secret Backends](https://airflow.apache.org/docs/apache-airflow/stable/security/secrets/secrets-backend/index.html).

Fernet-Verschlüsselung und Maskierung in der Oberfläche schützen nicht den gesamten Lebenszyklus eines Secrets. Sobald Task-Code einen Wert liest, liegt er im Worker-Prozess im Klartext vor. Zusätzlich sind Worker-Isolation, Log-Redaktion, Egress-Beschränkungen, Rotation und Audits erforderlich.

## Warten von Worker-Slots entkoppeln

### Poke-, Reschedule- und Deferrable-Modus

| Modus | Worker-Slot während des Wartens | Geeignete Situation | Wichtigster Nachteil |
|---|---:|---|---|
| Sensor `poke` | dauerhaft belegt | sehr kurze Wartezeiten mit häufigen Prüfungen | verschwendet Worker bei langem Warten |
| Sensor `reschedule` | zwischen Prüfungen freigegeben | Wartezeiten, bei denen Polling im Abstand einiger Minuten genügt | zusätzlicher Aufwand für erneutes Scheduling |
| Deferrable Operator | an Triggerer übergeben und freigegeben | langes Warten auf externe Ereignisse | Betrieb des Triggerers und Provider-Unterstützung erforderlich |

Die offizielle [Sensor-Dokumentation](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/sensors.html) erläutert den Unterschied der Slot-Nutzung zwischen `poke` und `reschedule`. Laut [Deferrable Operators & Triggers](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/deferring.html) übernimmt während einer Zurückstellung ein asynchroner Trigger im Triggerer das Polling, während der Task seinen Worker-Slot freigibt.

Prüfen Sie in der Dokumentation der Provider-Version, ob ein Sensor `deferrable=True` unterstützt; dieses Argument lässt sich nicht beliebig jedem Sensor hinzufügen. Benutzerdefinierte Trigger dürfen weder blockierende E/A noch CPU-Arbeit enthalten. Ein einziger Trigger, der die Event Loop blockiert, kann viele zurückgestellte Tasks verzögern.

Jeder wartende Task benötigt:

- einen Gesamt-`timeout`
- ein Polling-Intervall oder eine definierte Trigger-Semantik
- eine Festlegung, ob ein Timeout einen weichen oder harten Fehler auslöst
- ein Kriterium zur Unterscheidung veralteter und neuer Ereignisse
- sofortigen Erfolg, wenn die externe Bedingung bereits erfüllt ist
- Überwachung von Triggerer-Zustand und Alter zurückgestellter Tasks

Ist Polling unvermeidbar, prüfen Sie nicht nur die Existenz einer Datei, sondern auch erwartete Partition, Prüfsumme beziehungsweise Abschlussmarkierung und Ereigniszeitstempel. Verwechseln Sie eine alte Datei aus einem vorherigen Run nicht mit einem neuen Erfolg.

## Catchup und Backfill steuern historische Intervalle auf unterschiedliche Weise

### Catchup

Bei `catchup=True` in einem zeitbasierten Zeitplan kann der Scheduler DAG Runs für seit `start_date` noch nicht erstellte Datenintervalle anlegen. Wird ein neuer DAG mit altem `start_date` bereitgestellt, können auf einmal viele Runs entstehen.

`catchup=False` verhindert, dass der reguläre Scheduler fehlende historische Intervalle automatisch erstellt. Es bedeutet weder, dass Tasks `now()` verwenden dürfen, noch dass eine historische Neuverarbeitung unmöglich ist.

### Backfill

Ein Backfill erstellt DAG Runs für einen expliziten historischen Datumsbereich. Die offizielle [Backfill-Dokumentation](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/backfill.html) von Airflow 3 beschreibt Neuverarbeitungsverhalten, ein unabhängiges `max_active_runs`, Ausführungsreihenfolge und Probeläufe.

Prüfen Sie zuerst, welche Intervalle erstellt würden.

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

Prüfen Sie vor ihrer Erstellung:

- Bewahrt die Aufbewahrungsrichtlinie der Quelle das historische Intervall noch auf?
- Ist der aktuelle Code mit dem historischen Schema kompatibel?
- Kann das Überschreiben der Ausgabe mit parallel laufender Downstream-Arbeit kollidieren?
- Reichen API-Kontingente, Datenbankbelastbarkeit und Pool-Kapazität aus?
- Entspricht das Neuverarbeitungsverhalten der Absicht für bereits erfolgreiche Runs?
- Erlauben die Abhängigkeiten eine Verarbeitung vom neuesten oder vom ältesten Intervall aus?

Verwenden Sie einen eigenen Pool oder ein eigenes Kontingent, damit Backfill-Parallelität nicht unbegrenzt mit dem Produktionsverkehr konkurriert. Beurteilen Sie Erfolg neben dem Task-Zustand auch anhand von Partitionsanzahl, Prüfsummen, Datenqualität und Downstream-Aktualität.

## Wann Assets und ereignisgesteuertes Scheduling sinnvoll sind

Ein Zeitplan drückt klar aus: „Verarbeite jeden Tag nach diesem Zeitpunkt das Intervall des Vortags.“ Schwankt der Abschluss vorgelagerter Verarbeitung stark oder müssen Abhängigkeiten zwischen mehreren Produzenten ausgedrückt werden, kann ein Asset-bewusster Zeitplan direkter sein.

Ein Produzent deklariert ein Ausgabe-Asset; nach Erfolg kann dieses einen Consumer-DAG einplanen.

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

Laut offizieller [Dokumentation zum Asset-Aware Scheduling](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/asset-scheduling.html) wird bei erfolgreichem Produzenten-Task eine Asset-Aktualisierung erfasst und der Consumer-DAG eingeplant. UND-/ODER-Bedingungen zwischen Assets sowie Kombinationen mit Zeitplänen sind möglich; für komplexe Logik müssen jedoch zuerst Ereignisreihenfolge, Duplikate, Zusammenführung und Replay-Semantik definiert werden.

Das [ereignisgesteuerte Scheduling](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/event-scheduling.html) von Airflow 3 kann externe Ereignisse mit Asset-Aktualisierungen verbinden. Nicht jeder `BaseTrigger` ist geeignet; ein kompatibler Trigger ist erforderlich. Bietet eine Message Queue At-least-once-Zustellung, müssen Ereignis-IDs und Idempotenz so gestaltet sein, dass doppelte Zustellung keine doppelten Ergebnisse erzeugt.

Assets erzeugen nicht automatisch einen vollständigen Datenkatalog. Verwalten Sie URI-Benennung, Eigentümer, Schema, Aktualität, Partitionen und Qualitätsverträge separat. Speichern Sie weder Zugangsdaten noch personenbezogene Kennungen in Asset-URIs oder `extra`; die offizielle Dokumentation geht davon aus, dass diese unverschlüsselt sein können, und empfiehlt öffentlich unbedenkliche Kennungen.

## DAG-Parsing von Geschäftslogik trennen

Scheduler und DAG Processor importieren DAG-Dateien wiederholt. Folgende Aktionen auf oberster Ebene machen das Parsing langsam und unzuverlässig.

- externe API- und Datenbankaufrufe
- Laden großer Dataframes
- wiederholte Abfragen von Variables oder Connections
- Import umfangreicher Machine-Learning-Bibliotheken
- nichtdeterministische Änderung der Task-Struktur anhand der aktuellen Zeit

DAG-Dateien sollten sich auf Graphdeklarationen und schlanke Adapter beschränken. Legen Sie Domänenlogik in einem gewöhnlichen Python-Paket ab und testen Sie sie ohne Airflow mit Unit-Tests.

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

Sind Konflikte zwischen Provider- und Airflow-Abhängigkeiten erheblich oder ist die Berechnung aufwendig, sollte der Task einen eigenen Container oder Job starten. Jede Workload-Abhängigkeit auf Airflow-Workern zu installieren vergrößert Images und erhöht DAG-übergreifende Konflikte sowie das Upgrade-Risiko.

## Beobachtbarkeit: Airflow Control Plane und Datenprodukt gemeinsam überwachen

### Signale der Control Plane

- Heartbeats von Scheduler und DAG Processor
- DAG-Importfehler und Parsing-Dauer
- Alter wartender beziehungsweise eingeplanter Tasks
- freie, wartende und belegte Executor- und Pool-Slots
- Anzahl zurückgestellter Tasks und Zustand des Triggerers
- Latenz, Verbindungen und Speicherwachstum der Metadatenbank
- Fehler bei der Übertragung entfernter Task-Logs

Die offizielle [Airflow-Metrikdokumentation](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/logging-monitoring/metrics.html) beschreibt `scheduler_heartbeat`, `dag_processor_heartbeat`, `dag_processing.import_errors` sowie Metriken für Pools, Executor und Task-Zustände. Prüfen Sie Namen und Tags für den installierten Executor und das verwendete Telemetrie-Backend.

### Workflow-Signale

- Erfolg, Fehler und Dauer des DAG Run
- Task-Retry, Timeout, Zombie und Heartbeat-Ausfall
- Zeitplanverzögerung: vom Intervallende bis zum Run-Start
- Warteschlangenverzögerung: von der Einplanbarkeit bis zum tatsächlichen Task-Start
- End-to-End-Abschluss: vom Intervallende bis zur Veröffentlichung der Ausgabe

### Signale des Datenprodukts

- Aktualität und neueste erfolgreiche Partition
- erwartete/tatsächliche Zeilenanzahl und Volumenanomalien
- Schema-/Vertragsverletzungen
- Nullwerte, Duplikate und referenzielle Integrität
- Abgleich zwischen Quelle und Ausgabe sowie Prüfsummen

Ein DAG kann nach Veröffentlichung einer leeren Datei erfolgreich sein, obwohl das Datenprodukt fehlschlägt. Umgekehrt kann der Benutzer-SLO eingehalten werden, wenn ein Task nach einem Retry dennoch rechtzeitig eine korrekte Ausgabe erzeugt. Koppeln Sie Bereitschaftsalarme an die Auswirkungen auf Aktualität und Korrektheit wichtiger Artefakte statt an die Anzahl fehlgeschlagener Tasks.

Strukturieren Sie Logs nach DAG, Task, Run, Versuch, Datenintervall und Ausgaberevision. Protokollieren Sie weder Secrets und Connection-URIs noch vollständige Quelldatensätze. Konfigurieren Sie Remote Logging für kurzlebige Worker und überwachen Sie Fehler des Log-Backends. Siehe die offizielle [Dokumentation zu Produktionsbereitstellungen](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/production-deployment.html).

## Prüfliste für lokale Tests und CI-Verifikation

### Schnelle Verifikationsebenen

1. Gewöhnliche Python-Domänenlogik mit Unit-Tests prüfen.
2. Alle DAG-Importe und Parsing-Fehler prüfen.
3. DAG-IDs, Task-IDs, Abhängigkeiten, Zeitpläne und Retry-Richtlinien strukturell testen.
4. Ein repräsentatives Intervall lokal mit `dag.test()` ausführen.
5. Tatsächliche Connections sowie Secret-Backend-, Executor- und Storage-Integration im Staging testen.
6. Nach der Produktionsbereitstellung einen synthetischen DAG und dessen Aktualität beobachten.

Die offiziellen [Best Practices zum Testen eines DAG](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html#testing-a-dag) unterscheiden DAG-Loader-Tests, Unit-Tests, Selbstprüfungen und Staging-Verifikation.

Beispiel für einen DagBag-Test in CI:

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

`airflow.dag_processing.dagbag` erscheint in offiziellen Testbeispielen, ist jedoch ein interner Paketpfad. Prüfen Sie Testimporte daher bei Airflow-Minor-Upgrades. Im DAG-Code der Produktion ist die öffentliche Airflow-3-Schnittstelle zu bevorzugen.

Beispielbefehle für CI:

```bash
python -m compileall -q dags src tests
python -m pytest -q
airflow dags list
airflow dags list-import-errors
```

Verwenden Sie in CI denselben Lock für Airflow Core, Provider und Python-Abhängigkeiten wie in der Produktion. Airflow verhält sich zugleich als Anwendung und Bibliothek; kombinieren Sie daher offizielle Constraints mit der Locking-Strategie der Organisation und prüfen Sie die Kompatibilität von Core und Providern im Staging.

DAG-Prüfung:

- [ ] Zeitplan, Zeitzone, `start_date` und Catchup-Semantik sind eindeutig.
- [ ] Tasks leiten Partitionen aus `data_interval_start/end` ab.
- [ ] Retries und Backfills duplizieren keine Ausgabe.
- [ ] Timeouts, Retries, Pools und Parallelität entsprechen der Kapazität der Abhängigkeiten.
- [ ] XCom transportiert nur kleine Metadaten.
- [ ] Connections, Variables und Params sind nach Aufgabe getrennt.
- [ ] Weder Quellcode, Logs und XCom noch Asset-URIs enthalten ungeschützte Secrets.
- [ ] Langes Warten wird über Reschedule, Deferral oder Ereignisse von Workern verlagert.
- [ ] Beim Parsing auf oberster Ebene finden keine Netzwerk-/DB-Aufrufe oder umfangreichen Importe statt.
- [ ] Leaf Tasks und Trigger Rules stellen den Gesamtzustand des DAG Run nicht falsch dar.

Betriebsprüfung:

- [ ] Backfill-Probelauf, Parallelität und Neuverarbeitungsverhalten wurden geprüft.
- [ ] Quellenaufbewahrung und historische Schemakompatibilität wurden geprüft.
- [ ] Scheduler, DAG Processor, Triggerer, Executor und Metadatenbank werden überwacht.
- [ ] Es bestehen Warnmeldungen zur Aktualität und Korrektheit benutzerrelevanter Artefakte.
- [ ] Richtlinien zur Log-Aufbewahrung und Bereinigung der Metadatenbank bestehen.
- [ ] Metadaten-Backup, Migration, Provider-Kompatibilität und Staging werden vor Upgrades getestet.
- [ ] Berechtigungen für Task Clear, Retry und Backfill sowie Audit-Logs sind eingeschränkt.

## Fehlermuster und Grenzen

### Airflow als Datenverarbeitungs-Engine verwenden

Große Dataframes im Arbeitsspeicher eines Workers zu verarbeiten und über XCom weiterzugeben untergräbt Skalierbarkeit und Isolation. Lassen Sie Airflow externe Rechenressourcen wie Spark, Warehouses und Container-Jobs orchestrieren und dabei nur kleine Metadaten verfolgen.

### `now()` als Partitionsschlüssel verwenden

Retries, Warteschlangenverzögerungen, manuelle Runs und Backfills können unterschiedliche Partitionen lesen oder schreiben. Leiten Sie logische Eingaben aus Datenintervallen und expliziten Params ab.

### Task-Erfolg vor dem Commit der Ausgabe markieren

Startet ein Task einen asynchronen externen Job und meldet Erfolg, bevor dessen Abschluss geprüft wurde, liest die Downstream-Verarbeitung unvollständige Daten. Verwenden Sie einen Deferrable Operator oder separaten Sensor, um Endzustand und Ausgabequalität vor der Erfolgsmeldung zu prüfen.

### XCom als dauerhaften Zustandsspeicher verwenden

XCom ist für kleine Werte zur Task-Kommunikation vorgesehen und kann bei einem Retry gelöscht werden. Speichern Sie langlebige Checkpoints und große Payloads versioniert in einem externen Speicher und legen Sie nur Referenzen in XCom ab.

### Instabilität durch mehr Retries verbergen

Retries helfen bei vorübergehenden Fehlern, verzögern jedoch die Erkennung deterministischer Fehler und erhöhen die Last auf Abhängigkeiten. Definieren Sie Fehlertaxonomie und Retry-Budget und brechen Sie nach dessen Ausschöpfung mit handlungsrelevantem Kontext ab.

### Jede Abhängigkeit durch Sensor-Polling ausdrücken

Das erhöht Worker- und Scheduler-Last sowie Polling-Latenz. Sendet die Quelle Ereignisse, kommen Asset-/Ereigniszeitpläne infrage; ist Polling nötig, verwenden Sie einen Deferrable Sensor mit Timeout.

### Asset-Ereignisse mit Exactly-once-Zustellung verwechseln

Wiederholte Produzenten-Runs, doppelte externe Ereignisse und Neuverarbeitung durch Consumer nach Fehlern sind möglich. Ein Asset drückt eine Abhängigkeit aus, keine Geschäftstransaktion. Sowohl Ausgaben als auch Consumer müssen idempotent sein.

### Annehmen, Airflow ersetze Streaming

Airflow eignet sich für batchorientierte Orchestrierung. Stehen kontinuierliche Ereignisverarbeitung mit geringer Latenz, Zustand je Ereignis und Backpressure im Mittelpunkt, sollten Stream Processor und Messaging-System die Datenebene übernehmen, während Airflow Batch-Abgleiche und Verwaltungsworkflows steuert.

Der Kern des Airflow-Betriebs ist kein ausgefeilter DAG-Graph. Entscheidend sind präzise definierte Verarbeitungsintervalle, wiederholbar ausgelegte Tasks, die Trennung kleiner Orchestrierungsmetadaten von der eigentlichen Datenebene sowie von Beginn an gestaltete historische Neuverarbeitung und Störungsreaktion.
