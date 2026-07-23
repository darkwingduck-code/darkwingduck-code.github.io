---
title: "Branches, PRs, Merge, Rebase und ein sicherer Git-Wiederherstellungsleitfaden"
date: 2026-07-21 09:10:00 +0900
categories: [Platform Engineering, Git]
tags: [git, branching, pull-request, rebase, recovery]
description: Eine PR-Integrationsstrategie anhand des Branch- und Commit-Graphen auswählen und Fehler sicher beheben, ohne Daten zu verlieren.
lang: de-DE
translation_key: git-branch-pr-rebase-recovery
hidden: true
---

{% include language-switcher.html %}

## Das Problem: Git-Incidents wachsen, wenn übersehen wird, ob der Verlauf geteilt ist – nicht wegen eines Befehls

Die Wiederherstellung unterscheidet sich grundlegend danach, ob derselbe Fehler noch ausschließlich lokal existiert oder bereits auf ein Remote publiziert wurde. Lokale Commits lassen sich relativ frei umschreiben. Ändert man jedoch öffentliche Commits, auf denen andere ihre Arbeit aufgebaut haben, durch Rebase oder Force Push, stört dies sowohl den Verlauf der Kollegen als auch CI-Referenzpunkte.

Drei Fragen genügen für eine sichere Entscheidung.

1. Befindet sich die nicht zu verlierende Änderung im Working Tree, in der Staging Area oder in einem Commit?
2. Hat jemand anderes den Ziel-Commit bereits abgerufen?
3. Soll das Ergebnis mit neuem Verlauf entgegenwirken oder bestehenden Verlauf umschreiben?

Beginnen Sie nicht mit einem Wiederherstellungsbefehl. Erfassen Sie zuerst Status und Graph.

```bash
git status --short --branch
git log --graph --decorate --oneline --all -n 30
git reflog -n 20
```

## Denkmodell: Ein Branch ist ein Name, der auf einen Commit verweist

Wer einen Branch als „Kopie eines Ordners“ betrachtet, versteht Merge und Rebase nur schwer. Ein Branch ist eine leichtgewichtige Referenz auf eine Commit-ID.

```text
          F1---F2  feature
         /
M1---M2---M3      main
```

`feature` verweist auf `F2`, `main` auf `M3`. Es gibt drei typische Wege, beide Branches zu integrieren.

| Methode | Ergebnis | Besonders geeignet für | Vorsicht |
|---|---|---|---|
| Merge Commit | Erstellt einen Integrations-Commit mit zwei Eltern | Erhalt von Branchstruktur und einzelnen Commits | Verlauf kann komplex werden |
| Squash Merge | Integriert PR-Änderungen als einen neuen Commit | Kleine Features und unaufgeräumte Arbeits-Commits | Commit-Grenzen im PR verschwinden |
| Rebase + Fast-forward | Spielt Feature-Commits auf der neuesten Basis erneut ab | Linearer Verlauf mit aussagekräftigen Commits | Commit-IDs ändern sich; Vorsicht beim Umschreiben öffentlichen Verlaufs |

Vor dem Rebase:

```text
          F1---F2  feature
         /
M1---M2---M3      main
```

Nach dem Rebase von `feature` auf `main`:

```text
M1---M2---M3---F1'---F2'  feature
```

Auch wenn `F1'` und `F2'` ähnliche Inhalte besitzen, sind sie neue Objekte mit anderen Eltern und Commit-IDs. Rebase „verschiebt“ Commits nicht, sondern **erzeugt Patches auf einer neuen Basis neu**.

### Ein PR ist eine Einheit der Änderungskontrolle über Git hinaus

Ein Pull Request verbindet einen Branchvergleich mit folgenden Elementen.

- Diskussion und Entwurfsbegründung
- Automatisierte Tests und statische Analyse
- Freigabe durch Code Owner
- Schutzregeln der Deployment-Umgebung
- Auditierbare Integrationsentscheidung

