---
title: "Sicheres Terraform-IaC-Design: Grenzen für Module, Umgebungen, State und Secrets"
date: 2026-07-21 09:30:00 +0900
categories: [Platform Engineering, Infrastructure]
tags: [terraform, infrastructure-as-code, state-management, security, devops]
description: Terraform als deklaratives Änderungssystem verstehen und Modulverträge, Umgebungstrennung, Remote State, Secret-Verwaltung sowie Verfahren zur Plan-/Apply-Verifikation entwerfen.
lang: de-DE
translation_key: terraform-iac-safe-foundations
hidden: true
---

{% include language-switcher.html %}

## Das Problem: Infrastruktur als Code ist nicht automatisch sicher

Terraform verwandelt manuelle Klicks in reproduzierbaren Code, konzentriert aber zugleich Änderungsberechtigungen für die Infrastruktur und den tatsächlichen Ressourcenzustand in einem einzigen Workflow. Beginnt man ohne Struktur, trägt am Ende ein kleines Root-Modul sämtliche Umgebungen, Berechtigungen, Secrets und Provider-Konfigurationen.

Häufige Fehler sind:

- Entwicklung und Produktion teilen State und Zugangsdaten.
- Ein Modul bietet so viele Wahlmöglichkeiten, dass es praktisch selbst zu einer Plattform wird.
- Lokaler State geht verloren oder mehrere Runner verändern ihn gleichzeitig.
- `sensitive = true` wird mit Verschlüsselung verwechselt, sodass Secrets im State verbleiben.
- Code, Provider oder State ändern sich zwischen geprüftem Plan und tatsächlichem Apply.
- `-target` und manuelle Konsolenänderungen werden zur üblichen Betriebspraxis.

Das Ziel von IaC besteht nicht darin, die Zahl der Dateien zu erhöhen. Es soll **Änderungsabsicht, tatsächlichen Zustand, Berechtigungsgrenzen und Verifikationsergebnisse zu einem einzigen auditierbaren Ablauf verbinden**.

## Denkmodell: Konfiguration, State, Provider und reale Infrastruktur abgleichen

Ein Terraform-Lauf besitzt vier Elemente.

- **Konfiguration**: HCL, das den gewünschten Zustand ausdrückt
- **State**: Zuordnungsinformationen zwischen Terraform-Adressen und IDs sowie Attributen tatsächlicher entfernter Objekte
- **Provider**: Plugin, das APIs liest und verändert
- **reale Infrastruktur**: tatsächliche Ressourcen in Cloud, SaaS-Systemen und lokalen Umgebungen

`terraform plan` ist kein einfacher Datei-Diff. Der Befehl erzeugt einen Ausführungsplan, indem er Konfiguration, vorigen State und den von Providern gelesenen tatsächlichen Zustand vergleicht. `apply` ruft APIs gemäß dem Abhängigkeitsgraphen auf und erfasst erfolgreiche Ergebnisse im State.

State ist daher kein Cache, sondern kritische Betriebsinformation mit Elementen wie:

- tatsächliche Ressourcenkennungen
- Abhängigkeiten und Attribut-Schnappschüsse
- Outputs und einige Provider-Rückgabewerte
- Eingaben und berechnete Ergebnisse, die geheim sein können

Der Verlust des States lässt die reale Infrastruktur nicht verschwinden, doch Terraform verliert seine Eigentumszuordnung. Umgekehrt kann bereits jemand mit ausschließlich der State-Datei sensible Informationen und die Infrastrukturstruktur erkennen.

### Deklarativ bedeutet nicht „ungeordnet“

Eine Ressourcenreferenz erzeugt eine Abhängigkeitskante. Terraform parallelisiert Operationen, soweit dies unter Wahrung der Graphreihenfolge möglich ist. Viele bedeutungslose `depends_on`-Deklarationen schaffen verborgene Kopplung und langsamere Pläne. Datenfluss wird durch Referenzen ausgedrückt; `depends_on` dient nur impliziten Beschränkungen einer API.

### Ein Modul ist mehr Richtlinienvertrag als Mechanismus zur Codewiederverwendung

Ein gutes Modul schränkt die von der Organisation zugelassenen Wahlmöglichkeiten ein.

- Input: Was dürfen Aufrufer entscheiden?
- Local: Welche Namen, Tags und Richtlinien standardisiert das Modul?
- Resource: Implementierungsdetails
- Output: stabile Verträge, von denen andere Komponenten abhängen dürfen

Ein „dünner Wrapper“, der jedes Provider-Argument unverändert als Variable verfügbar macht, bietet wenig Abstraktionswert. Besitzt ein einziges Modul dagegen Netzwerk, Datenbank, Anwendung und Monitoring, wächst der Schadensradius seiner Änderungen.

## Praktisches Muster: kleine Roots, stabile Module und unabhängiger State je Umgebung

