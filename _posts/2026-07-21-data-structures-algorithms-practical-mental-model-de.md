---
title: "Ein praxisnahes Denkmodell für Datenstrukturen und Algorithmen: Begründung vor Komplexität"
date: 2026-07-21 10:10:00 +0900
categories: [Computer Science, Algorithms]
tags: [data-structures, algorithms, big-o, amortized-analysis, graph-algorithms, invariants, benchmarking]
description: "Wie Big-O und amortisierte Analyse als reale Kostenmodelle interpretiert und Arrays, Hashes, Heaps, Bäume sowie Graphalgorithmen anhand von Anforderungen, Korrektheit und Messungen ausgewählt werden."
math: true
lang: de-DE
hidden: true
translation_key: data-structures-algorithms-practical-mental-model
---

{% include language-switcher.html %}

Wer Datenstrukturen und Algorithmen als Prüfungstabelle auswendig lernt, behält nur Sätze wie „ein Hash hat \(O(1)\), ein Baum dagegen \(O(\log n)\)“. In einem echten Entwurf sollten zuerst folgende Fragen gestellt werden.

- Passen die Daten in den Arbeitsspeicher?
- Welcher Vorgang tritt am häufigsten auf: Nachschlagen, Einfügen, Minimum entnehmen oder Bereichsabfrage?
- Müssen Reihenfolge und Duplikate erhalten bleiben?
- Ist die Worst-Case-Latenz oder der durchschnittliche Durchsatz wichtiger?
- Wie sehen Datenverteilung und Wahrscheinlichkeit adversarialer Eingaben aus?
- Welche Kosten verursachen Cache-Lokalität, Allokation und Nebenläufigkeit?

Die Wahl eines Algorithmus ist kein Ratespiel mit Namen. Sie ist **die Übersetzung von Anforderungen in ein Kostenmodell und Korrektheitsinvarianten**.

## 1. Vor der Analyse die Größenvariablen definieren

Big-O ist bedeutungslos, wenn nicht bekannt ist, wofür \(n\) im Komplexitätsausdruck steht.

- Anzahl der Arrayelemente \(n\)
- Anzahl der Knoten \(V\) und Kanten \(E\) eines Graphen
- Länge einer Zeichenkette \(L\)
- Anzahl der Abfragen \(Q\)
- Zustandsdimension \(d\)
- Anzahl der Bits \(b\) eines Ganzzahlwerts

Einen Graphalgorithmus pauschal als \(O(n^2)\) zu beschreiben verwischt etwa den Unterschied zwischen dünn und dicht besetzten Graphen. BFS auf Basis einer Adjazenzliste hat

$$
\Theta(V+E)
$$

während das vollständige Scannen einer Adjazenzmatrix

$$
\Theta(V^2)
$$

benötigt. Nicht nur der Name des Algorithmus, sondern auch die Repräsentation verändert die Komplexität.

## 2. Big-O, Big-Theta und Big-Omega

### Obere Schranke: \(O(g(n))\)

Existiert eine Konstante \(c\), sodass für hinreichend große \(n\)

$$
0\le f(n)\le c\,g(n)
$$

gilt, dann ist \(f(n)=O(g(n))\). Da dies eine obere Schranke ist, kann auch eine Funktion aus \(\Theta(n)\) als \(O(n^2)\) beschrieben werden. Wann immer möglich, vermittelt die enge Schranke \(\Theta\) mehr Information.

### Asymptotisch gleiche Ordnung: \(\Theta(g(n))\)

Wenn

$$
c_1g(n)\le f(n)\le c_2g(n)
$$

gilt, dann ist \(f(n)=\Theta(g(n))\).

### Untere Schranke: \(\Omega(g(n))\)

Gilt für hinreichend große \(n\), dass \(f(n)\ge c\,g(n)\), handelt es sich um eine untere Schranke.

### Worst Case, Average Case und Erwartungswert kennzeichnen

„Ein Hash-Lookup hat \(O(1)\)“ ist im Allgemeinen eine erwartete oder amortisierte Aussage unter der Annahme eines geeigneten Hashings und Lastfaktors. Bei konzentrierten Kollisionen sieht der Worst Case anders aus. Unterscheiden Sie:

- Worst Case pro Vorgang
- Erwartete Kosten aufgrund von Randomisierung
- Durchschnittlicher Fall unter einer festgelegten Eingabeverteilung
- Amortisierte Kosten über eine Folge von Vorgängen

