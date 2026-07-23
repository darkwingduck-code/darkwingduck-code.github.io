---
title: "Deterministische Simulationen testen: Invarianten, eigenschaftsbasiertes Testen und Replay"
date: 2026-07-21 09:40:00 +0900
categories: [Software Engineering, Simulation Testing]
tags: [determinism, simulation-testing, invariants, property-based-testing, replay, regression-testing, reproducibility]
description: "Erfahren Sie, wie deterministische Simulatoren mit Invarianten, generativen Eigenschaftstests, Zustands-Hashes und Ereignis-Replay statt nur mit einigen Beispielen validiert werden."
math: true
lang: de-DE
hidden: true
translation_key: deterministic-simulation-testing-invariants-replay
---

{% include language-switcher.html %}

Beschränkt sich das Testen einer Simulation darauf, „eine repräsentative Eingabe auszuführen und zu prüfen, ob der Graph ähnlich aussieht“, bleibt unklar, welches Gesetz durch eine kleine Änderung verletzt wurde. Wird umgekehrt eine vollständige Ausgabedatei als Golden File eingefroren, scheitern Tests an harmlosen Gleitkommaabweichungen und können ein falsches Althergebnis für immer festschreiben.

Eine belastbarere Strategie verbindet drei Ebenen.

1. **Invarianten und Beziehungen**, die jeder korrekte Lauf erfüllen muss
2. **Eigenschaftsbasierte Tests**, die einen breiten Eingaberaum automatisch erkunden
3. **Replay von Seeds, Ereignissen und Zuständen**, das einen Fehler exakt reproduziert

## 1. Zuerst drei Begriffe unterscheiden

### Determinismus

Die Eigenschaft, aus demselben Anfangszustand, derselben Eingabe, Konfiguration und Ausführungsumgebung dieselben Zustandsübergänge zu erhalten.

$$
s_{t+1}=F(s_t,u_t;\theta)
$$

muss für dieselben \(s_t,u_t,\theta\) dasselbe \(s_{t+1}\) ergeben.

### Reproduzierbarkeit

Die Fähigkeit, ein Ergebnis zu einem anderen Zeitpunkt oder in einer anderen Umgebung innerhalb eines zulässigen Bereichs wiederherzustellen. Sie ist weiter gefasst als bitweiser Determinismus und erfordert Informationen über Quellcode, Abhängigkeiten, Konfiguration, Daten, Compiler und Hardware.

### Robustheit

Die Eigenschaft, dass eine Schlussfolgerung bei zulässigen Änderungen der Eingabe oder Umgebung stabil bleibt. Ein Programm, das für dieselbe Eingabe stets dieselbe falsche Antwort liefert, ist deterministisch, aber weder robust noch korrekt.

## 2. Verborgene Eingaben, die Determinismus brechen

Die Funktionsargumente im Code sind nicht die einzigen Eingaben. Auch Folgendes kann Zustandsübergänge beeinflussen.

- Seed und Algorithmus des Pseudozufallszahlengenerators
- Wanduhrzeit und Locale
- Iterationsreihenfolge einer Hash-Map
- Thread-Scheduling und Reduktionsreihenfolge
- atomare Operationen in GPU-Kernels
- Compiler-Flags und Fast Math
- BLAS, Laufzeit und Treiber
- Reihenfolge der Dateiauflistung
- Umgebungsvariablen und Konfigurationsvorgaben
- Antworten externer Dienste
- nicht initialisierter Speicher

„Wir haben den Seed festgelegt“ stellt daher noch keinen vollständigen Determinismus her. Zufallsströme werden besser nach Subsystem getrennt, damit eine veränderte Ausführungsreihenfolge nicht den Zufallszahlenverbrauch eines anderen Subsystems verschiebt.

## 3. Ein Testgitter statt einer Testpyramide

Ein Simulator benötigt mehrere Arten von Orakeln.

