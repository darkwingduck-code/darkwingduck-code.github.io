---
title: "Reproduzierbare und sichere Docker-Images: Vom Build Context zur Non-Root-Ausführung"
date: 2026-07-21 09:40:00 +0900
categories: [Platform Engineering, Containers]
tags: [docker, containers, reproducibility, supply-chain, security]
description: Multi-Stage-Builds, festgeschriebene Abhängigkeiten, Health Checks, Non-Root-Ausführung und Image-Verifikation anhand von Docker-Layern und Build Contexts entwerfen.
lang: de-DE
translation_key: docker-reproducible-secure-images
hidden: true
---

{% include language-switcher.html %}

## Das Problem: „Auf meinem Rechner funktioniert es“ kann in ein Image verschoben werden

Container paketieren eine Ausführungsumgebung, garantieren aber nicht automatisch Reproduzierbarkeit oder Sicherheit. Wer ein `latest`-Basis-Image, nicht gesperrte Abhängigkeiten, einen übergroßen Build Context, den root-Benutzer oder in das Image kopierte Geheimnisse beibehält, paketiert Umgebungsunterschiede und Angriffsfläche zusammen mit der Anwendung.

Zwei Images können sich selbst dann unterscheiden, wenn sie aus demselben Dockerfile gebaut wurden.

- Zum Build-Zeitpunkt verwies das Basis-Tag auf einen anderen Digest.
- Der Paketindex wählte eine neue Abhängigkeit.
- Eine lokale temporäre Datei gelangte in den Build Context.
- Für eine andere CPU-Architektur wurde ein anderes natives Wheel heruntergeladen.
- Build-Metadaten und Zeitstempel unterschieden sich.

Unterscheiden Sie daher die Ziele.

1. **Funktionale Reproduzierbarkeit**: Dieselbe Quelle und derselbe Lock erzeugen dasselbe Verhalten.
2. **Reproduzierbarkeit der Abhängigkeiten**: Dieselben Basis- und Paketartefakte werden ausgewählt.
3. **Bitgenaue Reproduzierbarkeit**: Selbst der erzeugte Image-Digest ist identisch.

Ein typischer Dienst sollte zunächst die ersten beiden Ziele erreichen und bei strengeren Lieferkettenanforderungen auf deterministische Builds und Provenienz erweitern.

## Denkmodell: Ein Image besteht aus unveränderlichen Layern, ein Container ist Laufzeitzustand

Die Kernkomponenten eines Docker-Builds sind:

- **Build Context**: Menge der an den Builder gesendeten Dateien
- **Dockerfile-Anweisung**: Schritt, der einen Layer und Image-Metadaten erzeugt
- **Image**: Unveränderliche Menge inhaltsadressierter Layer und Konfiguration
- **Container**: Laufende Instanz, die ein Image mit beschreibbarem Layer, Prozess, Namespaces und Ressourcengrenzen verbindet
- **Registry**: Speicher, der Image-Manifeste und Blobs bewahrt und verteilt

Jeder Dockerfile-Schritt erzeugt aus vorherigem Zustand, Anweisung und verwendeten Dateien einen Cache-Key. Wenn häufig geänderter Quellcode vor der Installation von Abhängigkeiten kopiert wird, invalidiert selbst eine kleine Codeänderung den Abhängigkeitslayer.

Tags und Digests unterscheiden sich ebenfalls.

```text
registry.example.invalid/service:1.4    # 이동 가능한 이름
registry.example.invalid/service@sha256:<DIGEST>  # 불변 content 주소
```

Eine nützliche Kombination besteht darin, Releases für Menschen über Versionstags auffindbar zu machen, während Deployment-Systeme verifizierte Digests verwenden.

### Containerisolation ist eine Schicht der Sicherheitsgrenze

Container besitzen im Allgemeinen keinen eigenen Kernel wie eine VM. Verwenden Sie Rootless Runtimes, seccomp/AppArmor/SELinux, entfernte Capabilities, schreibgeschützte Dateisysteme, Netzwerkrichtlinien und Host-Patching gemeinsam. `USER` im Image auf Non-root zu setzen ist ein wichtiger Standard, aber keine vollständige Sandbox.

## Praktisches Muster: Kleiner Context, gesperrte Eingaben, mehrere Stufen und minimale Laufzeitrechte

### Zuerst den Build Context einschränken

Beispiel für `.dockerignore`:

