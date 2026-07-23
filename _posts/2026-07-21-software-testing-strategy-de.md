---
title: "Eine risikobasierte Software-Verifikationsstrategie jenseits der Testpyramide"
date: 2026-07-21 10:40:00 +0900
categories: [Software Engineering, Testing]
tags: [testing, pytest, contract-testing, property-testing, integration-testing, quality]
description: Unit-, Integrations-, Vertrags- und E2E-Tests risikogerecht kombinieren und starke Orakel sowie Invarianten entwerfen.
lang: de-DE
translation_key: software-testing-strategy
hidden: true
---

{% include language-switcher.html %}

Der Zweck von Tests besteht nicht darin, Codezeilen auszuführen, sondern **wichtige Fehler vor dem Release zu finden und nach Änderungen nachzuweisen, dass Verträge intakt bleiben**. Selbst hohe Coverage vermittelt wenig Vertrauen, wenn Assertions schwach sind oder Tests reale Risiken nicht behandeln.

## Tests rückwärts vom Risiko entwerfen

Zuerst werden Fehlermodi notiert.

| Fehlermodus | Auswirkung | Geeignete Verifikation |
|---|---|---|
| Klassifikationsfehler am Randwert | falsche Entscheidung | Unit- und Randwerttests |
| DB-Schema stimmt nicht überein | vollständiger Request-Ausfall | Integrations- und Migrationstests |
| defekter Client-/Serververtrag | Integrationsfehler nach Deployment | Vertragstests |
| Umgehung der Authentifizierung | unbefugter Zugriff | Sicherheits- und Integrationstests |
| fehlende Deployment-Konfiguration | Dienst startet nicht | Smoke-Test |
| defekter langer Benutzerablauf | Unterbrechung eines kritischen Workflows | wenige E2E-Tests |

Zuerst werden Punkte mit hoher Wahrscheinlichkeit, Auswirkung und Erkennungsschwierigkeit automatisiert. Geld, Berechtigungen, Zustandsübergänge und Datenverlustpfade haben Vorrang vor trivialen Gettern.

## Testebenen beantworten verschiedene Fragen

### Unit-Tests

Beantworten schnell: „Ist eine kleine Regel für jede wichtige Eingabe korrekt?“ I/O wird isoliert; im Mittelpunkt stehen Randwerte, Exceptions und Invarianten.

### Integrationstests

Beantworten: „Kommunizieren reale Komponenten unter demselben Vertrag?“ Durch echte Datenbank-Engine, Dateiformat, Serializer und HTTP-Adapter werden Unterschiede geprüft, die Mocks verbergen können.

### Vertragstests

Beantworten: „Sind Schema und Semantik, auf die sich Provider und Consumer geeinigt haben, weiterhin intakt?“ Feldtypen, Pflicht- und optionale Felder, Fehlercodes und Rückwärtskompatibilität werden geprüft.

### E2E-Tests

Beantworten: „Können Benutzer ihre kritischen Ziele im bereitgestellten System erreichen?“ Da diese Tests langsam und fragil sind, beginnt man mit drei bis fünf hochwertigen Pfaden statt jeden Bildschirm zu automatisieren.

### Verifikation nach dem Deployment

Die Prüfung endet nicht damit, dass ein Health-Endpoint 200 zurückgibt. Sichere synthetische Transaktionen prüfen Verbindungen zu kritischen Abhängigkeiten, minimale Lese- und Schreibvorgänge, Berechtigungen, Versionen und Status von Hintergrund-Workern.

## Gute Tests besitzen klare Arrange–Act–Assert-Phasen

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

Zu viele Aktionen in einem Test machen die Fehlerstelle unklar. Das andere Extrem, private Implementierungsmethoden festzuschreiben, lässt selbst gültiges Refactoring Tests brechen. Verifiziert werden extern beobachtbare Ergebnisse und kritische Invarianten.

## Beispiel- und eigenschaftsbasierte Tests kombinieren

Beispieltests sind leicht lesbar, decken aber nur vom Entwickler vorhergesehene Fälle ab. Eigenschaftsbasierte Tests prüfen Eigenschaften, die über einen breiten Eingaberaum stets gelten müssen.

Für eine Normalisierungsfunktion kommen etwa folgende Eigenschaften infrage.

- Ausgabe liegt im zulässigen Bereich.
- Dieselbe Eingabe zweimal zu normalisieren liefert dasselbe Ergebnis.
- Eine Umordnung der Eingabe verändert kein reihenfolgeunabhängiges Aggregat.
- Serialisierung und anschließende Deserialisierung bewahren die Bedeutung.

