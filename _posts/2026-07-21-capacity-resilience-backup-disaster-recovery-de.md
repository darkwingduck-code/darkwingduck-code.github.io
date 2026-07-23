---
title: "Kapazität, Resilienz und Disaster Recovery: Vom Lasttest zur Backup-Wiederherstellung"
date: 2026-07-21 12:09:00 +0900
categories: [Reliability, Operations]
tags: [capacity-planning, resilience, backup, disaster-recovery, load-testing]
description: Ein einheitlicher Verifikationsrahmen, der Kapazitätsplanung, Überlastschutz, Resilienztests, Backup-Wiederherstellung, RTO/RPO und Disaster Recovery miteinander verbindet.
lang: de-DE
translation_key: capacity-resilience-backup-disaster-recovery
mermaid: true
math: true
hidden: true
---
{% include language-switcher.html %}

## Das Problem: Ein erfolgreiches Backup und Wiederherstellbarkeit sind verschiedene Behauptungen

Wer Performance nur bei einem gesunden Dienst misst, erfährt nichts über sein Verhalten während eines Ausfalls.

Ein grüner Status des Backup-Jobs sagt nichts darüber aus, ob sich das Backup tatsächlich wiederherstellen lässt.

Folgende Risiken bleiben oft verborgen.

- Die durchschnittliche Last ist niedrig, aber ein kurzer Peak überlastet die Queue.
- Das Latenz-SLO wird verletzt, bevor die automatische Skalierung beginnt.
- Wiederholungsversuche erzeugen mehr Last als der ursprüngliche Traffic.
- Nach dem Failover besitzen die verbleibenden Zonen nicht genügend Kapazität.
- Ein Backup existiert, aber sein Verschlüsselungsschlüssel und die IAM-Konfiguration lassen sich nicht wiederherstellen.
- Die Datenbank wurde wiederhergestellt, doch das Anwendungsschema stimmt nicht überein.
- Das DR-Runbook existiert nur im Gedächtnis einer Person.

Resilienz ist nicht die Anzahl der Replikate. Sie ist der Nachweis, dass Funktionalität und Daten nach einem Ausfall innerhalb der zulässigen Zeit wiederhergestellt wurden.

## Denkmodell: Normale Last, Überlast, Ausfall und Katastrophe bilden ein Kontinuum

```mermaid
flowchart LR
    N[Normalbetrieb] --> P[Spitzenlast]
    P --> O[Überlast]
    O --> F[Komponentenausfall]
    F --> D[Standort- oder Regionskatastrophe]
    D --> R[Wiederherstellung]
    R --> N
```

### Kapazität ist keine einzelne Zahl für eine einzelne Ressource

Der End-to-End-Durchsatz wird von der ersten sättigenden Einschränkung begrenzt.

- CPU
- Arbeitsspeicher
- Verbindungspool
- Thread oder Worker
- Netzwerkbandbreite
- Speicher-IOPS und -Durchsatz
- Queue-Partition
- Datenbanksperre
- Quote einer externen API

### Mit Little's Law ein Verständnis für Queues aufbauen

In einem stabilen Zustand gilt für die durchschnittliche Zahl gleichzeitiger Jobs $L$, die Ankunftsrate $\lambda$ und die mittlere Systemverweildauer $W$:

$$
L = \lambda W
$$

Bleibt die Ankunftsrate über der Verarbeitungsrate, wächst der Rückstau kontinuierlich.

Auch mit Autoscaling muss berechnet werden, wie viel sich während der Scale-out-Verzögerung ansammelt.

### RTO von RPO unterscheiden

- **RTO**: Maximal zulässige Zeit zur Wiederherstellung des Dienstes nach einem Ausfall
- **RPO**: Akzeptabler zeitlicher Umfang des Datenverlusts bei der Wiederherstellung

Sie können sich je Dataset und Funktion unterscheiden.

Wer für jedes System RPO 0 und eine sofortige RTO verlangt, lässt Kosten und Komplexität sprunghaft steigen.

## Workflow: Eine Kapazitäts-Baseline erstellen

### Schritt 1. Das Workload-Modell erfassen

