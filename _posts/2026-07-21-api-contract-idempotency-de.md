---
title: "Contract-First-API-Design: Fehler, Versionen, Idempotenz und asynchrone Jobs"
date: 2026-07-21 10:30:00 +0900
categories: [Software Engineering, API Design]
tags: [api, openapi, idempotency, schema, pagination, versioning]
description: Eine API als langlebigen, sich weiterentwickelnden Vertrag statt als Funktionssammlung behandeln und Anfragen, Antworten, Fehler, Wiederholungen sowie Versionen entsprechend entwerfen.
lang: de-DE
translation_key: api-contract-idempotency
hidden: true
---

{% include language-switcher.html %}

API-Qualität sollte nicht nach der Zahl der Endpoints beurteilt werden, sondern danach, **ob Aufrufer Erfolg, Fehler und Wiederholungen vorhersagen können**. Serverimplementierungen ändern sich, doch Verträge bleiben über mehrere Clients und Automatisierungssysteme hinweg bestehen.

## Ein Vertrag ist breiter als eine erfolgreiche Antwort

Der Vertrag einer Operation enthält mindestens Folgendes.

- Methode und Pfad
- Authentifizierungs- und Autorisierungsanforderungen
- Pfad-, Query-, Header- und Body-Schemata
- Einheiten, Zeitzonen, Bereiche und Nullable-Regeln
- Erfolgsstatuscodes und Antwortschemata
- Fehlercodes und Wiederholbarkeit
- Idempotenz- und Parallelitätsregeln
- Rate Limits und Paginierung
- Timeouts oder Verfahren asynchroner Verarbeitung

Eine maschinenlesbare Spezifikation wie OpenAPI ist nicht bloß eine Datei zur Dokumentationserzeugung. Sie ist der Referenzpunkt, der Schemavalidierung, Clientgenerierung, Vertragstests und Prüfungen auf Breaking Changes verbindet.

## Ressourcen von Jobs unterscheiden

Substantivbasierte Ressourcen stellen Zustand dar, HTTP-Methoden drücken Absicht aus.

```text
GET    /v1/jobs/{job_id}
POST   /v1/jobs
PATCH  /v1/jobs/{job_id}
DELETE /v1/jobs/{job_id}
```

Eine synchrone HTTP-Verbindung wird nicht offen gehalten, bis ein minutenlanger Job endet.

1. `POST /v1/jobs` validiert die Eingabe und registriert einen Job.
2. Der Server gibt `202 Accepted`, eine `job_id` und eine Status-URL zurück.
3. Der Client pollt den Status oder empfängt Webhook beziehungsweise Ereignis.
4. Zustände werden ausdrücklich gemacht, etwa `queued → running → succeeded | failed | cancelled`.

Zustandsübergänge sollten unidirektional sein und den Fehlergrund von der Wiederholbarkeit des Jobs unterscheiden.

## Eingaben an der Grenze streng validieren

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

Entscheidend ist die Richtlinie, nicht die YAML-Syntax.

- Entscheiden, ob unbekannte Felder abgelehnt oder ignoriert werden.
- Auslassung von einem ausdrücklichen `null` unterscheiden.
- Numerische Einheiten und erlaubte Bereiche in Namen, Beschreibungen und Validierung abbilden.
- Zeit in einem Standardformat mit Offset austauschen und interne Referenz definieren.
- Beim Hinzufügen eines Enum-Wertes berücksichtigen, wie ältere Clients reagieren.

## Auch Fehler besitzen ein stabiles Schema

Nur einen menschenlesbaren Satz zurückzugeben zwingt den Client, Text zu parsen.

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

- `code` ist eine stabile Kennung für maschinelle Verzweigung.
- `message` wird von Benutzern oder Operatoren gelesen.
- `details` strukturiert Probleme auf Feldebene.
- `request_id` verbindet Supportfälle mit Traces.
- Interne Stacktraces, SQL, Pfade oder Secrets werden nicht extern zurückgegeben.

## POST-Wiederholungen benötigen einen Idempotenzschlüssel

Bricht die Verbindung ab, nachdem ein Client eine Anfrage gesendet, aber bevor er die Antwort erhalten hat, weiß er nicht, ob der Job angelegt wurde. Den POST bedingungslos erneut zu senden kann ein Duplikat erzeugen.

```text
Idempotency-Key: client-generated-unique-key
```

Grundlegender Serverablauf:

1. Vorhandenen Datensatz anhand der Kombination aus authentifiziertem Principal und Schlüssel suchen.
2. Bei der ersten Anfrage Ergebnis zusammen mit einem normalisierten Hash des Request-Bodies speichern.
3. Bei gleichem Schlüssel und Body gespeichertes Ergebnis zurückgeben.
4. Bei gleichem Schlüssel und anderem Body Anfrage als Konflikt ablehnen.
5. Aufbewahrungsdauer und Regeln für parallele Anfragen dokumentieren.

