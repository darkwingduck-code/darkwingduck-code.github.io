---
title: "Mindeststandards, um Python-Code produktionsreif zu machen"
date: 2026-07-21 10:10:00 +0900
categories: [Software Engineering, Python]
tags: [python, packaging, testing, typing, logging, reproducibility]
description: Praktische Standards, um Skripte zu reproduzierbaren, testbaren und beobachtbaren Python-Anwendungen weiterzuentwickeln.
lang: de-DE
translation_key: python-production-baseline
hidden: true
---

{% include language-switcher.html %}

Eine Python-Datei einmal zum Laufen zu bringen und daraus Software zu machen, die in anderen Umgebungen sicher und wiederholt läuft, sind völlig verschiedene Herausforderungen. Der Kern produktionsreifen Codes ist kein aufwendiges Framework, sondern die Frage, ob **Eingaben, Ausgaben, Abhängigkeiten und Fehler ausdrücklich sind**.

## 1. Zuerst Grenzen festlegen

Am schwersten wartbar ist Code, der Berechnung, Dateizugriff, Netzwerkanfragen, Lesen von Umgebungsvariablen und Logausgabe in einer einzigen Funktion mischt. Eine Aufteilung in folgende drei Schichten erleichtert Tests und Austausch.

1. **Domänenlogik**: reine Berechnung, die für dieselbe Eingabe dieselbe Ausgabe liefert
2. **Adapter**: Kommunikation mit Dateien, Datenbanken, HTTP-Diensten und Nachrichtenwarteschlangen
3. **Einstiegspunkt**: Konfiguration lesen, Objekte zusammensetzen und Exit-Codes bestimmen

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

Diese Funktion greift weder auf Dateien noch auf Uhren oder Netzwerke zu. Randwerte lassen sich daher schnell prüfen, und mögliche Fehlerursachen sind begrenzt.

## 2. Mit einer kleinen Projektstruktur beginnen, Verantwortlichkeiten aber trennen

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

Das `src`-Layout verringert die Gefahr, dass das Repository-Root unbeabsichtigt zum Importpfad wird und Packaging-Fehler verbirgt. `pyproject.toml` führt Build-System, Projektmetadaten, Laufzeitabhängigkeiten und Konfiguration der Entwicklungswerkzeuge zusammen.

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

Die Versionsbereiche sind nur Beispiele. In einem realen Projekt werden eine Richtlinie für unterstützte Python-Versionen und eine Lockdateistrategie gewählt und in CI sowie Deployment konsistent eingesetzt.

## 3. Konfiguration von Secrets trennen

Konfiguration fällt in drei Kategorien.

| Kategorie | Beispiele | Speicherort |
|---|---|---|
| Codevorgaben | Batch-Größe, Standard-Timeout | Code oder öffentliche Konfigurationsdatei |
| umgebungsspezifische Konfiguration | API-Adresse, Log-Level | Umgebungsvariablen oder Deployment-Konfiguration |
| Secrets | Token, Passwörter, private Schlüssel | Secret Manager |

Selbst ein Wert wie `DEBUG=true` ist eine Zeichenkette. Er wird beim Start einmal validiert, statt sich auf implizite Typkonvertierung zu verlassen.

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

Secret-Werte dürfen weder in Exception-Meldungen, CLI-Argumenten, Git, Test-Fixtures noch Notebook-Ausgaben zurückbleiben. Sie nur mit `***` zu maskieren genügt nicht; sicherer ist es, sie von vornherein niemals in Logfelder aufzunehmen.

## 4. Typen erklären Verträge; sie ersetzen keine Ausführung

Type Hints vermitteln rasch die Absicht von Eingaben und Ausgaben und verringern Refactoring-Fehler. Extern empfangene JSON-, CSV- und Umgebungsvariablen werden durch Type Hints allein jedoch nicht validiert. Zwei Ebenen sind nötig: **Laufzeitvalidierung an Vertrauensgrenzen** und interne Typprüfung.

- `Any` auf Bereiche einer schrittweisen Migration beschränken.
- Aussagekräftige `dataclass`-, `TypedDict`- oder Modelltypen gegenüber `dict[str, object]` bevorzugen.
- Klarstellen, ob `None` einen normalen oder einen Fehlerzustand darstellt.
- Zahlen mit verschiedenen Einheiten durch Namen oder eigene Typen unterscheiden.

## 5. Logs sind strukturierte Ereignisse, keine Sätze

Produktionslogs müssen später filter- und aggregierbar sein.

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

Minimale gemeinsame Felder sind `event`, `timestamp`, `severity`, `service`, `request_id` oder `job_id`, `duration` und `outcome`. Vollständige rohe Request-Bodies oder Authentifizierungsheader werden nicht geloggt.

## 6. Tests entlang der Risikoschichten anordnen

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

- Unit-Tests: reine Logik, Randwerte und Invarianten
- Integrationstests: Datenbank-, Datei- und HTTP-Adapter
- Vertragstests: Request-/Response-Schemata und Fehlerformate
- Smoke-Tests: ob kritische Pfade nach dem Deployment betriebsfähig bleiben

Jedes Implementierungsdetail zu mocken kann echte Integrationsfehler verbergen. Umgekehrt macht jeder Test als E2E die Suite langsam und Fehler schwer diagnostizierbar. Die Ebenen werden entsprechend Fehlerkosten und Änderungshäufigkeit geteilt.

## 7. Exits und Wiederholungen sind ebenfalls APIs

CLIs und Batch-Jobs müssen Erfolg und Fehler durch Exit-Codes unterscheiden. Netzwerkwiederholungen benötigen maximale Versuchszahl, exponentiellen Backoff, Jitter und eine Gesamtfrist. Operationen mit Nebenwirkungen dürfen nur automatisch wiederholt werden, wenn Idempotenz garantiert ist.

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

## Prüfliste vor der Produktion

- [ ] Die Anwendung lässt sich in einer neuen Umgebung allein mit den dokumentierten Befehlen installieren und ausführen.
- [ ] Python-Version und Abhängigkeiten sind deklariert, eine Locking-Strategie besteht.
- [ ] Eingabeschemata, Einheiten, Bereiche und Richtlinien für fehlende Werte werden validiert.
- [ ] In Code, Git-Historie, Logs und Testdaten erscheinen keine Secrets.
- [ ] Kern-Domänenlogik wird ohne externe I/O getestet.
- [ ] Timeouts, Wiederholungsbudget und Exit-Codes sind ausdrücklich.
- [ ] Request oder Job lässt sich durch strukturierte Logs verfolgen.
- [ ] Release-Artefakte können in einer sauberen Umgebung neu gebaut werden.

## Häufige Fehler

- Der Code läuft nur in einem Notebook, während Paketimporte und CLI defekt sind.
- Globaler Zustand und Seiteneffekte zur Importzeit machen Ergebnisse von der Testreihenfolge abhängig.
- `except Exception: pass` lässt Fehler wie Erfolg aussehen.
- Stets die neuesten Versionen zu installieren macht die Umgebung von gestern unreproduzierbar.
- Es werden viele Logs erzeugt, doch ohne Kennungen oder Ereignisnamen sind sie nicht durchsuchbar.

Produktionsreife sollte nicht nach Codezeilen beurteilt werden, sondern danach, **wie zuverlässig sich die Software neu installieren, ein Fehler reproduzieren und eine Wiederherstellung sicher durchführen lässt**.

## Referenzen

- [Python Packaging User Guide — `pyproject.toml` schreiben](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [Python Packaging User Guide — Python-Projekte paketieren](https://packaging.python.org/tutorials/packaging-projects/)