### Empfohlene Ausgangsstruktur

```text
infrastructure/
├── modules/
│   └── service/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── versions.tf
└── live/
    ├── development/
    │   ├── backend.hcl
    │   ├── main.tf
    │   └── terraform.tfvars.example
    └── production/
        ├── backend.hcl
        ├── main.tf
        └── terraform.tfvars.example
```

Ein Umgebungsverzeichnis zu duplizieren ist nicht die einzige richtige Lösung. Getrennte Repositories, eine Orchestrierungsschicht oder Pipelines je Konto sind ebenfalls möglich. Entscheidend sind folgende Invarianten:

- Jede Umgebung besitzt einen unabhängigen State-Key und eigene Apply-Berechtigungen.
- Die Produktion verwendet ein eigenes Konto oder Projekt und eine unabhängige Genehmigungsgrenze.
- Version oder Commit des gemeinsamen Moduls ist ausdrücklich fixiert.
- Umgebungsunterschiede sind ausdrückliche Eingaben statt eines Waldes von Bedingungen.

Terraform-Workspaces erleichtern den Betrieb mehrerer States mit derselben Konfiguration, schaffen aber nicht automatisch starke Sicherheitstrennung oder wesentlich unterschiedliche Umgebungsstrukturen. Sind Grenzen zwischen Zugangsdaten und Konten erforderlich, werden neben Verzeichnissen und State auch Ausführungsidentitäten getrennt.

### Modulen enge, überprüfbare Verträge geben

Beispiel für `variables.tf`:

```hcl
variable "name" {
  description = "서비스를 식별하는 짧은 이름"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.name))
    error_message = "name은 소문자로 시작하고 소문자, 숫자, 하이픈만 사용해야 합니다."
  }
}

variable "environment" {
  description = "배포 환경"
  type        = string

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "허용된 environment 값을 사용해야 합니다."
  }
}

variable "labels" {
  description = "추가 공통 label"
  type        = map(string)
  default     = {}
}
```

Standardisierte Werte verbleiben in `main.tf` innerhalb des Moduls.

```hcl
locals {
  required_labels = {
    managed-by  = "terraform"
    environment = var.environment
    service     = var.name
  }

  labels = merge(var.labels, local.required_labels)
}

# provider에 독립적인 예시를 위해 실제 resource는 생략했다.
# 각 resource는 local.labels를 사용해 소유권과 환경을 표시한다.
```

Da spätere Maps in `merge` frühere überschreiben, verhindert die letzte Position der Pflicht-Labels, dass Aufrufer sie ändern. Dies ist ein kleines Beispiel dafür, wie ein Modul Richtlinien kapselt.

Über Outputs wird nur der mindestens nötige Vertrag angeboten.

```hcl
output "service_id" {
  description = "다른 module이 참조할 안정된 서비스 ID"
  value       = <RESOURCE_ADDRESS>.id
}
```

Das vollständige Ressourcenobjekt auszugeben koppelt Aufrufer an Implementierungsdetails. Zurückgegeben wird nur, was Verbraucher tatsächlich benötigen, etwa ID, Endpoint oder Rollenkennung.

### Versionsbeschränkungen und Provider-Lock gemeinsam verwalten

```hcl
terraform {
  required_version = ">= 1.8, < 2.0"

  required_providers {
    <PROVIDER_NAME> = {
      source  = "<PROVIDER_NAMESPACE>/<PROVIDER_NAME>"
      version = "~> <REVIEWED_MAJOR.MINOR>"
    }
  }
}
```

Die Platzhalter in diesem Beispiel werden durch den tatsächlichen Provider ersetzt. Versionsbeschränkungen werden im Root-Modul festgelegt, und die von `terraform init` erzeugte `.terraform.lock.hcl` wird eingecheckt. Ein Modul sollte die benötigte Mindestversion des Providers deklarieren; für endgültige Auswahl und Lock ist gewöhnlich das Root verantwortlich.

Die Lockdatei fixiert die Auswahl des Provider-Binary und dessen Prüfsummen. Erfolgt die Ausführung auf mehreren Betriebssystemen oder Architekturen, sind die von CI- und Entwicklungsumgebungen benötigten Plattformprüfsummen bewusst zu verwalten.

### Backend- und State-Zugriff vom Codezugriff trennen

Secrets werden nicht direkt in den Backend-Block geschrieben.

```hcl
terraform {
  backend "<REMOTE_BACKEND_TYPE>" {}
}
```

Nicht sensible umgebungsspezifische Einstellungen können über eine eigene Datei bereitgestellt werden.

```hcl
# live/production/backend.hcl
bucket         = "<REMOTE_STATE_BUCKET>"
key            = "<SERVICE>/production/terraform.tfstate"
region         = "<REGION>"
encrypt        = true
use_lockfile   = true
```