Nur eine anwendungsseitige Vorprüfung ohne Unique-Bedingung in der Datenbank erzeugt eine Race Condition.

## Parallele Änderungen benötigen bedingte Anfragen

Lesen und ändern zwei Benutzer dieselbe Ressource, kann der spätere Schreibvorgang die frühere Änderung überschreiben. Optimistische Parallelitätskontrolle mit Versionsnummer oder `ETag` ist eine übliche Lösung.

```text
GET /v1/items/42
ETag: "version-7"

PATCH /v1/items/42
If-Match: "version-7"
```

Hat sich die Version geändert, meldet der Server einen Konflikt, damit der Client den neuesten Zustand erneut lesen kann.

## Paginierung muss Datenänderungen tolerieren

Eine große Liste wird nicht auf einmal zurückgegeben. Offset-Paginierung ist einfach, doch Einfügungen oder Löschungen nahe dem Anfang können Duplikate oder Auslassungen verursachen. Für große, häufig veränderte Listen eignet sich Cursor-Paginierung auf Basis eines stabilen Sortierschlüssels besser.

```json
{
  "items": [],
  "next_cursor": "opaque-cursor",
  "has_more": false
}
```

Der Cursor wird als undurchsichtig behandelt; Sortierreihenfolge, maximale Seitengröße und Regeln zur Kombination von Filtern und Cursor gehören in den Vertrag.

## Versionierung ist eine Änderungsrichtlinie, kein letzter Ausweg

Änderungen fallen in drei Typen.

- kompatibel: optionales Feld oder neuen Endpoint hinzufügen
- bedingt kompatibel: Enum-Wert hinzufügen oder Beschränkung lockern
- inkompatibel: Feld entfernen oder Typ beziehungsweise Bedeutung ändern

Inkompatible Änderungen werden in eine ausdrückliche neue Version oder parallele Operation verschoben. Deprecation-Hinweise, Beobachtungszeiträume, Clientnutzung und Stilllegungspläne werden gemeinsam verwaltet. Eine Versionsnummer in der URL schließt das Änderungsmanagement nicht ab.

## Vertragstests und Deployment-Gates

- Spezifikation validieren.
- Prüfen, dass Serverantworten der Spezifikation entsprechen.
- Bestätigen, dass repräsentative Clients aus der neuen Spezifikation erzeugt und kompiliert werden können.
- Gegenüber der Vorversion auf Breaking Changes prüfen.
- Fehlende Authentifizierung, unzureichende Autorisierung, Rate Limits und Validierungsfehler testen.
- Parallele Anfragen mit demselben Idempotenzschlüssel testen.
- Kritische Endpoints nach dem Deployment per Smoke-Test prüfen.

## Prüfliste zur Verifikation

- [ ] Neben Request- und Response-Schemata sind Fehlerschemata angegeben.
- [ ] Richtlinien für Einheiten, Zeitzonen, Nullable-Werte und Enum-Erweiterung sind eindeutig.
- [ ] Für POST-Anfragen mit Nebenwirkungen besteht eine Strategie zur Duplikatvermeidung.
- [ ] Lang laufende Arbeit ist in eine Statusressource ausgelagert.
- [ ] Lost Updates aus parallelen Änderungen werden verhindert.
- [ ] Paginierungsreihenfolge ist deterministisch und Cursor sind undurchsichtig.
- [ ] CI enthält eine Erkennung inkompatibler Änderungen.
- [ ] Stacktraces und interne Implementierungsdetails erscheinen nicht in externen Fehlern.

## Häufige Fehler

- Jedes Ergebnis als `200 OK` mit frei geformtem JSON zurückgeben
- Wiederholbare Fehler nicht von permanenten Fehlern unterscheiden
- Jobs nach einem Client-Timeout ohne Duplikatschutz anlegen
- Für dasselbe Feld verschiedene Einheiten oder Zeitzonen zwischen Endpoints verwenden
- Ein Response-Feld entfernen und „nur die Dokumentation aktualisieren“
- Daten auslassen, wenn sie sich während der Offset-Paginierung ändern

Eine gute API verbirgt Implementierungsdetails und **spezifiziert zugleich genug Verhalten, damit Aufrufer sicher scheitern und wiederholen können**.

## Referenzen

- [OpenAPI-Spezifikation](https://spec.openapis.org/oas/latest.html)
- [RFC 9110 — HTTP-Semantik](https://www.rfc-editor.org/rfc/rfc9110.html)