Durchschnittlich und amortisiert bedeuten nicht dasselbe.

## 3. Amortisierte Analyse: Seltene teure Vorgänge auf die gesamte Folge verteilen

Wenn ein dynamisches Array seine Kapazität erreicht, kann das Erstellen eines größeren Puffers samt Kopieren aller Elemente einen einzelnen Append-Vorgang \(\Theta(n)\) kosten lassen. Wächst die Kapazität jedoch um einen konstanten Faktor, wird die Gesamtzahl der Kopiervorgänge bei \(m\) Appends durch eine geometrische Reihe beschränkt.

$$
1+2+4+\cdots < 2m.
$$

Damit betragen die Gesamtkosten von \(m\) Appends \(\Theta(m)\) und die amortisierten Kosten je Append \(\Theta(1)\).

Amortisierte Analyse ist kein empirischer Durchschnitt mit der Aussage „meistens war es schnell“. Sie beweist, dass **die Gesamtkosten für keine Eingabefolge die Schranke überschreiten**.

Typische Beweismethoden sind:

- Aggregatmethode: Kosten der gesamten Folge direkt summieren
- Buchhaltungsmethode: Günstigen Vorgängen vorab ein Guthaben anrechnen
- Potentialmethode: Änderungen des Potentials der Datenstruktur in die Kosten einbeziehen

In einem System mit Latenzfrist kann amortisiertes \(O(1)\) unzureichend sein. Klären Sie, ob eine einzelne \(O(n)\)-Pause zum Vergrößern akzeptabel ist und ob inkrementelles Rehashing oder eine Kapazitätsreservierung benötigt wird.

## 4. Komplexität ist ein mehrdimensionaler Kostenbegriff

Eine Auswahl allein anhand der Zeitkomplexität übersieht:

- Zusätzlichen Speicher
- Anzahl der Allokationen
- Cache Misses und Pointer Chasing
- Sprungvorhersage
- Serialisierungsgröße
- Parallele Ressourcenkonkurrenz
- Vorverarbeitungszeit
- Verhältnis von Aktualisierungen zu Abfragen

Selbst bei gleichem \(O(n)\) kann das Scannen eines zusammenhängenden Arrays viel schneller sein als das Durchlaufen einer verketteten Struktur. Umgekehrt kann eine verkettete Liste beim Entfernen vorteilhaft sein, wenn ein Zeiger auf den mittleren Knoten bereits vorliegt. Die Kosten für das Auffinden dieses Knotens dürfen nicht unterschlagen werden.

## 5. Auswahlkarte für Datenstrukturen

### Array / dynamisches Array

**Stärken**

- Indexzugriff in \(\Theta(1)\)
- Zusammenhängender Speicher und gute Cache-Lokalität
- Amortisiertes \(\Theta(1)\) beim Anhängen am Ende
- Geeignet für Sortierung, binäre Suche und vektorisierte Verarbeitung

**Schwächen**

- Einfügen oder Löschen in der Mitte ist wegen des Verschiebens von Elementen \(\Theta(n)\)
- Lastspitzen beim Vergrößern und ungenutzte Kapazität
- Stabile Zeiger können ungültig werden

Dies ist ein sehr starker Standard. Prüfen Sie, ob die „Liste“ einer Sprache tatsächlich ein dynamisches Array oder eine verkettete Liste ist.

### Verkettete Liste

**Stärken**

- Einfügen und Löschen in \(\Theta(1)\), wenn die Knotenposition bereits bekannt ist
- Strukturen, die Splicing und stabile Knotenreferenzen benötigen

**Schwächen**

- Indexzugriff und Suche in \(\Theta(n)\)
- Allokations- und Zeiger-Overhead je Knoten
- Schlechte Cache-Lokalität

Wählen Sie sie nicht nur, weil „viele Einfügungen“ stattfinden. Kostet das Auffinden der Einfügeposition \(\Theta(n)\), kann der Gesamtvorteil verschwinden.

### Hashtabelle

**Stärken**

- Erwartetes \(\Theta(1)\) für schlüsselbasiertes Nachschlagen, Einfügen und Löschen
- Mitgliedschaftsprüfung, Häufigkeitszählung und Deduplizierung

**Schwächen**