Diese Argumente variieren nach Backend-Typ und Terraform-Version; die offizielle Dokumentation und Fähigkeiten des tatsächlichen Backends sind zu prüfen. Kernanforderungen sind:

- Verschlüsselung während Übertragung und Speicherung
- Sperrung zur Verhinderung gleichzeitiger Applies
- Versionierung und Wiederherstellungsrichtlinie
- Identität mit geringstmöglichen Berechtigungen
- getrennte Keys und Zugriffsrichtlinien je Umgebung
- Audit-Logs und Alarme bei ungewöhnlichem Zugriff

Die Initialisierung wird ausdrücklich aus dem Umgebungsverzeichnis ausgeführt.

```bash
terraform init -backend-config=backend.hcl
terraform providers
```

Backend-Zugangsdaten gehören nicht in Dateien; kurzlebige Zugangsdaten werden über CI-OIDC oder eine Standard-Credential-Chain ausgegeben. Ein Zugriffsschlüssel in `backend.hcl` kann unter anderem in `.terraform`-Metadaten und Shell-Verlauf zurückbleiben.

### Plan und Apply zu einer prüfbaren Änderung verbinden

Der grundlegende Verifikationsablauf lautet:

```bash
terraform fmt -check -recursive
terraform init -input=false -backend=false
terraform validate
```

Ein Plan mit realem Remote State und Provider-APIs wird unter einer genehmigten Identität und Umgebung ausgeführt.

```bash
terraform init -input=false -backend-config=backend.hcl
terraform plan -input=false -out=tfplan
terraform show -no-color tfplan
```

Eine gespeicherte Plandatei ist binär und kann sensible Werte enthalten. Sie wird nicht unbegrenzt als öffentliches CI-Artefakt aufbewahrt, sondern verschlüsselt, zugriffsgeschützt und nur kurz gespeichert. Angewandt wird ausschließlich ein Plan aus demselben Commit, derselben Lockdatei und derselben State-Herkunft.

```bash
terraform apply -input=false tfplan
```

Genehmigt eine Person einen Textplan und wendet die Pipeline automatisch einen neuen Plan aus einem anderen Commit an, verliert die Genehmigung ihre Bedeutung. Die Pipeline muss den Quell-SHA an den Digest des Planartefakts binden.

### Secret-Referenzen statt Secret-Werte übergeben

Die folgende Deklaration verbirgt den Wert in der Oberfläche und einigen Ausgaben, verschlüsselt aber nicht den State.

```hcl
variable "bootstrap_secret" {
  type        = string
  sensitive   = true
  description = "초기 구성에만 필요한 비밀값"
}
```

Akzeptiert eine Provider-API den Wert als Ressourcenattribut, kann er im State gespeichert werden. Ein möglicher Entwurf ist:

1. Das Secret in einem Secret Manager mit getrenntem Lebenszyklus erstellen.
2. Terraform verbindet nur Secret-ID oder -Pfad und Leseberechtigungen.
3. Der Workload liest den Wert mit seiner Laufzeitidentität aus dem Secret Manager.
4. Klartext-Secrets nicht an Pläne, Outputs oder Logs übergeben.

Muss Terraform das Secret ebenfalls erzeugen, ist anzuerkennen, dass State zum Secret Store geworden ist; State-Zugriff, Verschlüsselung und Rotation werden auf diesem Niveau betrieben. Das Entfernen der Markierung mit `nonsensitive()` ist keine Sicherheitslösung.

### Drift-Erkennung endet nicht mit einem nächtlichen Plan

Drift durch Konsolenänderungen und externe Automatisierung wird mit regelmäßigen schreibgeschützten Plänen erkannt. Bei gefundener Drift ist ausdrücklich eine von drei Reaktionen zu wählen.

- Die reale Änderung war falsch: den ursprünglich deklarierten Zustand mit Terraform wiederherstellen.
- Die reale Änderung war legitim: in der Konfiguration abbilden und über den normalen PR-Prozess anwenden.
- Die Eigentumszuordnung war falsch: `import`, `moved` und State-Operationen prüfen, um die Verantwortungsgrenze zu korrigieren.

Beim Ändern einer Ressourcenadresse verhindert ein `moved`-Block, dass Terraform die Änderung als Löschen und Neuerstellen missversteht.

```hcl
moved {
  from = <OLD_RESOURCE_ADDRESS>
  to   = <NEW_RESOURCE_ADDRESS>
}
```

Imports und State-Befehle verändern Terraforms Verständnis der Eigentumszuordnung, selbst wenn die reale Ressource unverändert bleibt. Vor der Operation wird die State-Versionierung geprüft; danach ist stets zu bestätigen, dass der Plan erwartungsgemäß leer ist oder nur den beabsichtigten Diff enthält.

## Prüfliste zur Verifikation