```dockerignore
.git
.github
.env
.env.*
!.env.example
.venv
__pycache__/
*.pyc
*.log
.pytest_cache/
.mypy_cache/
tests/
docs/
dist/
build/
```

`.dockerignore` ist nicht bloß ein Werkzeug zur Verringerung der Image-Größe. Es reduziert die an den Builder gesendeten Daten und verhindert, dass Geheimnisse und unnötige Dateien durch `COPY . .` aufgenommen werden. Wenn ein Projekt Tests oder Dokumentation tatsächlich zur Laufzeit benötigt, dürfen sie nicht wahllos ausgeschlossen werden; entwerfen Sie Contexts für jeden Build-Zweck.

Auch wenn `.env` ausgeschlossen ist, kann ihr Inhalt offengelegt werden, wenn sie bereits in Git committet oder als Build-Argument übergeben wurde. Secret Scanning und Rotation von Zugangsdaten sind separat erforderlich.

### Ein Multi-Stage-Dockerfile für einen Python-Dienst

Das folgende Beispiel ist ein Dienstgerüst, das per Hash gesperrte binäre Wheels ohne Compiler verwendet.

```dockerfile
# syntax=docker/dockerfile:1.7

# 로컬에서는 tag로 실행할 수 있지만, CI에서는 검토한 digest로 덮어쓴다.
ARG PYTHON_IMAGE=python:3.12-slim

FROM ${PYTHON_IMAGE} AS dependencies

WORKDIR /build
COPY requirements.lock ./requirements.lock

RUN python -m pip download \
      --require-hashes \
      --only-binary=:all: \
      --destination /wheelhouse \
      --requirement requirements.lock

FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /nonexistent app

WORKDIR /app

COPY --from=dependencies /wheelhouse /wheelhouse
COPY requirements.lock ./requirements.lock
RUN python -m pip install \
      --no-index \
      --find-links=/wheelhouse \
      --require-hashes \
      --requirement requirements.lock \
    && rm -rf /wheelhouse requirements.lock

COPY --chown=10001:10001 app/ ./app/

USER 10001:10001
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"]

CMD ["python", "-m", "app"]
```

Dieses Muster soll:

- Den Dependency Lock vor dem Quellcode kopieren und so die Cache-Grenze stabilisieren.
- Paketartefakte, die mit `--require-hashes` nicht im Lock stehen, ablehnen.
- Downloadstufe der Build-Zeit von der Laufzeit trennen.
- Unterschiede bei der Auflösung von Laufzeitbenutzern durch numerische UID und GID verringern.
- Exec-Form von `CMD` statt Shell-Form verwenden, um Signalzustellung zu vereinfachen.
- Den Health Check eine HTTP-Antwort statt nur die Existenz des Dienstprozesses prüfen lassen.

Fixieren Sie das Basis-Image in CI per Digest.

```bash
docker build \
  --pull \
  --build-arg 'PYTHON_IMAGE=python:3.12-slim@sha256:<REVIEWED_BASE_IMAGE_DIGEST>' \
  --tag 'service:<SOURCE_REVISION>' \
  .
```

Ersetzen Sie Platzhalter der Form `<...>` durch tatsächlich geprüfte Werte. Digest-Pinning verhindert keine Updates, sondern macht Änderungen in Pull Requests sichtbar. Wenn ein Fix für eine Schwachstelle im Basis-Image erscheint, prüfen Sie einen automatisierten Pull Request zur Digest-Aktualisierung und bauen Sie neu.

Wenn native Erweiterungen aus Quellcode kompiliert werden müssen, installieren Sie Compiler und Header in einer Builder-Stufe und kopieren Sie nur die erzeugten Wheels in die Laufzeit. Auch Compiler-Toolchain und OS-Paketversionen sind Eingaben und müssen daher in den Umfang von Locking und Provenienz aufgenommen werden.

### Eine Lockdatei repräsentiert exakte Artefakte, keine Bereiche

Eine Datei, die nur Bereiche wie die folgenden enthält, kann mit der Zeit unterschiedliche Ergebnisse auswählen.

```text
framework>=1.0
client-library
```

Ein Produktions-Lock fixiert Versionen und Hashes einschließlich transitiver Abhängigkeiten; ein automatisiertes Update-Werkzeug erzeugt einen neuen Lock, der anschließend getestet wird. Nur einen Teil des Abhängigkeitsbaums manuell zu bearbeiten kann eine inkonsistente Auflösung erzeugen.