| Testart | Frage | Besonders gut erkennbare Fehler |
|---|---|---|
| Unit-Test | Verhält sich eine kleine Operation wie definiert? | Vorzeichen, Einheiten, Indizes, Randbehandlung |
| analytischer/Benchmark-Test | Konvergiert das Verfahren gegen eine bekannte Lösung? | Implementierung von Gleichung oder Schema |
| Invariantentest | Befolgt es Gesetze, die erhalten bleiben müssen? | kumulative Drift, fehlende Quellen |
| eigenschaftsbasierter Test | Gelten Eigenschaften über breite gültige Eingaben hinweg? | unerwartete Randfälle |
| metamorpher Test | Stimmen Ausgabebeziehungen bei Eingabetransformationen? | logische Fehler bei Problemen ohne Orakel |
| differenzieller Test | Stimmt es mit einer unabhängigen Implementierung überein? | implementierungsspezifische Abweichung |
| Regressions-/Golden-Test | Ist genehmigtes Verhalten unverändert geblieben? | unbeabsichtigte Änderungen |
| Replay-Test | Lässt sich ein früherer Fehler exakt reproduzieren? | Nichtdeterminismus, ausgelassener Zustand |

Keine Testart ersetzt eine andere. Ein Erhaltungstest kann bestehen, obwohl die räumliche Verteilung falsch ist; eine Golden-Ausgabe kann übereinstimmen, obwohl die Referenz selbst falsch ist.

## 4. Invarianten in ausführbare Spezifikationen verwandeln

Eine Invariante darf nicht nur als Satz in der Dokumentation stehen, sondern sollte in jedem Lauf als Assertion ausgewertet werden.

### Erhaltungsgleichung

Für die allgemeine Bilanz

$$
M_{t+1}
=
M_t+\Delta t\,(I_t-O_t+S_t)+e_t
$$

muss der Defekt

$$
d_t=M_{t+1}-M_t-\Delta t\,(I_t-O_t+S_t)
$$

innerhalb der numerischen Toleranz bleiben.

### Grenzen und Positivität

Zustände mit eingeschränkten Domänen wie Wahrscheinlichkeiten, Konzentrationen und Massenanteilen müssen Grenzen wie

$$
0\le x_i\le 1
$$

einhalten. Zugleich ist zu prüfen, ob das Schema eine kleine Unterschreitung zulässt und ob Clipping die Erhaltung verletzt. Negative Werte einfach durch null zu ersetzen, kann einen Fehler verbergen.

### Symmetrie und Äquivarianz

Soll das Drehen, Spiegeln oder Permutieren der Eingabekoordinaten dieselbe physikalische Transformation in der Ausgabe bewirken, wird

$$
f(Tx)=Tf(x)
$$

getestet. Diese Beziehung liefert auch dann ein starkes Orakel, wenn die korrekten Ausgabewerte unbekannt sind.

### Dimensionskonsistenz und Skalierungsbeziehungen

Wenn ein Einheitenwechsel denselben physikalischen Zustand ausdrückt, sollten dimensionslose Ausgaben unverändert bleiben. Zuerst ist herzuleiten, ob die Skalierungsinvarianz für die zugrunde liegende Gleichung und die Randbedingungen tatsächlich gilt.

### Zustandsautomaten-Invarianten

- Eine nicht vorhandene Entität nicht zweimal entfernen.
- Ein abgeschlossenes Ereignis nicht erneut verarbeiten.
- Ressourcenzahlen werden nie negativ.
- Zeitstempel nehmen entgegen der kausalen Reihenfolge nicht ab.
- Der Lebenszyklus jeder Entitäts-ID folgt ausschließlich gültigen Zustandsübergängen.

## 5. Absolute und relative Toleranzen gemeinsam verwenden

Die Grundform eines Gleitkommavergleichs lautet

$$
|a-b|
\le
\mathrm{atol}
+\mathrm{rtol}\cdot s
$$

wobei \(s\) eine problemgerechte Referenzskala ist.

~~~python
def assert_close(actual, expected, *, atol, rtol, scale=None):
    reference_scale = abs(expected) if scale is None else abs(scale)
    error = abs(actual - expected)
    limit = atol + rtol * reference_scale
    assert error <= limit, {
        "actual": actual,
        "expected": expected,
        "error": error,
        "limit": limit,
    }
~~~

Relative Fehler allein sind ungeeignet, wenn der Erwartungswert nahe null liegt; absolute Fehler allein lassen sich bei großen Werten schwer interpretieren. Eine Toleranz ist keine nachträglich angepasste Zahl, mit der ein Test zum Bestehen gebracht wird, sondern sollte ein Fehlerbudget sein, das auf Folgendem beruht:

- Diskretisierungs- und Abschneidefehler
- Toleranz des iterativen Lösers
- Grenzen der Gleitkommaakkumulation
- Mess- oder Eingabegenauigkeit
- Entscheidungsschwellen nachgelagerter Systeme

## 6. Eigenschaftsbasiertes Testen: Eigenschaften statt Beispiele erzeugen

Ein beispielbasierter Test prüft nur Punkte, an die eine Person gedacht hat. Eigenschaftsbasiertes Testen erzeugt gültige Eingaben und verkleinert einen Fehler zu einem einfacheren Gegenbeispiel.

Das folgende Beispiel ist konzeptionell.

~~~python
from hypothesis import given, strategies as st

@given(
    total=st.floats(min_value=0.0, max_value=1.0e3,
                    allow_nan=False, allow_infinity=False),
    fraction=st.floats(min_value=0.0, max_value=1.0,
                       allow_nan=False, allow_infinity=False),
)
def test_partition_conserves_total(total, fraction):
    left, right = partition(total, fraction)

    assert left >= 0.0
    assert right >= 0.0
    assert_close(
        left + right,
        total,
        atol=1.0e-12,
        rtol=1.0e-12,
    )
~~~

Diese Zahlen veranschaulichen die Codeform; sie sind keine Kriterien für ein bestimmtes Projekt. Tatsächliche Toleranzen werden aus Rechengenauigkeit und Fehlerbudget abgeleitet.

### Eigenschaften eines guten Generators

- Er erfüllt physikalisch gültige Bedingungen.
- Er erzeugt ausreichend Randwerte, Nullen, sehr kleine Werte und große dynamische Bereiche.
- Er erzeugt korrelierte Variablen nicht unabhängig voneinander.
- Er trennt Tests ungültiger Eingaben von Eigenschaftstests der gültigen Domäne.
- Er speichert nicht nur den fehlgeschlagenen Seed, sondern auch die verkleinerte Minimaleingabe.

Anders als Fuzzing, das ein Programm lediglich mit vielen zufälligen Eingaben bewirft, legt eigenschaftsbasiertes Testen fest, **was wahr sein muss**.

## 7. Metamorphes Testen: die Beziehung kennen, auch wenn die Antwort unbekannt ist

Bei einer komplexen Simulation ist die exakte Ausgabe für eine beliebige Eingabe schwer zu kennen. Stattdessen wird die erwartete Beziehung zwischen Ausgaben geprüft, wenn die Eingabe transformiert wird.

Zum Beispiel:

- Eine geänderte Entitätsreihenfolge lässt permutationsinvariante Aggregate unverändert.
- Werden Domäne und Quelle um dieselbe Symmetrie verschoben, verschiebt sich die Ausgabe identisch.
- Ein Grenzfall mit einer Quelle von null erreicht einen bekannten einfachen Zustand.
- Die Summe zweier unabhängiger kombinierter Subsysteme entspricht der Summe ihrer jeweiligen Einzelwerte.
- Zwei aufeinanderfolgende Zeitintervalle stimmen innerhalb des Checkpoint-Fehlers mit einem ununterbrochenen Lauf überein.

Die letzte Beziehung prüft sowohl die Halbgruppeneigenschaft als auch die Checkpoint-Serialisierung.

$$
F_{t_2}\left(F_{t_1}(s_0)\right)
\approx
F_{t_1+t_2}(s_0).
$$

Adaptive Löser oder Ereignislokalisierung können andere Ausführungspfade einschlagen; deshalb ist die erforderliche Äquivalenzstufe ausdrücklich zu definieren.

## 8. Für Replay erforderliche Mindestaufzeichnungen

Um einen Fehler zu reproduzieren, werden **Eingabeereignisse und Zustandsherkunft** benötigt, nicht bloß Logmeldungen.

### Laufmanifest

~~~yaml
schema_version: 1
run_id: "<opaque-run-id>"
source_revision: "<commit>"
configuration_digest: "<hash>"
input_digest: "<hash>"
dependency_lock_digest: "<hash>"
random_streams:
  initialization: "<seed>"
  events: "<seed>"