- Ungeeignet für Schlüsselreihenfolge und Bereichsabfragen
- Abhängig von Hashqualität und Lastfaktor
- Kosten des Rehashings
- Risiken durch adversariale Kollisionen und veränderliche Schlüssel

Gleichheit und Hashing müssen konsistent sein.

$$
a=b\quad\Longrightarrow\quad hash(a)=hash(b).
$$

Wenn ein Feld, das an der Gleichheitsprüfung beteiligt ist, nach dem Verwenden des Objekts als Schlüssel geändert wird, kann der Eintrag unauffindbar werden.

### Balancierter Suchbaum

**Stärken**

- Worst-Case-\(\Theta(\log n)\) für Nachschlagen, Einfügen und Löschen
- Sortierte Traversierung
- Vorgänger und Nachfolger
- Bereichsabfragen

**Schwächen**

- Größere Konstanten und mehr Zeiger-Overhead als eine Hashtabelle
- Komplexe Implementierung der Balancierung

Er eignet sich, wenn eine geordnete Map oder Menge, Intervallabfragen oder vorhersehbares Worst-Case-Verhalten benötigt werden.

### Heap / Prioritätswarteschlange

Für einen binären Heap gilt:

- Minimum oder Maximum ansehen: \(\Theta(1)\)
- Einfügen: \(\Theta(\log n)\)
- Minimum oder Maximum entnehmen: \(\Theta(\log n)\)
- Suche nach einem beliebigen Schlüssel unter allen ungeordneten Elementen: \(\Theta(n)\)
- Heapify für alle Elemente: \(\Theta(n)\)

Ein Heap ist kein „sortierter Container“. Er garantiert nur die Priorität der Wurzel. Verwenden Sie ihn, wenn wiederholt das nächste Element mit der höchsten Priorität entnommen wird, etwa bei Top-\(k\), Schedulern und der Dijkstra-Frontier.

### Deque

Verwenden Sie eine Deque, wenn eine Queue Push und Pop an beiden Enden in \(\Theta(1)\) benötigt. Vermeiden Sie bei BFS das wiederholte Löschen am Anfang eines Arrays, das Verschiebungen in \(\Theta(n)\) verursacht.

### Disjoint-Set Union

Wenn Mengen wiederholt vereinigt und Verbindungen abgefragt werden, liefert Pfadkompression zusammen mit Union nach Rang oder Größe amortisierte Kosten pro Vorgang, die praktisch nahezu konstant sind:

$$
O(\alpha(n))
$$

Diese Struktur ist ungeeignet, wenn dynamisches Löschen oder der Pfad selbst benötigt wird.

## 6. Vom Ziel rückwärts zur Datenstruktur arbeiten

| Kernanforderung | Erster Kandidat | Zu prüfende Bedingungen |
|---|---|---|
| Indexzugriff und sequenzielles Scannen | dynamisches Array | Häufigkeit mittiger Änderungen, Kapazität |
| Schlüsselmitgliedschaft | Hash-Set/Map | Notwendigkeit von Reihenfolge oder Worst-Case-Garantien |
| Sortierte Schlüssel und Bereichsabfragen | balancierter Baum | Verhältnis von Aktualisierungen zu Abfragen |
| Wiederholte Entnahme des Minimums | Heap | Unterstützung für beliebiges Löschen/Decrease-Key |
| FIFO | Deque | Begrenzte Queue, Nebenläufigkeit |
| LIFO | Stack / dynamisches Array | Maximale Tiefe |
| Verbindungen vereinigen/abfragen | Disjoint Set | Ob Kanten niemals gelöscht werden |
| Traversierung eines dünn besetzten Graphen | Adjazenzliste | Mehrfachkanten, Richtung |
| Dichter Graph oder schneller Kantentest | Adjazenzmatrix/Bitset | Ob \(V^2\) Speicher akzeptabel ist |

Ein Dienst kann seine Source of Truth von den Auslieferungsindizes trennen. Datensätze lassen sich beispielsweise in einem Array speichern, während ein Hashindex für ID-Suchen und ein Heap für Prioritäten gepflegt werden. Dann wird **die Synchronisationsinvariante zwischen den Repräsentationen** zu einem neuen Kostenfaktor.

## 7. Die Graphrepräsentation bestimmt den Algorithmus

### Adjazenzliste

Der Speicherbedarf beträgt \(\Theta(V+E)\), und die Iteration über die Nachbarn eines Knotens ist proportional zu seinem Grad. Dies ist der Standard für dünn besetzte Graphen.

