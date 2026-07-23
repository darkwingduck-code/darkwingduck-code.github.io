---
title: "Grundlagen der Linux-Diagnose: Prozesse, Dateien, Signale und systemd als Evidenz lesen"
date: 2026-07-21 12:06:00 +0900
categories: [Linux, Operations]
tags: [linux, diagnostics, processes, signals, systemd]
description: Ein praxisnaher Ablauf, um Linux-Incidents anhand von Evidenz aus Prozessen, Deskriptoren, Dateisystemen, Signalen, Ressourcen und dem systemd-Journal einzugrenzen, statt mit einem Neustart zu beginnen.
lang: de-DE
translation_key: linux-diagnostics-processes-files-signals-systemd
hidden: true
---
{% include language-switcher.html %}

## Das Problem: Ein Neustart beseitigt die Symptome, erklärt aber nicht die Ursache

Wenn ein Linux-Dienst langsam ist oder nicht reagiert, kann ein sofortiger Neustart ihn vorübergehend wiederherstellen.

Dabei können jedoch Nachweise aus Arbeitsspeicher, Deskriptoren, Sockets, Kindprozessen, Dateisystemen und Abhängigkeiten verloren gehen.

Folgende Fehlannahmen verzögern die Diagnose.

- Eine geringe CPU-Auslastung bedeutet, dass der Prozess gesund ist.
- Wenig freier Arbeitsspeicher muss einen Speichermangel bedeuten.
- Wenn eine Datei existiert, muss sie lesbar sein.
- `kill` bedeutet erzwungenes Beenden.
- Wenn der Dienststatus aktiv ist, muss auch die benutzerseitige Funktion gesund sein.
- Die letzte Logzeile muss die Ursache sein.
- Die Ausführung als root ist eine akzeptable Umgehung von Berechtigungsproblemen.

Eine betriebliche Diagnose sollte `Beobachtung -> Hypothese -> minimale Prüfung -> sichere Entschärfung -> Verifikation` folgen.

## Denkmodell: Ein Prozess ist ein Bündel von Kernel-Ressourcen

Ein Prozess ist nicht bloß eine ausführbare Datei.

Er besitzt Folgendes.

- PID und PID des Elternprozesses
- Benutzer- und Gruppenidentität
- Virtuelle Speicherzuordnung
- Tabelle offener Dateideskriptoren
- Aktuelles Arbeitsverzeichnis
- Umgebung
- Signalbehandlung
- Mitgliedschaft in Namespaces und cgroups
- Threads und Scheduling-Zustand

Das Ersetzen einer ausführbaren Datei ändert nicht automatisch die Speicherzuordnung eines bereits laufenden Prozesses.

Eine gelöschte Datei kann weiterhin Plattenblöcke belegen, solange ein Deskriptor für sie offen bleibt.

### `/proc` ist ein Fenster in den laufenden Kernel

`/proc/<pid>/status` zeigt einen Überblick über Zustand und Speicher.

`/proc/<pid>/fd` zeigt offene Deskriptoren.

`/proc/<pid>/maps` zeigt Speicherzuordnungen.

`/proc/<pid>/limits` zeigt Ressourcengrenzen.

Berechtigungs- und Namespace-Grenzen gelten auch für Lesezugriffe.

### Dateideskriptoren verweisen nicht nur auf Dateien

Reguläre Dateien, Verzeichnisse, Sockets, Pipes, Geräte und Ereignisobjekte können allesamt Deskriptoren sein.

Ein Deskriptorleck kann sich nicht nur durch das Scheitern beim Öffnen von Dateien zeigen, sondern auch durch fehlgeschlagene neue Verbindungen.

Prüfen Sie sowohl die Grenzen pro Prozess als auch die systemweiten Grenzen.

### Ein Signal ist eine asynchrone Benachrichtigung

`SIGTERM` ist ein abfangbares Signal mit der Aufforderung zum geordneten Beenden.

`SIGKILL` kann von einem Prozess weder behandelt noch ignoriert werden.