- Anteil jedes Anfragetyps
- Verteilung der Payload-Größen
- Lese-/Schreibverhältnis
- Cache-Hit-Rate
- Denkzeit der Benutzer
- Überlappung von Batch- und interaktivem Traffic
- Latenz externer Abhängigkeiten
- Wachstum und Saisonalität

Ein Test, der einen durchschnittlichen Benutzer wiederholt, reproduziert keine reale Schiefe.

### Schritt 2. Repräsentative SLIs auswählen

- Durchsatz
- Latenzperzentile
- Fehlerrate
- Alter der Queue-Einträge
- Sättigung
- Anzahl erfolgreicher Geschäftstransaktionen
- Datenkorrektheit

Durchschnittslatenz verbirgt Probleme am Verteilungsende; untersuchen Sie daher Perzentile.

Um Coordinated Omission zu vermeiden, prüfen Sie außerdem, dass der Lastgenerator wegen langsamer Antworten nicht aufhört, neue Anfragen zu erzeugen.

### Schritt 3. Baseline- und Grenztests trennen

Ein Baseline-Test untersucht die Stabilität unter normaler Ziellast.

Ein Stresstest identifiziert den Knickpunkt und Fehlermodi.

Ein Spike-Test untersucht plötzliche Lastspitzen.

Ein Soak-Test untersucht Lecks und kumulative Probleme.

Ein Breakpoint-Test findet Grenzen in einer sicher isolierten Umgebung.

### Schritt 4. Die Autoscaling-Schleife verifizieren

Addieren Sie Verzögerung der Metrikerfassung, Evaluationsfenster, Bereitstellungszeit und Aufwärmzeit.

Prüfen Sie, ob der Scale-out-Auslöser relativ zum Benutzer-SLO nicht zu spät greift.

Untersuchen Sie Connection Draining und Cacheverlust beim Scale-in.

Stimmen Sie die maximale Instanzzahl mit der nachgelagerten Kapazität ab.

### Schritt 5. Admission Control hinzufügen

Anfragen, die ein System nicht bewältigen kann, explizit abzulehnen kann die Wiederherstellung besser unterstützen, als sie in eine unbegrenzte Queue zu stellen.

Verwenden Sie Quoten pro Mandant, Nebenläufigkeitsgrenzen, begrenzte Queues, Fristen und Prioritäten.

Schützen Sie kritischen Traffic.

Geben Sie Wiederholungsversuchen ein separates Budget.

## Workflow: Resilienz und DR entwerfen

### Schritt 6. Fehlermodi inventarisieren

- Prozessabsturz
- Verlust eines Knotens
- Verlust einer Zone
- Timeout einer Abhängigkeit
- DNS- oder Identitätsfehler
- Datenkorruption
- Versehentliches Löschen
- Kompromittierung von Zugangsdaten
- Verlust einer Region oder eines Standorts
- Bedienfehler

Weisen Sie für jeden Modus Verantwortliche für Erkennung, Eindämmung, Wiederherstellung und Verifikation zu.

### Schritt 7. Unabhängigkeit der Redundanz verifizieren

Mehrere Replikate können dieselbe Zone, dasselbe Konto, dieselben Zugangsdaten, dasselbe Deployment oder dieselbe Konfiguration teilen.

Kennzeichnen Sie gemeinsame Ursachen auf der Architekturkarte.

Prüfen Sie regelmäßig, ob echter Traffic an das Failover-Ziel gesendet werden kann.

Ein ungenutzter Standby ist anfällig für Patch- und Konfigurationsdrift.

### Schritt 8. Backuptypen und Aufbewahrung auswählen

- Vollständig, inkrementell und differenziell
- Snapshot und logischer Dump
- Transaktionslog oder Point-in-time Recovery
- Anwendungskonsistentes Backup
- Unveränderliche oder schreibgeschützte Kopie
- Kontoübergreifende oder externe Kopie

Die 3-2-1-Regel ist ein nützlicher Ausgangspunkt, muss aber an Bedrohungsmodell und regulatorische Anforderungen angepasst werden.