### Adjazenzmatrix

Der Speicherbedarf beträgt \(\Theta(V^2)\), doch die Prüfung, ob eine Kante existiert, benötigt \(\Theta(1)\). Sie kann sich für dichte Graphen, kleine Graphen und bitparallele Vorgänge eignen.

### Kantenliste

Sie ist einfach für Algorithmen, die jede Kante einmal scannen oder sortieren. Das Nachschlagen der Nachbarn eines beliebigen Knotens ist ohne separaten Index langsam.

Entscheiden Sie bei der Wahl der Repräsentation auch, ob der Graph gerichtet oder ungerichtet, gewichtet oder ungewichtet ist, Selbstschleifen und parallele Kanten zulässt, veränderlich ist und wie dicht die Knoten-IDs liegen.

## 8. Vorbedingungen für BFS, DFS und Dijkstra

### BFS

BFS findet in einem ungewichteten Graphen oder einem Graphen mit identischen Kantengewichten die kürzeste Distanz ab einer Quelle gemessen in Kantenanzahl.

~~~python
from collections import deque

def bfs(graph, source):
    distance = {source: 0}
    parent = {source: None}
    queue = deque([source])

    while queue:
        u = queue.popleft()
        for v in graph[u]:
            if v in distance:
                continue
            distance[v] = distance[u] + 1
            parent[v] = u
            queue.append(v)

    return distance, parent
~~~

Markieren Sie einen Knoten beim **Einreihen** als besucht und nicht erst beim Entfernen aus der Queue, damit derselbe Knoten nicht wiederholt eingereiht wird.

Dieses Beispiel nimmt an, dass jeder als Nachbar auftretende Zielknoten auch ein Schlüssel in `graph` ist. Eine echte API sollte diese Repräsentationsinvariante validieren oder eine leere Adjazenz etwa mit `graph.get(u, ())` explizit behandeln.

### DFS

DFS ist ein Baustein für Erreichbarkeit, Zusammenhangskomponenten, Zyklenerkennung und topologische Sortierung. Die Aussage „DFS verwenden“ allein legt jedoch die Zyklenerkennung nicht fest.

- Ungerichteter Graph: Ein besuchter Nachbar, der nicht die Elternkante ist, signalisiert einen Zyklus
- Gerichteter Graph: Eine Rückwärtskante in den aktuellen Rekursionsstack oder Farbzustand ist erforderlich
- Topologische Reihenfolge: Nur für einen gerichteten azyklischen Graphen gültig

Die Traversierungsreihenfolge in einem DFS-Baum kann mit der Iterationsreihenfolge der Adjazenz variieren. Fixieren Sie die Nachbarreihenfolge, wenn deterministische Ausgabe erforderlich ist.

### Dijkstra

Dijkstra findet kürzeste Wege von einer Quelle, wenn **jedes Kantengewicht nicht negativ** ist.

~~~python
from heapq import heappop, heappush
from math import inf, isfinite

def dijkstra(graph, source):
    distance = {v: inf for v in graph}
    distance[source] = 0.0
    heap = [(0.0, source)]

    while heap:
        best, u = heappop(heap)
        if best != distance[u]:
            continue

        for v, weight in graph[u]:
            if not isfinite(weight) or weight < 0:
                raise ValueError("Dijkstra requires finite nonnegative weights")
            candidate = best + weight
            if candidate < distance[v]:
                distance[v] = candidate
                heappush(heap, (candidate, v))

    return distance
~~~

Da veraltete Einträge desselben Knotens in der Prioritätswarteschlange verbleiben können, ist eine Prüfung auf veraltete Einträge erforderlich. Eine Implementierung mit einem Heap, der direktes Decrease-Key unterstützt, unterscheidet sich davon.

Mit Adjazenzliste und binärem Heap beträgt die übliche Zeitkomplexität \(O((V+E)\log V)\), für einen zusammenhängenden Graphen oft als \(O(E\log V)\) geschrieben. Bei der obigen Implementierung, die doppelte Einträge zulässt, sind außerdem Heapspeicher und konstante Kosten zu berücksichtigen.

### Auswahl nach Gewichtsstruktur