Historisch bedeutet `SIGHUP` die Trennung eines Terminals; manche Daemons verwenden es für ein Neuladen, doch der Vertrag der Anwendung muss geprüft werden.

Die erfolgreiche Zustellung eines Signals und eine erfolgreiche Bereinigung durch die Anwendung sind verschiedene Dinge.

## Workflow: Reihenfolge zur Eingrenzung von Incidents

### Schritt 1. Das sichtbare Symptom genau bestimmen

- Wann begann es?
- Betrifft es jede Anfrage oder nur einen bestimmten Endpunkt?
- Handelt es sich um einen Timeout oder einen sofortigen Fehler?
- Ist ein Host oder die gesamte Flotte betroffen?
- Gab es kürzlich Änderungen an Deployment, Konfiguration, Zertifikaten oder Abhängigkeiten?

Erfassen Sie einen UTC-Zeitstempel und eine Korrelations-ID.

### Schritt 2. Den Zustand des Service Managers prüfen

```bash
systemctl status example.service --no-pager
systemctl show example.service -p ActiveState -p SubState -p Result -p MainPID
journalctl -u example.service --since "-30 min" --no-pager
```

`active (running)` sagt kaum mehr aus, als dass der Hauptprozess lebt.

Es garantiert nicht, dass geschäftliche Anfragen erfolgreich sind.

Prüfen Sie außerdem `ExecStart`, `User`, `WorkingDirectory`, `EnvironmentFile` und die Neustartrichtlinie der Unit.

### Schritt 3. Prozessbaum und Zustand untersuchen

```bash
ps -eo pid,ppid,user,stat,etimes,%cpu,%mem,cmd --forest
```

Die wichtigsten Hinweise in `STAT` sind:

- `R`: laufend oder ausführbar
- `S`: unterbrechbarer Schlafzustand
- `D`: nicht unterbrechbarer Schlafzustand, meist beim Warten auf I/O
- `T`: angehalten oder getraced
- `Z`: Zombie

Ein Zombie ist ein bereits beendeter Kindprozess, dessen Elternprozess seinen Exitstatus noch nicht abgeholt hat.

Ein Zombie selbst verbraucht fast keinen Speicher, doch ein anhaltender Anstieg weist auf einen Fehler des Elternprozesses hin.

### Schritt 4. CPU-Auslastung vom Scheduler-Verhalten trennen

Der Load Average ist nicht dasselbe wie die CPU-Auslastung.

Er kann ausführbare Tasks und einige nicht unterbrechbare Tasks umfassen.

```bash
uptime
vmstat 1
pidstat -p <PID> 1
```

Betrachten Sie User-CPU, System-CPU, I/O-Wartezeit und Kontextwechsel gemeinsam.

In einem Container kann eine cgroup-Quote zu Throttling führen.

Selbst wenn der Host noch CPU-Kapazität besitzt, kann der Workload eingeschränkt sein.

### Schritt 5. Speicher nach Bestandteilen betrachten

Linux verwendet freien Speicher als Page Cache.

Beachten Sie auch die Schätzung `available` von `free`.

```bash
free -h
cat /proc/<PID>/status
cat /proc/<PID>/smaps_rollup
```

Unterscheiden Sie RSS, virtuelle Größe, anonymen Speicher, dateibasierte Mappings und Shared Memory.

Prüfen Sie Kernel-Journal und cgroup-Ereignisse auf Hinweise auf einen OOM Kill.

```bash
journalctl -k --since "-1 hour" --no-pager
```

### Schritt 6. Deskriptoren und Sockets prüfen

```bash
ls -l /proc/<PID>/fd
cat /proc/<PID>/limits
ss -lntp
ss -antp
```

Vergleichen Sie den Trend der Deskriptoranzahl mit ihrer Grenze.

Prüfen Sie, ob sich Verbindungszustände auf `SYN-SENT`, `CLOSE-WAIT` oder `TIME-WAIT` konzentrieren.

Angehäufte `CLOSE-WAIT`-Verbindungen können darauf hinweisen, dass die Anwendung Sockets nach der Trennung durch die Gegenstelle nicht schließt.