Das Backup selbst muss vor Ransomware und kompromittierten Zugangsdaten isoliert sein.

### Schritt 9. Wiederherstellungsabhängigkeiten gemeinsam bewahren

Daten allein stellen keine Anwendung wieder her.

- IaC und Images
- Schemamigrationen
- Konfiguration
- Verschlüsselungsschlüssel und Zertifikate
- IAM-Bootstrap
- DNS und Domainkontrolle
- Observability
- Runbooks und Kontakte
- Lizenz- oder externe Integrationsinformationen

Entwerfen Sie ein wiederherstellbares Verwaltungssystem, ohne geheime Bytes direkt in Dokumenten abzulegen.

### Schritt 10. Die Wiederherstellung in einer isolierten Umgebung testen

1. Einen bestimmten Wiederherstellungspunkt auswählen.
2. Infrastruktur in einem sauberen Konto oder Namespace erstellen.
3. Schlüssel und Berechtigungen bootstrappen.
4. Backup wiederherstellen.
5. Schema- und Anwendungsversionen angleichen.
6. Integrität und Geschäftsinvarianten verifizieren.
7. Eine synthetische Transaktion ausführen.
8. Tatsächliche RTO und RPO erfassen.
9. Temporäre Umgebung und sensible Kopien sicher bereinigen.

### Schritt 11. Failover von Failback unterscheiden

Das Failback zum ursprünglichen Standort nach einem erfolgreichen Failover besitzt eigene Risiken.

Entscheiden Sie, wie auf beiden Seiten entstandene Schreibvorgänge zusammengeführt werden.

Fencing und Autoritätsübertragung sind nötig, um Split Brain zu verhindern.

DNS-TTL, Client-Caches und wiederverwendete Verbindungen können verhindern, dass die Traffic-Umschaltung sofort abgeschlossen ist.

### Schritt 12. Wiederherstellungsprioritäten nach Service Tier setzen

Versuchen Sie nicht, jede Funktion gleichzeitig wiederherzustellen.

- Identität und Control Plane
- Zentraler Lesepfad
- Zentraler Schreibpfad
- Asynchrone Verarbeitung
- Reporting und Batch
- Unkritische Funktionen

Legen Sie die Reihenfolge anhand von Abhängigkeitsgraph und Geschäftsauswirkung fest.

## Praxisbeispiel: Den Verlust einer Zone testen

### Hypothese

Selbst wenn eine Zone ausfällt, bleibt das SLO der Kern-API innerhalb einer begrenzten Verschlechterung.

### Vorbedingungen

- Reservierungen und Quoten in den verbleibenden Zonen prüfen
- Failover-Verhalten der Datenbank verifizieren
- PDB und Platzierung prüfen
- Abbruchschwelle für Kundenauswirkungen definieren
- Rollback-Verantwortliche und Beobachter benennen

### Ausführung

1. Baseline mit Canary-Traffic erfassen.
2. Ausgewählten Fehler in kleinem Umfang injizieren.
3. Routing von Anfragen und Verschiebung der Replikate beobachten.
4. Wiederholungsversuche und Queue-Alter beobachten.
5. Wiederaufbau der Datenbankverbindungen beobachten.
6. SLO mit der Abbruchschwelle vergleichen.
7. Gesunden Zustand wiederherstellen.
8. Dateninvarianten und Abbau des Rückstaus prüfen.

### Ergebnisse

Erfassen Sie statt eines einfachen Bestanden/Nicht bestanden die tatsächliche Erkennungszeit, Failover-Zeit, maximale Fehlerrate, Wiederherstellungszeit und manuelle Aktionen.

## Praxisbeispiel: Point-in-time Restore

Wählen Sie einen hypothetischen Zeitpunkt für ein versehentliches Löschen.

Stellen Sie die Datenbank auf einen Wiederherstellungspunkt unmittelbar vor dem Incident zurück.

Stellen Sie sie in einer neuen Instanz wieder her, statt das Original zu überschreiben.

Vergleichen Sie die gelöschten Daten mit gültigen Schreibvorgängen, die danach stattfanden.