execution:
  worker_count: "<count>"
  numeric_mode: "<mode>"
~~~

Die Platzhalter sind durch tatsächliche Werte zu ersetzen; Geheimnisse, Benutzerpfade oder interne Hostnamen dürfen nicht enthalten sein.

### Ereignisprotokoll

In einem Event-Sourcing-Entwurf erhält jedes Ereignis:

- eine monoton steigende Sequenznummer,
- Simulationszeit und logische Zeit,
- Ereignistyp und Schemaversion,
- eine kanonische Nutzlast,
- einen Digest des Vor- oder Nachzustands und
- ein kausales Elternelement oder einen Korrelationsschlüssel.

Die Replay-Engine ersetzt externe Ein-/Ausgaben durch aufgezeichnete Antworten und wendet die Ereignisfolge in derselben Reihenfolge an.

### Checkpoint

Einen langen Lauf von Anfang an wiederzugeben, ist teuer. Ein versionierter Checkpoint wird zusammen mit dem nachfolgenden Ereignisprotokoll gespeichert. Der Checkpoint-Loader muss Migrationen von älteren Schemata testen oder bei einer nicht unterstützten Version eindeutig fehlschlagen.

## 9. Fallstricke von Zustands-Hashes

Ein Zustands-Hash hilft, den Schritt zu finden, in dem die Abweichung beginnt, ist ohne Kanonisierung jedoch unzuverlässig.

- Map-Schlüssel sortieren.
- Serialisierungsformat und Schemaversion festlegen.
- Flüchtige Caches und Zeitstempel ausschließen.
- Regeln für NaN-Darstellung und vorzeichenbehaftete Null definieren.
- Gleitkommazahlen nicht hashen, nachdem sie willkürlich gerundet in Zeichenketten umgewandelt wurden.

Ein diskreter Kern, der bitweise Gleichheit verlangt, ist von numerischen Feldern zu trennen, für die Toleranzvergleiche geeignet sind. So können Ereignisreihenfolge und Entitätsanzahl exakt verglichen werden, stetige Felder dagegen anhand von Normen und Invarianten.

## 10. Parallele Berechnung und reproduzierbare Reduktion

Gleitkommaaddition ist nicht exakt assoziativ.

$$
(a+b)+c\neq a+(b+c)
$$

Daher können Reduktionsergebnisse je nach Thread-Scheduling variieren. Mögliche Lösungen sind:

- eine feste Partition und ein fester Reduktionsbaum
- paarweise oder kompensierte Summation
- ein deterministischer Bibliotheksmodus
- ein exakter Akkumulator für kritische Summen
- ein Kriterium numerischer statt bitweiser Äquivalenz

Eine nichtdeterministische Reduktion kann aus Leistungsgründen zulässig sein. Dann wird mit statistischen oder toleranzbasierten Tests bestätigt, dass die Ergebnisse innerhalb des erlaubten Bereichs bleiben; zugleich ist vertraglich zu dokumentieren, dass kein exaktes Replay verfügbar ist.

## 11. Regressions- und Golden Files sicher einsetzen

Golden-Tests sind nützlich, um Änderungen an APIs, Formaten und repräsentativen Trajektorien zu erkennen, erfordern aber folgende Grundsätze.

1. Auch das Verfahren zur Golden-Erzeugung wird versioniert.
2. Bei der Freigabe wird eine menschenlesbare Zusammenfassung des Diffs vorgelegt.
3. Wichtige Zielgrößen und Invarianten werden einer vollständigen großen Binärdatei vorgezogen.
4. Toleranzen und Reihenfolge werden festgelegt.
5. Referenzaktualisierungen werden von gewöhnlichen Testläufen getrennt.
6. Golden-Tests werden nicht ohne analytische oder Invariantentests eingesetzt.

„Die Referenzdatei automatisch mit der neuen Ausgabe überschreiben“ schaltet Regressionstests aus.

## 12. Ein Arbeitsablauf, der Fehler zu Vermögenswerten macht