Dasselbe Prinzip gilt für OS-Pakete. `apt-get upgrade` bei jedem Build auszuführen kann aktuell sein, ist aber keine reproduzierbare Eingabe. Wählen Sie eine zu den Systemanforderungen passende Richtlinie.

- OS-Paketsatz in den Digest eines vertrauenswürdigen Basis-Images aufnehmen und Basis häufig aktualisieren.
- Paket-Snapshot-Repository und exakte Versionen verwenden.
- Gehärtete Basis-Image-Pipeline der Organisation verwenden.

Die Reaktion auf Schwachstellen ist keine Wahl zwischen „immer das Neueste“ und „für immer fixiert“. Sie ist ein **Prozess zur regelmäßigen Aktualisierung und Validierung fixierter Eingaben**.

### Build-Geheimnisse nicht in Layern und Verlauf hinterlassen

Vermeiden Sie diese Form:

```dockerfile
ARG PACKAGE_TOKEN
ENV PACKAGE_TOKEN=${PACKAGE_TOKEN}
RUN python -m pip install --index-url "https://${PACKAGE_TOKEN}@<PRIVATE_INDEX>/simple" <PACKAGE>
```

Build-Argumente und Umgebungen können in Image-Verlauf, Metadaten, Logs und Cache-Pfaden offengelegt werden. Verwenden Sie einen BuildKit Secret Mount und geben Sie den Wert innerhalb der Anweisung nicht aus.

```dockerfile
RUN --mount=type=secret,id=package_token \
    PACKAGE_TOKEN="$(cat /run/secrets/package_token)" \
    python scripts/fetch_private_dependency.py
```

```bash
docker build \
  --secret id=package_token,src='<LOCAL_SECRET_FILE>' \
  --tag 'service:<SOURCE_REVISION>' \
  .
```

Auch das Beispielskript darf das Token weder in URLs, Exceptions noch Debug-Logs hinterlassen. Verwenden Sie wenn möglich kurzlebige, vom Build-Dienst ausgegebene Zugangsdaten statt eines langlebigen Tokens.

### Mit schreibgeschütztem Dateisystem und minimalen Capabilities ausführen

Ergänzen Sie den Non-root-Standard des Images um Laufzeitrichtlinien.

```bash
docker run --rm \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop ALL \
  --security-opt no-new-privileges=true \
  --memory 512m \
  --cpus 1.0 \
  --publish 127.0.0.1:8080:8080 \
  'service:<SOURCE_REVISION>'
```

Wenn der Dienst Dateien schreiben muss, öffnen Sie nicht das gesamte Root-Dateisystem. Mounten Sie nur erforderliche Orte wie `/tmp`, Uploads und Caches explizit. `--privileged`, Mounts des Host-Sockets und Host Networking schwächen das Isolationsmodell erheblich und dürfen nicht als Komfortoptionen verwendet werden.

Backen Sie Zugangsdaten nicht in ein Image oder eine gewöhnliche Umgebungsdatei. Verwenden Sie Secret Store und Workload Identity der Deployment-Plattform und stellen Sie Geheimnisse nur dem benötigten Prozess über Speicher oder einen eingeschränkten Mount bereit.

### Liveness von Readiness in Health Checks unterscheiden

Ein Dockerfile-`HEALTHCHECK` stellt nur einen Zustand dar. Ein Orchestrator trennt im Allgemeinen:

- **Startup**: Ist die Initialisierung abgeschlossen?
- **Liveness**: Hängt der Prozess so stark, dass er neu gestartet werden muss?
- **Readiness**: Kann er jetzt neuen Traffic annehmen?

Readiness stark an jede externe Abhängigkeit zu koppeln kann bei einem vorübergehenden nachgelagerten Ausfall jedes Replikat aus dem Traffic entfernen und einen kaskadierenden Ausfall verstärken. Der Endpunkt sollte die Fähigkeit zur Verarbeitung realen Traffics abbilden; ein externer Fehler, den ein Neustart nicht beheben kann, darf jedoch kein Liveness-Fehler werden.

### Evidenz nach dem Image-Build bewahren

Die Ausgabe der Verifikationspipeline umfasst nicht nur das Image, sondern auch:

- Quellrevision und Build-Aufruf
- Digests von Basis- und End-Image
- SBOM
- Ergebnisse des Schwachstellenscans und Ablaufdaten von Ausnahmen
- Testergebnisse
- Build-Provenienz sowie Signaturen oder Attestierungen

