---
title: "GitHub-Actions-CI/CD entwerfen: mit Vertrauensgrenzen statt schneller Automatisierung beginnen"
date: 2026-07-21 09:20:00 +0900
categories: [Platform Engineering, CI-CD]
tags: [github-actions, ci-cd, supply-chain, automation, security]
description: GitHub-Actions-Workflows, Jobs und Runner-Vertrauensgrenzen mit Berechtigungen, Secrets, Environments, Matrizen, Caches und Parallelitätssteuerung sicher entwerfen.
lang: de-DE
translation_key: github-actions-ci-cd-design
hidden: true
---

{% include language-switcher.html %}

## Das Problem: Ein bestandener Workflow ist nicht dasselbe wie eine vertrauenswürdige Pipeline

CI/CD verringert wiederkehrende Arbeit, doch ein schlechter Entwurf verbindet die mächtigsten Repository-Berechtigungen mit externen Eingaben. Ein Workflow checkt Quellcode aus, lädt Abhängigkeiten herunter, führt Tests aus und verändert manchmal die Produktionsumgebung. Eine kleine YAML-Datei dient somit gleichzeitig als Build-System, Credential Broker und Deployment-Control-Plane.

Wer bei „Tests laufen automatisch“ stehen bleibt, behält folgende Probleme.

- Jeder Job teilt ein Standard-Token mit Schreibzugriff.
- Nicht vertrauenswürdiger Code aus einem Fork-PR kann auf Secrets zugreifen.
- Ein älteres Deployment desselben Branches überschreibt das neueste.
- Caches und Artefakte gelangen ohne Provenienzprüfung in Ausführungsstufen.
- Nur eine von vielen Matrixkombinationen führt eine sinnvolle Validierung aus.
- Build und Deployment sind gekoppelt, sodass dasselbe Artefakt nicht promoviert werden kann.

Das Ziel einer guten Pipeline ist nicht bloß ein grünes Häkchen. Es sind **ein reproduzierbares Ergebnis für dieselbe Eingabe, geringstmögliche Berechtigungen, konsistente Promotion eines validierten Artefakts und eindeutige Stopppunkte bei Fehlern**.

## Denkmodell: Ein Workflow ist ein DAG, der Berechtigungen und Daten überträgt

Die Haupteinheiten von GitHub Actions sind zu unterscheiden.

- **Event**: externe Eingabe, die einen Lauf startet, etwa `pull_request`, `push` oder `workflow_dispatch`
- **Workflow**: Datei, die Events und Jobgraph definiert
- **Job**: Sammlung von Schritten auf einem Runner; Dateisysteme werden zwischen Jobs standardmäßig nicht geteilt
- **Step**: eine Action oder ein Shell-Befehl
- **Runner**: flüchtige oder selbst gehostete Rechenumgebung, die Code ausführt
- **Artifact**: Ausgabe, die ausdrücklich zwischen Jobs und Workflows übertragen und aufbewahrt wird
- **Cache**: Optimierung zur schnellen Wiederherstellung reproduzierbarer Abhängigkeiten
- **Environment**: Kontrollgrenze, die Deployment-Ziel, Genehmigungen, Schutzregeln und umgebungsspezifische Secrets bündelt

An jeder Grenze werden vier Fragen gestellt.

1. Wer kontrolliert die Eingabe?
2. Welcher Code wird ausgeführt?
3. Welche Token und Secrets werden offengelegt?
4. Wie werden Provenienz und Integrität der Ausgaben geprüft?

### CI und CD trennen

CI validiert die Qualität eines Commits und erzeugt ein unveränderliches Artefakt. CD promoviert ein bereits validiertes Artefakt in eine bestimmte Umgebung. Wird für jede Umgebung neu gebaut, kann sich das „getestete Binary“ vom „in Produktion bereitgestellten Binary“ unterscheiden.

```text
commit -> test -> build -> scan -> signed artifact
                                      |
                                      +-> staging deploy
                                      +-> production approval -> production deploy
```

Eine Deployment-Kennung sollte ein unveränderlicher Wert wie Commit-SHA, Image-Digest oder Artefakt-Digest sein, kein Branchname.