### Schritt 7. Dateisystemkapazität von Inode-Kapazität trennen

```bash
df -h
df -i
findmnt
```

Inodes können erschöpft sein, obwohl noch Byte-Kapazität vorhanden ist.

Eine offene, gelöschte Datei fehlt in Verzeichnisauflistungen, verbraucht aber weiterhin Platz.

```bash
lsof +L1
```

Prüfen Sie außerdem Mount-Optionen, schreibgeschützte Remounts und die Latenz von Netzwerkdateisystemen.

### Schritt 8. Berechtigungen entlang des gesamten Pfads untersuchen

Der Dateimodus allein reicht nicht aus.

Für jedes übergeordnete Verzeichnis wird die Berechtigung zum Durchlaufen benötigt.

```bash
namei -l /path/to/resource
id example-user
getfacl /path/to/resource
```

Wenn SELinux oder AppArmor eingesetzt wird, prüfen Sie auch Ablehnungen durch MAC-Richtlinien.

Eine Ausführung als root kann die Ursache verschleiern und Berechtigungsgrenzen verletzen.

### Schritt 9. I/O und Syscalls in minimalem Umfang beobachten

```bash
iostat -xz 1
strace -f -p <PID> -tt -T
```

`strace` kann Overhead verursachen und sensible Daten offenlegen.

Verwenden Sie es kurz, filtern Sie auf die erforderlichen Syscalls und halten Sie die Betriebsrichtlinien ein.

Wenden Sie dieselben Sicherheitsprinzipien auf `perf` und eBPF-Werkzeuge an.

### Schritt 10. Sicher herunterfahren

Stoppen Sie den Dienst zuerst über den Service Manager.

```bash
systemctl stop example.service
```

Senden Sie bei Bedarf SIGTERM und beobachten Sie den Zustand während der Karenzzeit.

SIGKILL ist das letzte Mittel.

Sichern Sie vor einer erzwungenen Beendigung die benötigten Nachweise, etwa Stacks, Logs, Deskriptoren und die Core-Dump-Richtlinie.

## Eine systemd-Unit lesen

### Abhängigkeit und Reihenfolge sind verschieden

`After=` legt die Startreihenfolge fest, fügt aber nicht automatisch eine erforderliche Abhängigkeit hinzu.

`Requires=` und `Wants=` drücken Abhängigkeitsbeziehungen aus.

Dass das Netzwerk `online` ist, bedeutet nicht, dass eine Anwendungsabhängigkeit tatsächlich bereit ist.

### Eine Neustartrichtlinie kann Fehler verdecken

`Restart=on-failure` hilft bei der Wiederherstellung nach vorübergehenden Abstürzen.

Eine schnelle Absturzschleife kann jedoch Abhängigkeiten belasten.

Prüfen Sie Begrenzung der Startrate und Backoff.

Alarmieren Sie bei wiederholten Neustarts und erfassen Sie den neuesten Beendigungsgrund.

### Die Ausführungsumgebung unterscheidet sich von einer interaktiven Shell

PATH, Arbeitsverzeichnis, Umgebung, umask und Limits können abweichen.

Gehen Sie nicht davon aus, dass ein Shell-Profil automatisch geladen wird.

Geben Sie erforderliche Pfade in der Unit-Datei an.

Legen Sie Geheimnisse weder im Unit-Quelltext noch in der Befehlszeile offen.

## Praxisbeispiel: Der Dienst ist aktiv, aber die API läuft in einen Timeout

1. Endpunkt und Zeitstempel mit einer synthetischen Anfrage festhalten.
2. MainPID und Neustartverlauf mit `systemctl show` untersuchen.
3. Das Journal im selben Zeitraum nach Timeouts und Abhängigkeitsfehlern durchsuchen.
4. Zustände ausgehender Verbindungen mit `ss` untersuchen.
5. Anzahl in `/proc/<pid>/fd` mit dem Limit vergleichen.
6. CPU je Thread und blockierte Zustände untersuchen.
7. Eine begrenzte Diagnoseanfrage an den nachgelagerten Endpunkt senden.
8. Die Hypothese prüfen, dass Thread- oder Verbindungspool erschöpft ist.
9. Entscheiden, ob nach dem Ableiten des Traffics neu gestartet wird.
10. Nach der Wiederherstellung Benutzer-SLI und Ressourcenmetriken prüfen.