1. Einen Fehler in der Produktion oder in einem generativen Test erkennen.
2. Quellrevision, Manifest, Minimaleingabe, Ereignisprotokoll und Checkpoint aufbewahren.
3. Bestätigen, dass Replay den Fehler reproduziert.
4. Den ersten Zustands-Digest finden, an dem die Abweichung beginnt.
5. Den kleinsten Invarianten- oder Eigenschaftstest hinzufügen, der die Ursache erklärt.
6. Nach der Korrektur sowohl den neuen Test als auch die vorhandene Testsuite bestehen.
7. Den Minimalfall im Korpus der Gegenbeispiele behalten.
8. War Nichtdeterminismus selbst die Fehlerursache, einen eigenen Test mit wiederholtem Scheduling hinzufügen.

## 13. Prüfliste zur Verifikation

- [ ] Wurden Determinismus, Reproduzierbarkeit und Korrektheit unterschieden?
- [ ] Wurden neben dem Seed auch verborgene Eingaben und die Ausführungsumgebung aufgezeichnet?
- [ ] Wurden Zufallsströme nach Subsystem getrennt?
- [ ] Sind kritische Erhaltungsgleichungen und Grenzen Laufzeit-Assertions oder Tests?
- [ ] Berücksichtigt der Eigenschaftsgenerator physikalische Bedingungen und Randwerte?
- [ ] Wurden metamorphe Beziehungen aus den maßgeblichen Regeln hergeleitet?
- [ ] Besitzen Toleranzen eine numerische Begründung und Einheiten?
- [ ] Wurden Ziele für exakten und approximativen Vergleich getrennt?
- [ ] Wurden die verkleinerte Eingabe und der Seed jedes Fehlers gespeichert?
- [ ] Sind Ereignis- und Checkpoint-Schemata versioniert?
- [ ] Wurden externe Ein-/Ausgaben während des Replays fixiert oder aufgezeichnet?
- [ ] Ist der Determinismusvertrag für parallele Reduktion ausdrücklich festgelegt?
- [ ] Ist verhindert, dass Golden-Aktualisierungen ohne Prüfung automatisch ausgeführt werden?

## 14. Fallstricke und Einschränkungen

### Eine falsche Eigenschaft lässt korrekten Code scheitern

Monotonie, Symmetrie und Positivität können abhängig von Modell, Randbedingungen oder numerischem Schema verletzt sein. Eigenschaften sind aus Spezifikation und Gleichungen herzuleiten, nicht aus Intuition.

### Exaktes Replay ist nicht auf jeder Plattform möglich

Unterschiedliche Compiler, Befehlssätze, transzendente Funktionen und GPU-Scheduling können bitweise Ergebnisse verändern. Unterstützte Reproduzierbarkeitsstufen zu definieren, ist realistischer.

- Stufe A: bitweise Gleichheit auf identischem Binary und identischer Hardware
- Stufe B: numerische Toleranz auf derselben Architektur
- Stufe C: plattformübergreifende Äquivalenz von Zielgrößen und Invarianten

### Vollständige Zustandsprotokollierung erhöht Kosten und Informationspreisgabe

Ereignisprotokolle, periodische Checkpoints und Zustands-Digests werden mit Aufbewahrungs- und Schwärzungsrichtlinien kombiniert. Auf Schemaebene ist zu verhindern, dass Geheimnisse oder personenbezogene Daten in Nutzlasten gelangen.

### Der deterministische Modus kann vom tatsächlichen Produktionspfad abweichen

Ein ausschließlich für Tests verwendeter Single-Thread-Modus kann bestehen, während der parallele Produktionspfad ungeprüft bleibt. Der deterministische Referenzmodus und der tatsächliche Ausführungsmodus werden mit differenziellen Tests verglichen.

## Fazit

Starke Simulationstests merken sich keine einzelnen Ausgabewerte. Sie kodieren, **was niemals brechen darf**, **welche Beziehungen bei geänderten Eingaben gelten müssen** und **wie ein Fehler aus demselben Zustand neu gestartet wird**.

Invarianten machen Physik und Domänenwissen zu ausführbaren Spezifikationen, eigenschaftsbasiertes Testen entdeckt von Menschen übersehene Eingaben, und Replay verwandelt einen einmaligen Zufallsfehler in einen dauerhaften Regressionswert.