| Kantengewicht | Kandidat für den Algorithmus |
|---|---|
| Alle gleich | BFS |
| 0 oder 1 | 0–1 BFS |
| Alle nicht negativ | Dijkstra |
| Negative Kanten möglich | Bellman–Ford-Familie |
| DAG | Relaxation in topologischer Reihenfolge |
| Alle Paare, dichter/kleiner Graph | Floyd–Warshall und andere erwägen |

Wenn ein negativer Zyklus erreichbar ist, kann ein endlicher kürzester Weg selbst undefiniert sein. Das ist ein Problem der Problemdefinition und kein Fehler des Algorithmus.

## 9. Rekursion und Iteration

Rekursion drückt Baum- und Divide-and-Conquer-Definitionen strukturell nahe am Code aus. Sie verursacht aber auch folgende Kosten.

- Begrenzung der Call-Stack-Tiefe
- Frame-Allokation und Funktionsaufruf-Overhead
- Stack Overflow bei tiefen oder stark einseitigen Bäumen
- Impliziter Zustand und Fehlerbehebung

Iteration verwaltet den Traversierungszustand direkt mit einem expliziten Stack oder einer Queue.

~~~python
def iterative_dfs(graph, source):
    visited = set()
    stack = [source]

    while stack:
        u = stack.pop()
        if u in visited:
            continue
        visited.add(u)
        for v in reversed(graph[u]):
            if v not in visited:
                stack.append(v)

    return visited
~~~

Dieses Beispiel nimmt an, dass die Adjazenz eine deterministische Sequenz ist, die `reversed` unterstützt. Um die Besuchsreihenfolge eines rekursiven DFS zu reproduzieren, kann das LIFO-Verhalten des Stacks verlangen, dass Nachbarn in umgekehrter Reihenfolge eingetragen werden. Selbst wenn die Besuchsreihenfolge für die Korrektheit unwichtig ist, sollten Tests nicht versehentlich davon abhängen.

Zu den Auswahlkriterien gehören:

- Kleine und klar begrenzte Tiefe: Rekursion kann lesbarer sein
- Adversariale Eingabe oder Tiefe \(O(n)\): Iteration bevorzugen
- Traversierung anhalten, fortsetzen oder serialisieren: Expliziter Zustand ist vorteilhaft
- Postorder-Verarbeitung: Eintritts-/Austrittszustand im Stack Frame speichern

Prüfen Sie, ob Sprache und Laufzeitumgebung Tail-Call-Optimierung garantieren.

## 10. Beweise mit Korrektheitsinvarianten an den Code binden

Um zu zeigen, dass ein Algorithmus für jede gültige Eingabe korrekt ist, statt lediglich „für das Beispiel zu funktionieren“, verwenden Sie eine Schleifeninvariante.

### Drei Schritte

1. **Initialisierung**: Die Invariante gilt vor Beginn der Schleife.
2. **Erhaltung**: Sie bleibt nach einer Iteration gültig.
3. **Terminierung**: Am Ende der Schleife liefert die Invariante die gewünschte Schlussfolgerung.

### Beispiel einer Invariante für binäre Suche

Bei Verwendung des halboffenen Intervalls \([lo,hi)\):

- Falls eine Antwort existiert, liegt sie stets in \([lo,hi)\).
- \([0,lo)\) erfüllt die Bedingung nicht.
- \([hi,n)\) erfüllt die Bedingung.

Behalten Sie bei Aktualisierungen und Rückgabe dieselbe Grenzkonvention bei, um Off-by-one-Fehler zu vermeiden.

### BFS-Invariante

Die Distanzen der aus der Queue verarbeiteten Knoten sind nicht fallend, und der zuerst gefundene Pfad besitzt die minimale Kantenzahl. Dies hängt von der Vorbedingung ab, dass alle Kantengewichte gleich sind.

### Dijkstra-Invariante

Die Distanz eines mit dem gültigen Minimum aus dem Heap finalisierten Knotens ist die kürzeste Distanz. Nicht negative Kanten sind für den Beweis erforderlich, dass kein unbesuchter Pfad diesen Wert später verkleinern kann.

### Heap-Invariante

Jeder Knotenschlüssel in einem Min-Heap ist höchstens so groß wie die Schlüssel seiner Kinder. Eine vollständige Sortierung ist nicht erforderlich. Testen Sie, ob die lokale Reparatur nach Push oder Pop diese Invariante wiederherstellt.

## 11. Randfälle sind Entwurfseingaben, keine späteren Ausnahmen