Wenn Sie neu gestartet haben, dokumentieren Sie dies nicht als Behebung der Grundursache.

Halten Sie separat `Symptome durch Neustart entschärft; Ursache unbestätigt` fest.

## Checkliste zur Verifikation

### Evidenzerhalt

- [ ] Zeitstempel des Symptoms und Auswirkungsumfang erfasst.
- [ ] Letzte Änderungen und Artefaktversion geprüft.
- [ ] Journal und Prozesszustand vor dem Neustart gesammelt.
- [ ] Core-Dump- und Datenschutzrichtlinien geprüft.
- [ ] Sichergestellt, dass Befehlsausgaben keine Geheimnisse enthalten.

### Prozesse und Ressourcen

- [ ] Prozessbaum und Eigentümer geprüft.
- [ ] CPU, Load und I/O-Wartezeit unterschieden.
- [ ] Sowohl Host- als auch cgroup-Grenzen geprüft.
- [ ] Speicherzusammensetzung und OOM-Ereignisse geprüft.
- [ ] Deskriptoren und Socket-Zustände geprüft.
- [ ] Sowohl Plattenbytes als auch Inodes geprüft.

### Dienstbetrieb

- [ ] Ausführungsbenutzer und Umgebung der Unit sind explizit.
- [ ] Geordnetes Herunterfahren mit SIGTERM getestet.
- [ ] Neustartstürme sind begrenzt.
- [ ] Bereitschaft wird vom bloßen Überleben des Prozesses unterschieden.
- [ ] Journal-Aufbewahrung und Zeitsynchronisierung geprüft.
- [ ] Benutzerseitige Funktion nach der Wiederherstellung verifiziert.

## Häufige Fehler und Grenzen

### Mit `kill -9` beginnen

Damit werden sowohl Bereinigungs- als auch Diagnose-Hooks umgangen.

Auch die Möglichkeit einer Beschädigung gemeinsam genutzten Zustands muss berücksichtigt werden.

### Nur Hostmetriken betrachten

Container und systemd-Dienste können Ressourcen innerhalb ihrer cgroup-Grenzen erschöpfen.

### Annehmen, kein Log bedeute, dass kein Ereignis stattfand

Logs können wegen eines Absturzes vor dem Leeren des Puffers, Sampling, Ratenbegrenzung oder vollen Speichers verloren gehen.

Gleichen Sie Metriken, Kernel-Ereignisse und Traces miteinander ab.

### Einen Prozess im Zustand `D` sofort mit einem Signal entfernen wollen

Die Signalverarbeitung kann sich verzögern, bis der nicht unterbrechbare Kernel-Wartezustand beendet ist.

Untersuchen Sie den zugrunde liegenden I/O- und Gerätezustand.

### Unbegrenztes Tracing in Produktion ausführen

Das Diagnosewerkzeug selbst kann Latenz- und Speicherprobleme verursachen.

Definieren Sie Umfang, Dauer, Filter und Rollback vor dem Einsatz.

## Offizielle Referenzen

- [Linux-man-pages-Projekt](https://www.kernel.org/doc/man-pages/)
- [proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html)
- [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html)
- [systemd.service](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)
- [Linux-Kernel-Dokumentation zu cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)

## Fazit

Bei der Linux-Diagnose geht es nicht darum, Befehle auswendig zu lernen, sondern die vom Kernel an den richtigen Grenzen offengelegte Evidenz zu lesen.

Prüfen Sie Hypothesen, indem Sie Prozesse, Deskriptoren, Speicher, Dateisysteme, Signale, cgroups und den Service Manager miteinander verbinden.

Selbst wenn ein Neustart nötig ist, sollten Sie zuerst Nachweise bewahren und die Wiederherstellung anhand der benutzerseitigen Funktion verifizieren, um wiederkehrende Incidents zu reduzieren.