## Praktisches Muster: PRs mit geringen Berechtigungen validieren und über eine getrennte Grenze deployen

### CI-Workflow mit geringstmöglichen Berechtigungen

Das folgende Beispiel ist ein Grundgerüst für ein Python-Projekt. Es wird an Lockdatei und Testbefehle des Repositorys angepasst.

{% raw %}
```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

# workflow 전체의 기본값은 읽기 전용이다.
permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: python-${{ matrix.python }} / ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    timeout-minutes: 20
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python: ["3.11", "3.12"]

    steps:
      - name: Check out source
        uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: pip
          cache-dependency-path: requirements.lock

      - name: Install locked dependencies
        run: python -m pip install --require-hashes -r requirements.lock

      - name: Static checks
        run: python -m ruff check .

      - name: Unit tests
        run: python -m pytest -q --maxfail=1
```
{% endraw %}

Der Lesbarkeit halber verwendet das Beispiel Major-Tags offizieller Actions. In einem Repository mit hohen Sicherheitsanforderungen wird eine Action auf einen geprüften **vollständigen Commit-SHA** fixiert und mit einem Werkzeug zur Aktualisierung von Abhängigkeiten erneuert. Quellcode, Maintainer, Release-Provenienz und angeforderte Berechtigungen einer Drittanbieter-Action sind wichtiger als ihre Marketplace-Bewertung.

Eine Matrix ist nicht allein deshalb besser, weil sie größer ist. Sie enthält nur Dimensionen, die der Supportvertrag tatsächlich garantieren muss.

- Bibliothek: Kombinationen der minimalen und neuesten unterstützten Laufzeit
- Anwendung: primäre produktionsgleiche Umgebung sowie Umgebungen mit hohem Kompatibilitätsrisiko
- GPU oder große Integration: Smoke-Tests in jedem PR von geplanten vollständigen Tests trennen

`fail-fast: false` bewahrt Kompatibilitätsinformationen der übrigen Kombinationen, wenn eine scheitert. Teure Jobs sollten dagegen gewöhnlich schnellen Lint- und Unit-Jobs folgen und mit `needs` blockiert werden.

### Cache und Artefakt unterscheiden

| Element | Cache | Artefakt |
|---|---|---|
| Zweck | reproduzierbare Eingaben beschleunigen | Build-Ausgaben und Berichte übertragen und aufbewahren |
| Bei einem Miss | Lauf sollte korrekt, nur langsamer bestehen | erforderliche nachgelagerte Stufe sollte scheitern |
| Key | Betriebssystem, Laufzeit, Lockdatei-Hash usw. | Commit-SHA, Build-ID, Digest usw. |
| Vertrauen | mögliche Kontamination annehmen und validieren | Provenienz und Digest gemeinsam verwalten |

Aus einem Cache wiederhergestellte Abhängigkeiten werden anhand von Lockdatei und Paket-Hashes validiert. Beliebige ausführbare Skripte oder langlebige Zugangsdaten gehören nicht in einen Cache. Event- und Scope-Einstellungen sind so zu prüfen, dass ein von einem PR beschreibbarer Cache nicht in einen privilegierten Job eines geschützten Branches fließt.

Ein einmal gebautes Artefakt wird über Umgebungen hinweg promoviert. Seine Aufbewahrungsdauer wird auf den geschäftlichen Bedarf begrenzt, sein Digest vor dem Deployment geprüft. Testberichte und Coverage sind Beobachtbarkeitsdaten; sie ersetzen nicht das Deployment-Binary.

### Deployment-Jobs nutzen Environments und kurzlebige Zugangsdaten

Ein Produktions-Deployment läuft statt im PR-Workflow in einem eigenen Workflow, der von einem geschützten Branch oder Tag ausgelöst wird, oder in einem streng isolierten Job. Das folgende Gerüst zeigt die Struktur. `<...>`-Werte und Action-SHAs werden durch Einstellungen der jeweiligen Cloud und des Repositorys ersetzt.