Numerische Berechnungen benötigen eine begründete Fehlertoleranz. Ein beliebig großes `epsilon` verbirgt Fehler, bitweise Gleichheit macht Tests dagegen plattformübergreifend instabil. Absolute und relative Fehler werden entsprechend Werteskala und Problembedingungen kombiniert.

## Test Doubles präzise wählen

- Stub: gibt einen vorgegebenen Wert zurück
- Fake: vereinfachte, aber funktionsfähige Ersatzimplementierung
- Spy: beobachtet Aufrufhistorie
- Mock: legt erwartete Interaktionen fest

Ein Netzwerk-Mock ist beim Testen von Domänenregeln nützlich. Reale Grenzen wie SQL-Dialekte, Transaktionen und Serialisierung zu mocken übersieht jedoch Integrationsfehler. „Was soll für Geschwindigkeit isoliert werden?“ wird getrennt von „Was muss mit dem echten System verifiziert werden?“ betrachtet.

## Nichtdeterminismus kontrollieren

Flaky Tests zerstören Vertrauen. Zeit, Zufall, Netzwerk, Parallelität und globaler Zustand werden zu kontrollierbaren Abhängigkeiten gemacht.

```python
from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=timezone.utc)
```

Nur einen Zufalls-Seed aufzuzeichnen garantiert keinen vollständigen Determinismus. Bibliotheksversionen, parallele Ausführung, hardwarespezifische Operationen und Eingabereihenfolge können Ergebnisse ebenfalls beeinflussen. Zuerst wird die benötigte Reproduzierbarkeitsstufe definiert.

## Wesentliches beim Datenbanktest

- Jeder Test verwendet unabhängige Daten und einen eigenen Namespace.
- Migrationen werden sowohl auf eine leere DB als auch auf eine DB der Vorversion angewandt.
- Unique-, Fremdschlüssel- und Check-Bedingungen werden darauf geprüft, Fehler tatsächlich zu verhindern.
- Nicht nur auf Transaktions-Rollback verlassen; Hintergrund-Worker und getrennte Verbindungen berücksichtigen.
- Produktionsdaten nicht in Test-Fixtures kopieren.

## Fehler untersuchbar machen

Bei einem CI-Fehler wird mindestens Folgendes bewahrt.

- Testname und Seed
- Eingabe-Fixture oder minimale reproduzierende Eingabe
- Anwendungs-/Logikversion
- Umgebung und Informationen zum Dependency Lock
- relevante Logs, Traces und Screenshots
- Unterscheidung zwischen ursprünglicher Ursache und Folgefehlern

Eine Richtlinie, Tests bedingungslos bis zum grünen Ergebnis zu wiederholen, verbirgt Flaky Tests. Sie benötigen Isolation, Ursachenklassifikation, einen Verantwortlichen und eine Korrekturfrist.

## Prüfliste zur Verifikation

- [ ] Die teuersten Fehlermodi sind den sie erkennenden Tests zugeordnet.
- [ ] Werte unmittelbar unter, an und über Grenzen werden geprüft.
- [ ] Tests prüfen neben Exceptions auch, ob Zustand nach einem Fehler erhalten bleibt.
- [ ] Integrationstests decken reale DB-, Serializer- und HTTP-Grenzen ab.
- [ ] Schemabrechende Änderungen werden in CI erkannt.
- [ ] Nur kritische Benutzerabläufe werden als stabile E2E-Tests gepflegt.
- [ ] Nichtdeterminismus von Zeit, Zufall und externen Abhängigkeiten wird kontrolliert.
- [ ] Flaky Tests werden nicht allein durch automatische Wiederholungen verborgen.
- [ ] Smoke-Tests nach dem Deployment und Rollback-Kriterien bestehen.

## Häufige Fehler

- Coverage-Zahl als Qualitätsziel behandeln.
- Denselben Happy Path wiederholen und Grenzen, Fehler sowie Parallelität übersehen.
- Selbst interne Aufrufzahlen festschreiben und dadurch Refactoring-Kosten erhöhen.
- Tests teilen Reihenfolge und globalen Zustand miteinander.
- Jede externe Grenze mocken und echte Schema- und Transaktionsfehler übersehen.
- In E2E-Tests von willkürlichen Pausen und Bildschirmkoordinaten abhängen.

Die abschließende Frage einer Teststrategie lautet nicht „Wie viele Tests haben wir geschrieben?“, sondern **„Welche Risiken haben wir kontrolliert, und mit welchen Nachweisen?“**