### Collections

- Leer
- Ein Element
- Alle gleich
- Bereits sortiert / umgekehrt sortiert
- Viele Duplikate
- Unmittelbar vor und nach einer Kapazitätsgrenze
- Fehlender Schlüssel und wiederholtes Löschen

### Numerische Werte

- Null und negative Null
- Kleinster und größter darstellbarer Wert
- Ganzzahlüberlauf
- Ob NaN und Unendlich erlaubt sind
- Gleitkommagleichheit und Toleranz
- Stark unterschiedliche Größenordnungen

### Graph

- Isolierter Knoten
- Nicht zusammenhängende Komponente
- Selbstschleife
- Parallele Kante
- Verwechslung von gerichtet und ungerichtet
- Zyklus und erreichbarer negativer Zyklus
- Quelle fehlt im Graphen
- Mehrere kürzeste Wege

### Ressourcen

- Eingabe passt nicht in den Arbeitsspeicher
- Maximale Rekursionstiefe
- Abbruch und Timeout
- Partielle Lese- und Schreibvorgänge
- Gleichzeitige Mutation

Belassen Sie Randfälle nicht nur in einer Testliste. Legen Sie im API-Vertrag fest, ob jeder davon abgelehnt, normalisiert oder unterstützt wird.

## 12. Profiling: Die Kosten finden, statt zu raten

Selbst ein Algorithmus mit guter Komplexität ist womöglich nicht der eigentliche Engpass. Gehen Sie vor einer Optimierung in dieser Reihenfolge vor.

1. End-to-End-Ziele für Latenz oder Durchsatz definieren.
2. Unter einer produktionsähnlichen Last profilieren.
3. CPU, Allokation, I/O-Wartezeit und Lock Contention trennen.
4. Auf dem Hot Path Aufrufhäufigkeit und Kosten pro Aufruf untersuchen.
5. Nach Änderung von Algorithmus oder Repräsentation unter denselben Bedingungen erneut messen.

Die Beseitigung einer \(O(n^2)\)-Schleife, unnötiger Serialisierung, wiederholter DB-Abfragen oder eines Allokationsmusters bewirkt oft viel mehr als Mikrooptimierung.

## 13. Bedingungen für vertrauenswürdige Benchmarks

### Workload

- An mehreren Punkten des realen Größenbereichs messen
- Neben Zufallseingaben auch sortierte, duplikatreiche, schiefe und adversariale Verteilungen einbeziehen
- Lese-/Schreib- und Cache-Hit-Verhältnisse abbilden
- Warme und kalte Caches unterscheiden

### Messung

- Aufwärm- sowie JIT/GC-Effekte kontrollieren
- Setup vom gemessenen Bereich trennen
- Median und Tail-Perzentile über mehrere Wiederholungen messen
- CPU-Frequenzskalierung und Hintergrundlast protokollieren
- Ergebnisse verbrauchen, um Dead-Code-Eliminierung zu verhindern
- Auch Spitzenwert des Speichers und Allokationen messen

### Interpretation

Ein Log-Log-Diagramm oder die Anzahl der Vorgänge nach Eingabegröße kann den Kreuzungspunkt zeigen. Ein einfacher Algorithmus kann für kleine \(n\) schneller sein, während ein asymptotisch besserer ihn bei großen \(n\) überholt.

Ein Benchmark beweist keine universelle Wahrheit. Er liefert Evidenz für die gemessene Hardware, Laufzeit und Eingabeverteilung.

## 14. Praktischer Auswahl-Workflow

1. **Vorgänge auflisten**: Häufigkeiten von Nachschlagen, Einfügen, Löschen, Minimum, Bereich und Traversierung abschätzen.
2. **Vertrag definieren**: Reihenfolge, Duplikate, Veränderlichkeit, Nebenläufigkeit und Latenzgrenzen festlegen.
3. **Größen und Verteilungen definieren**: \(n,V,E,Q\), Sparsity, Schiefe und Möglichkeit adversarialer Eingaben erfassen.
4. **Kandidaten vergleichen**: Durchschnittliche, Worst-Case- und amortisierte Zeit sowie Speicher tabellarisch gegenüberstellen.
5. **Korrektheitsinvarianten formulieren**: Bedingungen festhalten, die Struktur und Algorithmus aufrechterhalten müssen.
6. **Die einfachste korrekte Implementierung** erstellen.
7. Invarianten mit **Randfall- und Property-Tests** verifizieren.
8. Mit **Profiling** den tatsächlichen Engpass finden.
9. Alternativen mit einem **repräsentativen Benchmark** vergleichen.
10. **Begründung dokumentieren**: Workload-Annahmen und Schwellen für Neubewertungen bewahren.