Ein guter PR ist daher nicht bloß „ein Ort zum Hochladen von Code“, sondern ein Paket aus Änderungsrisiken, Validierungsevidenz und Rollback-Methoden.

## Praktisches Muster: Kurze Branches, explizite Integration und ein Snapshot vor der Wiederherstellung

### Grundablauf für einen kleinen Feature-Branch

```bash
git switch main
git fetch origin
git merge --ff-only origin/main

git switch -c feature/health-endpoint

# 편집과 테스트 후
git add --patch
git diff --staged
git commit -m "feat: add dependency-aware health endpoint"
git push --set-upstream origin feature/health-endpoint
```

Je kürzer ein Branch lebt, desto kleiner ist seine Konfliktfläche. Auch ein großes Feature kann durch Feature Flags, vorgezogene Schnittstellenänderungen und das Expand/Contract-Muster für Datenmigrationen aufgeteilt und häufig in `main` integriert werden.

Nehmen Sie mindestens Folgendes in die PR-Beschreibung auf.

```markdown
## 왜 필요한가
<문제와 사용자 영향>

## 무엇이 바뀌는가
<핵심 설계와 범위 밖 항목>

## 어떻게 검증했는가
<테스트 명령, 관찰 결과, 수동 확인>

## 위험과 복구
<호환성, migration, feature flag, rollback>
```

### Zwei Wege, einen Feature-Branch mit `main` zu aktualisieren

Wenn das Team einen Merge-basierten Workflow verwendet:

```bash
git fetch origin
git switch feature/health-endpoint
git merge origin/main
```

Wenn das Team einen Rebase-basierten Workflow verwendet und Sie praktisch die einzige Person auf dem Feature-Branch sind:

```bash
git fetch origin
git switch feature/health-endpoint

# 복구 지점을 먼저 만든다.
git branch backup/health-endpoint-before-rebase

git rebase origin/main
```

Wenn Git bei einem Konflikt anhält, wiederholen Sie folgende Sequenz.

```bash
git status

# 파일에서 conflict marker를 해결하고 테스트한다.
git add <RESOLVED_FILE>
git rebase --continue
```

Wenn Sie bei der Auflösung unsicher sind, kehren Sie zum ursprünglichen Zustand zurück.

```bash
git rebase --abort
```

Wenn Sie nach dem Rebase den bestehenden Remote-Feature-Branch aktualisieren müssen, verwenden Sie statt eines gewöhnlichen `--force` Folgendes.

```bash
git push --force-with-lease
```

`--force-with-lease` versucht die Remote-Referenz nur zu überschreiben, wenn sie noch den zuletzt beobachteten Wert besitzt. Es garantiert nicht absolut, dass jeder neue Push einer anderen Person erhalten bleibt; Schutzregeln für gemeinsam genutzte Branches und Teamvereinbarungen haben daher Vorrang. Erlauben Sie Force Pushes nicht auf geschützten Branches wie `main`.

### Sichere Wiederherstellung nach Fehlertyp

#### 1. Eine noch nicht gestagte Änderung soll verworfen werden

Lesen Sie zuerst das Diff und bestätigen Sie, dass das Verwerfen wirklich sicher ist.

```bash
git diff -- <FILE>
git restore -- <FILE>
```

Da `git restore` Inhalte des Working Tree ändert, können uncommittete Änderungen verloren gehen. Geben Sie den Dateinamen präzise an; bewahren Sie die Änderung bei Unsicherheit zuerst als Patchdatei oder Commit auf einem temporären Branch.

#### 2. Nur `add` soll rückgängig gemacht, der bearbeitete Inhalt aber erhalten werden

```bash
git diff --staged -- <FILE>
git restore --staged -- <FILE>
git diff -- <FILE>
```

Dies nimmt die Änderung nur aus der Staging Area und lässt die Änderung im Working Tree im Allgemeinen bestehen.

#### 3. Die letzte lokale Commit-Nachricht soll korrigiert oder eine fehlende Datei hinzugefügt werden

Bestätigen Sie, dass der Commit noch nicht geteilt wurde.