{% raw %}
```yaml
name: deploy

on:
  workflow_dispatch:
    inputs:
      artifact_digest:
        description: "검증된 artifact digest"
        required: true
        type: string

permissions:
  contents: read
  id-token: write

concurrency:
  group: production
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    environment: production

    steps:
      - uses: actions/checkout@<REVIEWED_FULL_COMMIT_SHA>
        with:
          persist-credentials: false

      - name: Exchange OIDC token for short-lived cloud credentials
        uses: <CLOUD_PROVIDER_LOGIN_ACTION>@<REVIEWED_FULL_COMMIT_SHA>
        with:
          role: <DEPLOYMENT_ROLE_IDENTIFIER>

      - name: Verify and deploy the immutable artifact
        env:
          ARTIFACT_DIGEST: ${{ inputs.artifact_digest }}
        run: ./scripts/deploy.sh --digest "$ARTIFACT_DIGEST"
```
{% endraw %}

Wesentliche Punkte:

- `id-token: write` nur dem Job gewähren, der den OIDC-Austausch benötigt.
- Cloud-Vertrauensrichtlinie nach Repository, Branch oder Tag und Environment-Claims einschränken.
- Kurzlebige Zugangsdaten ausgeben, statt langlebige Zugriffsschlüssel als Repository-Secrets zu speichern.
- Genehmiger, erlaubte Branches oder Tags und umgebungsspezifische Secrets am Environment `production` konfigurieren.
- Für Produktions-Deployments `cancel-in-progress: false` setzen und das Deployment-Werkzeug selbst bei doppelter Ausführung sicher gestalten.

OIDC ist nicht automatisch sicher. Sind die cloudseitigen Vertrauensbedingungen zu weit, kann ein Workflow auf jedem Branch die Produktionsrolle erhalten.

### Offenlegungspfade von Secrets verwalten, nicht nur ihre „Werte“

Ein Secret in der GitHub-Oberfläche zu speichern schließt die Aufgabe nicht ab.

- Ein Shell-Argument kann in einer Prozessliste oder einem Debug-Log erscheinen.
- Transformation oder Kodierung eines Secrets kann dessen Erkennung durch Maskierung verhindern.
- Fehlerobjekte, Test-Fixtures oder Artefakte können den Wert duplizieren.
- Datenträger oder Prozesse eines selbst gehosteten Runners können Spuren für den nächsten Job hinterlassen.

Es wird ausschließlich als Umgebungsvariable an den benötigten Schritt übergeben und niemals vollständig ausgegeben.

{% raw %}
```yaml
- name: Call protected service
  env:
    SERVICE_TOKEN: ${{ secrets.SERVICE_TOKEN }}
  run: python scripts/publish.py
```
{% endraw %}

Standardmäßig erhalten Fork-PRs keine geschützten Secrets. Insbesondere kann `pull_request_target` Berechtigungen im Kontext des Basisbranches erhalten und darf deshalb nicht mit einem Muster kombiniert werden, das nicht vertrauenswürdigen PR-Code auscheckt und ausführt. Metadatenverarbeitung wie Labels und Kommentare wird in getrennten Workflows von der Codeausführung separiert.

### Expression Injection von Shell-Quoting trennen

Direkte Interpolation einer Benutzereingabe wie eines PR-Titels in einen `run`-Block kann daraus Shell-Code machen. Der Wert wird durch die Umgebung übergeben und in der Shell quotiert.

Riskante Form:

{% raw %}
```yaml
- run: echo "${{ github.event.pull_request.title }}"
```
{% endraw %}

Sicherere Form:

{% raw %}
```yaml
- name: Print PR title as data
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  shell: bash
  run: printf '%s\n' "$PR_TITLE"
```
{% endraw %}

Wenn möglich, wird selbst die Ausgabe von Benutzereingaben vermieden; Formatvalidierung und Allowlist werden eingesetzt.

### Parallelitätsrichtlinien unterscheiden sich zwischen CI und CD

In der PR-CI verliert ein voriger Lauf seinen Wert, wenn ein neuer Commit eintrifft; Abbruch ist daher effizient.