Erstellen Sie einen Korrekturplan, der nur die erforderlichen Datensätze erneut anwendet.

Lassen Sie die geschäftlich verantwortliche Person genehmigen, ob alle Daten auf einen einzigen Zeitpunkt zurückgesetzt werden dürfen.

Bauen Sie nach der Wiederherstellung Suchindex, Cache und abgeleitete Tabellen neu auf.

## Checkliste zur Verifikation

### Kapazität

- [ ] Workload-Mix und Peak spiegeln echten Traffic wider.
- [ ] Perzentillatenz und Sättigung werden gemeinsam untersucht.
- [ ] Traffic aus Wiederholungsversuchen ist im Lastmodell enthalten.
- [ ] Autoscaling-Verzögerung und Aufwärmzeit wurden gemessen.
- [ ] Admission Control greift vor dem Erreichen nachgelagerter Grenzen.
- [ ] Verbleibende Kapazität nach dem Verlust einer Zone wurde verifiziert.

### Backup

- [ ] RPO und Aufbewahrung sind für jedes Dataset definiert.
- [ ] Backup-Kopien sind von Produktionszugangsdaten isoliert.
- [ ] Wiederherstellung von Verschlüsselungsschlüsseln wurde getestet.
- [ ] Für Backupfehler und -alter existieren Warnungen.
- [ ] Sowohl Lösch- als auch Korruptionsszenarien wurden getestet.
- [ ] Geschäftsinvarianten wiederhergestellter Ergebnisse werden verifiziert.

### DR

- [ ] RTO und Wiederherstellungsreihenfolge sind für jedes Tier definiert.
- [ ] DNS, Identität und Observability sind im Plan enthalten.
- [ ] Eine andere Person kann das Runbook ausführen.
- [ ] Failover-Autorität und Fencing sind explizit.
- [ ] Failback und Datenabgleich wurden getestet.
- [ ] Tatsächliche Übungszeit wird erfasst und mit dem Ziel verglichen.

## Häufige Fehler und Grenzen

### Einen Lasttest in einen Wettbewerb um die höchste Produktionszahl verwandeln

Ziel ist nicht, mit einer Zahl zu prahlen, sondern Knickpunkt und sicheren Betriebsbereich zu finden.

### Glauben, Autoscaling ersetze Kapazitätsplanung

Quoten, Bereitstellungsverzögerung, zustandsbehaftete Engpässe und nachgelagerte Grenzen bleiben bestehen.

### Replikation als Backup behandeln

Auch Löschung und Korruption können schnell repliziert werden.

Ein unabhängiger Wiederherstellungspunkt ist erforderlich.

### Eine erfolgreiche Snapshot-Wiederherstellung als Dienstwiederherstellung dokumentieren

Anwendungsverbindung, Schema, Schlüssel und Verifikation einer Geschäftstransaktion fehlen.

### DR-Dokumentation schreiben, ohne sie zu erproben

Abhängigkeiten, Berechtigungen, Kontakte und Befehle ändern sich mit der Zeit.

Regelmäßige Proben halten das Dokument gültig.

## Offizielle Referenzen

- [AWS Well-Architected: Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)
- [Google SRE Book: Umgang mit Überlast](https://sre.google/sre-book/handling-overload/)
- [Kubernetes-Ressourcenverwaltung](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [NIST SP 800-34 Rev. 1: Leitfaden zur Notfallplanung](https://csrc.nist.gov/pubs/sp/800/34/r1/final)
- [PostgreSQL: Backup und Wiederherstellung](https://www.postgresql.org/docs/current/backup.html)

## Fazit

Kapazität und Disaster Recovery sind keine getrennten Dokumente, sondern verschiedene Größenordnungen derselben Zuverlässigkeitsfrage.

Messen Sie Grenzen unter normaler Last, begrenzen Sie Überlast, injizieren Sie Fehler und stellen Sie Backups tatsächlich wieder her.

Wiederherstellbarkeit wird nicht durch ein Architekturdiagramm belegt, sondern durch wiederholbare Wiederherstellungen und Aufzeichnungen, die die benutzerseitige Funktion verifizieren.