Modulprüfung:

- [ ] Das Modul besitzt einen zusammengehörigen Lebenszyklus und Verantwortlichen.
- [ ] Input-Typen, Beschreibungen, Validierung und Vorgaben sind eindeutig.
- [ ] Aufrufer können vorgeschriebene Sicherheits- und Eigentums-Labels nicht umgehen.
- [ ] Outputs bilden einen stabilen minimalen Vertrag, statt die gesamte Implementierung offenzulegen.
- [ ] Provider- und Terraform-Versionsbereiche sind angegeben.
- [ ] Upgrades und Adressänderungen besitzen `moved`-Blöcke und Migrationsdokumentation.

Umgebungs- und State-Prüfung:

- [ ] State und Ausführungsidentitäten von Entwicklung, Staging und Produktion sind getrennt.
- [ ] Das Remote Backend bietet Verschlüsselung, Sperrung, Versionierung und Auditierung.
- [ ] Der Zugriff auf State- und Planartefakte ist enger als die Berechtigung zum Lesen des Codes.
- [ ] `.terraform/`, `*.tfstate*`, echte `*.tfvars` und Plandateien werden nicht eingecheckt.
- [ ] `.terraform.lock.hcl` wird nach Prüfung eingecheckt.
- [ ] Produktions-Applies laufen nur in einer geschützten Umgebung und genehmigten Pipeline.

Änderungsprüfung:

- [ ] `fmt`, `validate`, Lint- und Richtlinienprüfungen bestehen.
- [ ] Add-, Change-, Destroy- und Replace-Aktionen des Plans wurden Ressource für Ressource gelesen.
- [ ] Erzwungene Ersetzungen, Datenverlust und mögliche Netzwerkunterbrechung wurden geprüft.
- [ ] Geprüfter Plan und anzuwendender Binärplan stammen aus derselben Quelle und demselben State.
- [ ] Kritische Funktionalität und Beobachtbarkeitsmetriken lassen sich nach der Anwendung verifizieren.
- [ ] Für nicht rückrollbare Änderungen wurden Roll-forward-Verfahren und Backup-Wiederherstellung getestet.

## Fehlerfälle und Einschränkungen

### Ein enormer State

Referenzen sind bequem, doch selbst eine kleine Änderung verlangt eine Aktualisierung des gesamten Graphen und breite Berechtigungen. Ressourcen gehören in denselben State, wenn sie sich gemeinsam ändern, denselben Verantwortlichen besitzen und denselben Schadensradius haben sollen. Zu feine State-Aufteilung erhöht dagegen den Aufwand für Cross-State-Outputs, Reihenfolge und Orchestrierung.

### Sämtliche Umgebungsunterschiede in Bedingungen aufnehmen

Alle Umgebungen mit `count`, `for_each` und ternären Ausdrücken in ein Root zu legen macht Pläne schwer lesbar. Gemeinsame Richtlinien gehören in Module, umgebungsspezifische Zusammensetzung in dünne Roots.

### `-target` als alltägliches Deployment-Werkzeug verwenden

`-target` ist ein begrenztes Werkzeug für Wiederherstellung und Sonderfälle. Nur einen Graphteil anzuwenden kann die Konsistenz zwischen vollständiger Konfiguration und tatsächlichem Zustand verlieren. Nach seiner Verwendung wird stets ein vollständiger Plan ausgeführt.

### `prevent_destroy` als Backup behandeln

Ein Lifecycle-Guard verhindert einige Fehler, doch ein privilegierter Benutzer kann ihn entfernen, und Löschen außerhalb des Providers kann er nicht verhindern. Datenressourcen benötigen eigene Backups, Wiederherstellungsübungen, Aufbewahrung und Löschschutz.

### Ein erfolgreiches Apply mit einem gesunden Dienst gleichsetzen

Dass eine API eine Ressource angelegt hat, bedeutet nicht, dass die Anwendung gesund ist. Nach dem Deployment werden DNS, Berechtigungen, Konnektivität, Health und SLO-Metriken geprüft. IaC ersetzt weder betriebliche Verifikation noch Incident Response.

### Alles mit Terraform verwalten

Terraform eignet sich hervorragend für deklarative Ressourcen mit langem Lebenszyklus. Hochfrequente Anwendungs-Deployments, imperative Datenmigrationen und einmaliges Bootstrapping hineinzuzwingen, kann State und Graph destabilisieren. Für jede Änderung werden Werkzeuge gewählt, die zu Lebenszyklus und Rollback-Eigenschaften passen.

Sicheres Terraform entsteht durch den Entwurf von Grenzen, nicht durch raffiniertes HCL. Module werden als Richtliniengrenzen, State als Sicherheitswert, Pläne als Änderungsverträge und Pipeline-Identitäten als Ausführungsbefugnis behandelt.