{% raw %}
```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
{% endraw %}

Während eines Deployments kann der abrupte Abbruch einer laufenden Änderung die Umgebung in einem Zwischenzustand belassen. Deployments in dieselbe Umgebung werden serialisiert und standardmäßig in eine Warteschlange gestellt statt abgebrochen. Das Deployment-Werkzeug der Anwendung sollte Idempotenz, Timeouts und Rollback oder Roll-forward unterstützen.

## Prüfliste zur Validierung

Bei einem PR, der einen Workflow ändert, wird Folgendes geprüft:

- [ ] Trigger reagiert nur auf erforderliche Events und Branches.
- [ ] `permissions` auf oberster Ebene ist schreibgeschützt; Schreibzugriff besteht nur für benötigte Jobs.
- [ ] Fork-PRs und nicht vertrauenswürdiger Code können nicht auf Secrets oder Deployment-Zugangsdaten zugreifen.
- [ ] Eine Richtlinie fixiert Actions aus vertrauenswürdigen Quellen auf geprüfte SHAs.
- [ ] Abhängigkeiten werden mit Lockdatei und Hashes geprüft.
- [ ] Build besteht auch bei einem Cache-Miss korrekt.
- [ ] Artefakt ist mit Commit oder Digest verknüpft und wird nicht je Umgebung neu gebaut.
- [ ] Environment-Genehmigungen und Cloud-Vertrauensrichtlinie begrenzen Branch- und Tag-Umfang.
- [ ] CI bricht veraltete Läufe ab, während CD Änderungen derselben Umgebung serialisiert.
- [ ] Jeder Job besitzt einen angemessenen Wert für `timeout-minutes`.
- [ ] Fehlerlogs und Artefakte enthalten keine Secrets oder personenbezogenen Informationen.
- [ ] Namen erforderlicher Checks im Branchschutz bleiben nach der Workflow-Änderung gültig.

Für statische Validierung werden Workflow-Schema-Linting, Dependency Review, Secret Scanning und Action-Richtlinienprüfungen kombiniert. Bestandenes Lint beweist keinen sicheren Berechtigungsentwurf; zusätzlich wird das Bedrohungsmodell jedes Events geprüft.

## Fehlerfälle und Einschränkungen

### Probleme mit `permissions: write-all` lösen

Berechtigungsfehler verschwinden, doch der Schadensradius wächst. Die erforderliche API-Operation wird ermittelt und nur der konkrete Scope auf Jobebene ergänzt.

### Annehmen, ein Tag fixiere die Lieferkette vollständig

Ein Major- oder Versionstag kann verschoben werden. Ein vollständiger Commit-SHA ist ein stärkerer Fixpunkt, dennoch benötigen Quellcode und Release-Prozess dieses Commits Prüfung. Pinning muss mit Aktualisierungsautomatisierung und Reaktion auf Schwachstellen verbunden sein.

### Einen Cache als vertrauenswürdige Build-Ausgabe verwenden

Ein Cache ist eine Optimierung; sein Löschen darf die Korrektheit nicht beeinflussen. Deployment-Ziele werden als ausdrückliche Artefakte mit Provenienz übertragen.

### Einen selbst gehosteten Runner nur als Kostensparmaßnahme behandeln

Ein selbst gehosteter Runner kann mit Netzwerkzugriff, persistenten Datenträgern und Cloud-Metadaten eine größere Angriffsfläche besitzen. Öffentliche oder Fork-PRs dürfen nicht auf einem persistenten Runner ausgeführt werden; erforderlich sind flüchtige Isolation, Image-Resets, Egress-Beschränkungen und Patching.

### Jeden Test bei jedem PR ausführen

Wird Validierung langsam, umgehen Entwickler sie oder erzeugen große Batches. Das Testportfolio wird in schnelle Pflicht-Gates, pfadabhängige Integration, geplante vollständige Regression und Validierung nach dem Deployment geschichtet. Pfadfilter werden konservativ entworfen, damit sie keine echten Abhängigkeiten auslassen.

GitHub Actions ist kein YAML-Syntaxproblem, sondern ein Problem des Vertrauensgrenzendesigns. Die Trennung von Events, Code, Zugangsdaten, Artefakten und Umgebungen macht riskante Automatisierung wesentlich früher sichtbar.