```bash
git status --short --branch
git log --oneline origin/<BRANCH>..HEAD

# 필요한 변경을 stage한 뒤 마지막 커밋을 다시 만든다.
git add <FILE>
git commit --amend
```

Auch Amend erzeugt eine neue Commit-ID. Wenn der Commit bereits publiziert wurde, ist ein Folge-Commit in der Regel sicherer.

#### 4. Die Wirkung eines falschen öffentlichen Commits soll rückgängig gemacht werden

Erfassen Sie die umgekehrte Änderung in einem neuen Commit, ohne den öffentlichen Verlauf zu löschen.

```bash
git show <COMMIT_ID>
git revert <COMMIT_ID>
```

Beim Revert eines Merge Commits muss der Mainline-Elternteil gewählt werden; dies kann spätere erneute Merges beeinflussen. Prüfen Sie in diesem Fall Graph und Deployment-Zustand und folgen Sie dem Teamverfahren.

#### 5. Nach Reset oder Rebase scheint ein Commit verloren zu sein

In den meisten Fällen wurde das Objekt nicht sofort gelöscht; der Branch verweist nur nicht mehr darauf. Finden Sie das vorherige `HEAD` im Reflog.

```bash
git reflog --date=local
git show <RECOVERABLE_COMMIT_ID>
git branch recovery/<SHORT_NAME> <RECOVERABLE_COMMIT_ID>
```

Prüfen Sie nach Erstellung eines Recovery-Branches Dateien und Tests und führen Sie dann Cherry-pick oder Merge in den normalen Branch durch. Der Reflog erfasst Referenzbewegungen in einem lokalen Repository; er ist kein dauerhaftes Backup. Bereinigungsrichtlinien und Zeitablauf können Objekte entfernen.

#### 6. Auf einem völlig falschen Branch gearbeitet

Verwerfen Sie die Änderungen nicht. Bewahren Sie sie am aktuellen Ort in einem Commit oder Stash und wechseln Sie anschließend. Ein Commit auf einem temporären Branch ist die am besten auditierbare Methode.

```bash
git switch -c recovery/wrong-branch-work
git add --patch
git commit -m "wip: preserve work before branch correction"

git switch <TARGET_BRANCH>
git cherry-pick <PRESERVED_COMMIT_ID>
```

Wenn kein WIP-Commit im endgültigen Verlauf verbleiben soll, squashen Sie ihn bei der PR-Integration oder bereinigen Sie ihn vor der Publikation per interaktivem Rebase.

### `reset`-Modi unterscheiden sich darin, wie weit sie die drei Bereiche verschieben

| Modus | Branch/HEAD | Staging Area | Working Tree | Typisches Risiko |
|---|---:|---:|---:|---|
| `--soft` | Wird verschoben | Bleibt erhalten | Bleibt erhalten | Falschen Verlaufspunkt wählen |
| Standard `--mixed` | Wird verschoben | Wird auf Ziel-Commit gesetzt | Bleibt erhalten | Gestagter Zustand wird entfernt |
| `--hard` | Wird verschoben | Wird auf Ziel-Commit gesetzt | Wird auf Ziel-Commit gesetzt | Verlust uncommitteter Arbeit |

`git reset --hard` ist nicht der erste Schritt einer Wiederherstellung. Falls er nötig ist, bewahren Sie die aktuelle Commit-ID und Änderungen des Working Tree an einem separaten sicheren Punkt, verifizieren Sie den Ziel-Commit mit `git show` und verwenden Sie den Befehl anschließend in begrenztem Umfang. `revert` ist der Standard zum Rückgängigmachen geteilten Verlaufs.

### Schutzmaßnahmen zum Bestandteil der Repository-Richtlinie machen

Menschliche Aufmerksamkeit allein kann `main` nicht schützen. Erzwingen Sie in den Repository-Einstellungen:

- Änderungen nur über PRs zulassen
- Erfolgreiche Status Checks verlangen
- Eine Mindestzahl von Freigaben fordern und veraltete Freigaben verwerfen
- Für relevante Pfade Eigentümerprüfung durch CODEOWNERS verlangen
- Integration bei ungelösten Diskussionen blockieren
- Force Pushes und Branch-Löschung einschränken
- Administrator-Bypasses als Ausnahmeverfahren erfassen

## Checkliste zur Validierung

Vor der Integration eines PR:

- [ ] Der Änderungsumfang konzentriert sich auf einen Zweck.
- [ ] Der Basisbranch ist korrekt und enthält keine unnötigen Commits oder Dateien.
- [ ] Neben automatisierten Tests wurden Fehlerpfade und Rollback geprüft.
- [ ] Rückwärtskompatibilität von Daten-, API- und Konfigurationsänderungen wurde verifiziert.
- [ ] Integrationsmethode – Merge, Squash oder Rebase – entspricht der Repository-Richtlinie.
- [ ] Metriken vor und nach dem Deployment sowie ihre Verantwortlichen sind klar.

Vor einem Wiederherstellungsbefehl:

- [ ] `status`, `log --graph --all` und `reflog` wurden erfasst.
- [ ] Es wurde bestimmt, ob die Änderungen nur lokal oder bereits geteilt sind.
- [ ] Ein Sicherungsbranch oder -Commit wurde erstellt.
- [ ] Datei-, Branch- und Commit-IDs wurden präzise angegeben.
- [ ] Wenn ein Geheimnis offengelegt wurde, erfolgten Widerruf und Neuausgabe der Zugangsdaten vor Git-Manipulationen.
- [ ] Diff, Tests und Remote-Graph wurden nach der Wiederherstellung erneut geprüft.

## Fehlerfälle und Grenzen

### Einen langlebigen Branch auf einmal integrieren

Das Problem bei Konflikten ist ihre Bedeutung, nicht ihre Zeilenzahl. Auf einem lange getrennten Branch ändert sich die Entwurfsabsicht beider Seiten; selbst ohne Textkonflikte können Verhaltenskonflikte entstehen. Kleine PRs und kontinuierliche Integration senken Wiederherstellungskosten.

### Einen öffentlichen Branch achtlos rebasen

Rebase selbst ist nicht gefährlich; eine gemeinsam genutzte Grundlage ohne Vereinbarung zu ersetzen ist es. Unterscheiden Sie die Bereinigung eines persönlichen Feature-Branches von der Änderung des Verlaufs eines geteilten Branches.

### Einen Konflikt nach bloßem Entfernen seiner Marker für gelöst halten

Das Entfernen von `<<<<<<<`, `=======` und `>>>>>>>` bedeutet nicht, dass die Absichten beider Seiten bewahrt wurden. Führen Sie nach der Konfliktauflösung relevante Tests, Typprüfungen und Validierungen der Datenmigration erneut aus.

### Glauben, das Entfernen eines Geheimnisses aus dem Commit-Verlauf beende den Incident

Nach dem Push eines Tokens oder Schlüssels kann er bereits in Klonen, CI-Logs, Caches und Forks verbleiben. Widerrufen und ersetzen Sie das Geheimnis zuerst. Wenn eine Verlaufsbereinigung nötig ist, behandeln Sie sie als separate Incident Response, die von Repository-Administratoren und allen Benutzern koordiniert wird. Ein einseitiger Force Push kann den gemeinsamen Verlauf zerstören, ohne die Offenlegung rückgängig zu machen.

### Den Reflog als Backup behandeln

Der Reflog ist äußerst nützlich, aber ein lokaler und temporärer Wiederherstellungsmechanismus. Er ersetzt weder Remote Pushes, geschützte Branches, Tags, Artefaktaufbewahrung noch eine Repository-Backup-Richtlinie.

Zweck einer guten Git-Strategie ist kein „schöner Graph“. Sie soll Änderungen klein halten, Review-Evidenz bewahren und jedem ermöglichen festzustellen, zu welchem Commit nach einem Fehler zurückgekehrt werden muss.