Lösen Sie beim Deployment das Tag nicht erneut auf, sondern verwenden Sie den genehmigten Digest. Stimmen Sie die Registry-Aufbewahrungsrichtlinie so ab, dass vom Digest referenzierte Blobs nicht vor Ende des Deployment-Zeitraums gelöscht werden.

## Checkliste zur Verifikation

Vor dem Build:

- [ ] `.dockerignore` schließt Git-Daten, Geheimnisse, lokale Caches und unnötige Artefakte aus.
- [ ] Basis-Images und Sprachabhängigkeiten sind auf geprüfte Versionen beziehungsweise Digests und Hashes fixiert.
- [ ] Lock-Aktualisierungen durchlaufen automatisierte Tests und Schwachstellenprüfung.
- [ ] Build-Geheimnisse fehlen in `ARG`, `ENV`, URLs und Logs.
- [ ] Abhängigkeitsmanifeste werden vor dem Quellcode kopiert, um die Cache-Grenze festzulegen.

Image-Prüfung:

- [ ] Das Laufzeit-Image enthält weder Compiler noch Paketmanager-Cache oder Testzugangsdaten.
- [ ] `USER` ist Non-root und verwendet feste UID- und GID-Werte.
- [ ] Der Entrypoint kann Signale empfangen und geordnet herunterfahren.
- [ ] Der Health Check ist schnell, besitzt einen Timeout und hat keine Seiteneffekte.
- [ ] Es wurden Layerinhalte, SBOM und Schwachstellen statt nur der Image-Größe untersucht.
- [ ] Multi-Architektur-Images wurden auf jeder tatsächlichen Zielarchitektur getestet.

Laufzeitprüfung:

- [ ] Das Deployment verwendet einen unveränderlichen Digest.
- [ ] Das Root-Dateisystem ist schreibgeschützt und beschreibbare Mounts sind minimiert.
- [ ] Capability-Entfernung, No-new-privileges und eine seccomp-Schicht werden angewendet.
- [ ] CPU-, Speicher- und PID-Grenzen sowie eine Frist für geordnetes Herunterfahren sind definiert.
- [ ] Geheimnisse werden aus einer Laufzeitidentität oder einem Secret Store bereitgestellt.
- [ ] Die Bedeutungen von Readiness-, Liveness- und Startup-Probes sind verschieden.

## Fehlerfälle und Grenzen

### Alpine allein aufgrund der Image-Größe auswählen

Kleinere Größe bedeutet nicht immer geringeres Risiko oder schnelleren Betrieb. Vergleichen Sie libc-Unterschiede, fehlende native Wheels, DNS- und Zeitzonenverhalten sowie Schwierigkeit der Fehlersuche. Wählen Sie die kleinste Basis, deren betriebliche Kompatibilität validiert wurde.

### Annehmen, ein Multi-Stage-Build sei automatisch sicher

Das Kopieren eines gesamten Dateisystems in die Endstufe mit etwas wie `COPY --from=builder / /` bringt Build-Geheimnisse und Toolchain wieder hinein. Kopieren Sie nur die erforderlichen Artefaktpfade.

### Authentifizierung, Schreibvorgänge oder schwere Abfragen in einem Health Check ausführen

Probes laufen häufig. Eine langsame oder zustandsverändernde Probe wird selbst zur Fehlerquelle. Prüfen Sie nur wesentliche Readiness innerhalb begrenzter Zeit.

### Scannerergebnisse als absolute Urteile behandeln

Scanner hängen von Paketbeständen und Qualität der Advisories ab. Sowohl False Positives als auch unentdeckte Schwachstellen sind möglich. Prüfen Sie erreichbaren Code, Ausnutzbarkeit und kompensierende Kontrollen und weisen Sie jeder Ausnahme eine verantwortliche Person und ein Ablaufdatum zu.

### Vollständige Reproduzierbarkeit allein durch Container erreichen wollen

Externe Datenbankschemas, Feature Flags, Secret-Versionen, Hardwaretreiber, Kernel und Netzwerkabhängigkeiten bleiben außerhalb des Images. Verfolgen Sie auch Deployment-Manifeste, Migrationen, IaC, Konfigurationsversionen und Datenverträge.

Ein gutes Dockerfile ist nicht bloß eine kurze Datei. Es ist ein Build-Vertrag, der erklärt, welche Eingaben welches Ergebnis erzeugten, was zur Laufzeit unnötig ist und mit welchen Berechtigungen das Ergebnis ausgeführt wird.