## 15. Checkliste zur Verifikation

- [ ] Sind die Größenvariablen in Komplexitätsausdrücken definiert?
- [ ] Werden Worst Case, erwartete, durchschnittliche und amortisierte Kosten unterschieden?
- [ ] Werden neben Zeit auch Speicher, Allokation und Lokalheit bewertet?
- [ ] Enthalten die Einfügekosten einer verketteten Liste das Auffinden der Position?
- [ ] Wurden Reihenfolge, Kollisionen und Bedingungen veränderlicher Schlüssel bei Hashes geprüft?
- [ ] Wird ein Heap nicht als vollständig sortierte Struktur missverstanden?
- [ ] Passt die Graphrepräsentation zu Sparsity und Abfrageanforderungen?
- [ ] Wurden die Vorbedingungen für Kantengewicht und Richtung von BFS, DFS und Dijkstra geprüft?
- [ ] Ist die Rekursionstiefe nicht durch die Eingabe unbegrenzt?
- [ ] Lassen sich Initialisierung, Erhaltung und Terminierung der Schleifeninvariante erklären?
- [ ] Werden leere, doppelte, überlaufende und nicht zusammenhängende Fälle getestet?
- [ ] Wurde der Engpass vor der Optimierung durch Profiling bestätigt?
- [ ] Sind Workload und Umgebung des Benchmarks dokumentiert?
- [ ] Wurden neben Durchschnittswerten auch Tail-Latenz und Spitzenspeicher untersucht?

## 16. Häufige Fallstricke und Grenzen

### Eine Struktur mit kleinerem Big-O ist immer schneller

Konstanten, Cache-Lokalität, Allokation und der tatsächliche Bereich von \(n\) bestimmen den Kreuzungspunkt. Sowohl asymptotische Analyse als auch Benchmarks sind nötig.

### Komplexität allein aus dem Namen einer Bibliothek ableiten

Container mit demselben Namen können in verschiedenen Sprachen anders implementiert sein. Prüfen Sie Garantien der Vorgänge und Invalidierungsregeln in der offiziellen Dokumentation.

### Annehmen, sortierte Eingaben seien einfache Eingaben

Je nach Algorithmus können sortierte oder umgekehrt sortierte Eingaben den Worst Case darstellen. Untersuchen Sie die Annahmen hinter Pivot-Elementen, Hashes und Baumbalancierung.

### Dijkstra negative Kanten geben und nur das Ergebnis prüfen

In einem kleinen Beispiel kann es zufällig funktionieren, doch die Vorbedingung des Korrektheitsbeweises ist verletzt. Validieren Sie Eingaben an der Grenze des Algorithmus.

### Annehmen, die Umwandlung von Rekursion in eine Schleife erhalte immer die Reihenfolge

Der Traversierungsbaum ändert sich mit der Reihenfolge, in der Nachbarn auf den expliziten Stack gelegt werden, und mit dem Zeitpunkt ihrer Markierung als besucht.

### Eine Auswahl aufgrund eines einzigen Benchmarks dauerhaft festschreiben

Wenn sich Datengröße, Lese-/Schreibverhältnis oder Laufzeitversion ändern, kann sich auch die Begründung ändern. Dokumentieren Sie Kriterien für eine Neubewertung.

## Fazit

Das praktische Denkmodell für Datenstrukturen und Algorithmen lässt sich auf folgende Aussage verdichten.

> Schreiben Sie zuerst die erforderlichen Vorgänge und Garantien auf, wählen Sie die einfachste Struktur, die sie aufrechterhält, prüfen Sie die Skalierbarkeit mit asymptotischer Analyse und messen Sie unter der realen Workload.

Big-O ist eine Karte zum Filtern von Kandidaten, eine Invariante ist ein Vertrag zur Bewahrung der Korrektheit, und Profiling sowie Benchmarking sind das Instrumentenbrett zur Kontrolle realer Kosten. Mit allen dreien wird die Wahl einer Datenstruktur zur technischen Entscheidung statt zu einer Auswendiglernübung.
