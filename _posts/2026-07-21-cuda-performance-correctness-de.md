---
title: "CUDA-Leistung und -Korrektheit: Praktische Prinzipien für APOD, Speicherhierarchie und Profiling"
date: 2026-07-21 12:29:00 +0900
categories: [GPU, Performance]
tags: [cuda, gpu-programming, profiling, memory-coalescing, numerical-correctness]
description: CUDA-Kernel mit einer korrekten CPU-Referenz, dem APOD-Zyklus, Analysen des Speicherverkehrs, Belegung und Profiler-Evidenz gezielt statt blind optimieren.
lang: de-DE
hidden: true
translation_key: cuda-performance-correctness
math: true
mermaid: true
---

{% include language-switcher.html %}

CUDA-Optimierung besteht nicht in einem Trick wie der Erhöhung der Threadzahl oder dem Hinzufügen von Shared Memory.
Sie ist ein iterativer Prozess: lohnende Engpässe der gesamten Anwendung finden und Datenbewegung sowie Ausführungseffizienz verbessern, ohne die Korrektheit zu verlieren.

## 1. Das Problem: Ein schneller Kernel garantiert keine schnelle Anwendung

GPU-Code umfasst folgende Kosten.

- Vorverarbeitung auf dem Host
- Übertragung vom Host zum Gerät
- Kernelstart
- Berechnung auf dem Gerät
- Gerätesynchronisierung
- Übertragung vom Gerät zum Host
- Nachverarbeitung

Selbst eine dutzendfache Beschleunigung eines Kernels hat nur begrenzte Wirkung, wenn dieser lediglich einen kleinen Anteil der Gesamtzeit ausmacht.
Das Amdahlsche Gesetz lautet:

$$
S=\frac{1}{(1-p)+p/s}
$$

- (p): Anteil des zu verbessernden Bereichs
- (s): Beschleunigung dieses Anteils

Zunächst ist (p) mit einem Profil zu messen.

## 2. Denkmodell: Der APOD-Zyklus

```mermaid
flowchart LR
    A[Bewerten] --> B[Parallelisieren]
    B --> C[Optimieren]
    C --> D[Ausrollen]
    D --> E[Reale Lasten beobachten]
    E --> A
```

NVIDIAs APOD-Ansatz betont folgenden Zyklus.

- Bewerten: Engpässe und Ziele messen.
- Parallelisieren: sicher parallelisierbare Teile auswählen.
- Optimieren: Speicher, Ausführung und Instruktionen verbessern.
- Ausrollen: Regressionen und Portabilität in der realen Umgebung validieren.

Für jede Optimierung sind Korrektheitstests und Profiler-Evidenz aufzubewahren.

## 3. CPU-Referenz und numerischer Vertrag

Vor der Implementierung auf der GPU wird für kleine Eingaben eine Referenz gepflegt.

```cpp
for (int i = 0; i < n; ++i) {
    reference[i] = transform(input[i]);
}
```

Zu validierende Punkte:

- Absolute und relative Toleranz
- NaN und Inf
- Länge null und Randgrößen
- Größen, die kein Vielfaches der Blockgröße sind
- Extrem große oder kleine Werte
- Determinismusanforderungen
- Unterschiede der Reduktionsreihenfolge

Gleitkommaaddition ist nicht exakt assoziativ.
Eine parallele Reduktion muss daher nicht bitweise mit einer sequenziellen CPU-Summe übereinstimmen.

Beispiel für ein Fehlerkriterium:

$$
|y_{gpu}-y_{ref}| \le a_{tol}+r_{tol}|y_{ref}|
$$

Eine Toleranz ist anhand von Datentyp, Konditionszahl und Anzahl akkumulierter Operationen zu begründen, statt beliebig groß gewählt zu werden.

## 4. Abbildung von Thread, Block und Grid

Grundlegende Abbildung für ein eindimensionales Array:

```cpp
__global__ void scale(float* y, const float* x, float a, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        y[i] = a * x[i];
    }
}
```

Entwurfsfragen:

- Welche Ausgabe gehört zu jedem Thread?
- Überschneiden sich Schreibzugriffe verschiedener Threads?
- Ist eine Synchronisierung zwischen Blöcken erforderlich?
- Überschreitet die Eingabegröße die Grid-Grenze?
- Ist eine Schleife mit Schrittweite nötig?

Grid-Stride-Schleife:

```cpp
for (int i = blockIdx.x * blockDim.x + threadIdx.x;
     i < n;
     i += blockDim.x * gridDim.x) {
    y[i] = a * x[i];
}
```

Sie verarbeitet wechselnde Größen und erleichtert Experimente mit Startkonfigurationen.

## 5. Speicherhierarchie und zusammenhängende Zugriffe

Die Leistung wird häufig stärker von bewegten Bytes als von der Anzahl der Operationen begrenzt.

- Register: Thread-lokal und schnell, aber in begrenzter Zahl verfügbar
- Shared Memory: Block-lokal; erfordert explizite Verwaltung und Synchronisierung
- L1/L2-Cache: von der Hardware verwaltet
- Global Memory: groß, jedoch durch Latenz und Bandbreite beschränkt
- Constant Memory: bei bestimmten Broadcast-Mustern vorteilhaft

Das Array-Layout ist so zu gestalten, dass benachbarte Threads eines Warps auf benachbarte Adressen zugreifen.

Beispiel für eine ungünstige Schrittweite:

```cpp
float value = matrix[threadIdx.x * leading_dimension + column];
```

Es ist zu prüfen, ob sich der Index so umordnen lässt, dass Threads zusammenhängende Spalten lesen.

Ob Zugriffe zusammengefasst werden, darf nicht geraten werden; Speichertransaktions- und Durchsatzmetriken müssen es bestätigen.

## 6. Arithmetische Intensität und Roofline-Denken

Arithmetische Intensität:

$$
I=\frac{\text{Operationen}}{\text{übertragene Bytes}}
$$

Eine niedrige Intensität deutet auf Speicherbegrenzung hin, eine hohe auf Rechenbegrenzung.
Eine einfache obere Roofline-Grenze lautet:

$$
P\le \min(P_{peak}, I\times B_{memory})
$$

Dies ist ein Denkmodell für die Wahl der Optimierungsrichtung, kein exakter Leistungsprädiktor.

- Speicherbegrenzt: Datenwiederverwendung, zusammenhängende Zugriffe und weniger Übertragungen
- Rechenbegrenzt: Instruktionsmix, mathematischer Durchsatz und Eignung für Tensor Cores
- Latenzbegrenzt: Analyse von Parallelität und Abhängigkeiten

## 7. Wann Shared Memory eingesetzt werden sollte

Shared Memory ist vorteilhaft, wenn globale Daten wiederverwendet werden.

Typischer gekachelter Ablauf:

1. Jeder Thread liest einen Teil einer Kachel aus dem Global Memory.
2. Er speichert ihn im Shared Memory.
3. `__syncthreads()` synchronisiert den Abschluss des Ladens.
4. Die Kachel wird für mehrere Operationen wiederverwendet.
5. Danach folgt die nächste Kachel.

Zu beachten:

- Jeder beteiligte Thread muss die Barriere erreichen.
- Bankkonflikte können auftreten.
- Mehr Shared Memory pro Block verringert die Zahl gleichzeitig residenter Blöcke.
- Bei nur einmal gelesenen Daten kann das Kopieren mehr kosten als einsparen.

Globale Ladevorgänge und Kernelzeit sind vor und nach dem Shared-Memory-Einsatz zu vergleichen.

## 8. Belegung als Nebenbedingung statt als Ziel behandeln

Die Belegung ist der Anteil aktiver Warps auf einem SM relativ zum theoretischen Maximum.
Sie ist für das Verbergen von Latenz relevant, doch 100 Prozent sind nicht immer optimal.

Begrenzende Faktoren:

- Threads pro Block
- Registerverbrauch
- Shared-Memory-Verbrauch
- Architekturgrenzen

Ein erzwungen niedriger Registerverbrauch kann Spilling verursachen und den Local-Memory-Verkehr erhöhen.
Eine niedrige Belegung kann dennoch schnell sein, wenn Parallelität auf Instruktionsebene und Cache-Wiederverwendung gut sind.

Als Ausgangspunkt dienen Blockgrößen als Vielfache von 32; mehrere Kandidaten sind zu messen.
Offizielle Occupancy-API und Profiler helfen, die endgültige Entscheidung muss jedoch anhand der End-to-End-Zeit fallen.

## 9. Divergenz, atomare Operationen und Reduktionen

Führen Threads eines Warps verschiedene Zweige aus, können ihre Pfade serialisiert werden.
Komplexe Berechnungen zur Beseitigung eines kurzen Zweigs können jedoch langsamer sein.

Atomare Operationen sichern Korrektheit, doch Konkurrenz um dieselbe Speicherstelle kann zum Engpass werden.

Reduktionshierarchie:

1. Thread-lokales Teilergebnis
2. Reduktion auf Warp-Ebene
3. Reduktion auf Block-Ebene
4. Eine globale atomare Operation nur für Blockergebnisse oder ein zweiter Kernel

Jede eigene Reduktion ist mit verschiedenen Größen und NaN-Richtlinien zu testen.
Wenn ausreichend, sollte zuerst ein Bibliotheksprimitiv verwendet werden.

## 10. Asynchronität und Zeitmessung

Ein Kernelstart kann gegenüber dem Host asynchron sein.
Eine sofortige Messung mit einer allgemeinen Wanduhr erfasst möglicherweise nur die Startzeit.

CUDA-Events sind zu verwenden.

```cpp
cudaEventRecord(start, stream);
kernel<<<grid, block, 0, stream>>>(...);
cudaEventRecord(stop, stream);
cudaEventSynchronize(stop);
cudaEventElapsedTime(&milliseconds, start, stop);
```

Grundsätze der Leistungsmessung:

- Aufwärmen durchführen.
- Taktschwankungen und Störungen durch andere Prozesse erfassen.
- Mehrfach wiederholen und die Verteilung berichten.
- Nur die notwendige Synchronisierung hinzufügen.
- Zeiten mit und ohne Übertragungen unterscheiden.
- Kosten der Eingabeerzeugung und Validierung angeben.

## 11. Profiling-Ablauf

### Zeitleiste auf Systemebene

Mit Nsight Systems werden CPU-Aktivität, Übertragungen, Kernel, Synchronisierung und Leerlaufphasen untersucht.

Fragen:

- Wo ist die GPU untätig?
- Gibt es zu viele kleine Kernelstarts?
- Überlappen Übertragungen und Berechnung?
- Gibt es unnötige Synchronisierung?

### Metriken auf Kernel-Ebene

Nsight Compute liefert eine detaillierte Sicht auf ausgewählte Kernel.

- Erreichte Speicherbandbreite
- Effizienz der Speichertransaktionen
- Ursachen für Warp-Stalls
- Belegung und Register
- Verzweigungseffizienz
- Instruktionsdurchsatz

Das gleichzeitige Sammeln aller Metriken erhöht den Profiling-Aufwand.
Nur die Abschnitte, die eine Hypothese prüfen, sollten ausgewählt werden.

## 12. Praktische Optimierungsreihenfolge

1. Engpass mit einem End-to-End-Profil finden.
2. CPU-Referenz und Kerneltests festschreiben.
3. Unnötige Übertragungen und Synchronisierung entfernen.
4. Speicherzugriffsmuster verbessern.
5. Bei Wiederverwendung Shared Memory oder Fusion erwägen.
6. Start- und Blockkonfigurationen untersuchen.
7. Instruktions- und Präzisionsoptimierungen zuletzt betrachten.
8. Nach jeder Änderung Korrektheits- und Leistungsregressionstests ausführen.

Kernel-Fusion kann globale Speicherzugriffe auf Zwischenergebnisse und Starts reduzieren.
Daneben sind aber Registerdruck, Codekomplexität und geringere Wiederverwendbarkeit zu messen.

## 13. Bewertungscheckliste

- [ ] Gibt es für kleine Eingaben eine unabhängige CPU-Referenz?
- [ ] Ist die Toleranz numerisch begründet?
- [ ] Wurden Speicherfehler mit Compute Sanitizer oder einem gleichwertigen Werkzeug geprüft?
- [ ] Wurden zuerst End-to-End-Engpässe ermittelt?
- [ ] Werden Kernelzeit und Zeit einschließlich Übertragungen unterschieden?
- [ ] Wurden Aufwärmen und Event-Synchronisierung angewendet?
- [ ] Wurde das Zusammenfassen globaler Zugriffe anhand von Metriken bestätigt?
- [ ] Werden Daten im Shared Memory tatsächlich wiederverwendet?
- [ ] Werden Belegung und Spilling gemeinsam untersucht?
- [ ] Wurden nicht teilbare Größen und Grenzen getestet?
- [ ] Wurden Leistung und Korrektheit auf mehreren Architekturen geprüft?
- [ ] Sind Profiler-Evidenz und Commits vor und nach der Optimierung verknüpft?

## 14. Häufige Fehler und Einschränkungen

### Nur die GPU-Auslastung betrachten

Hohe Auslastung zeigt nicht, ob nützliche Berechnung oder ein Speicher-Stall stattfindet.
Anwendungsdurchsatz und Kernelmetriken sind gemeinsam zu untersuchen.

### Annehmen, Shared Memory sei immer schneller

Kopieren ohne Wiederverwendung fügt nur Instruktionen und Barrieren hinzu.
Die Entscheidung folgt aus Profilen vor und nach der Änderung.

### 100 Prozent Belegung erzwingen

Register-Spilling und schlechtere Cache-Wiederverwendung können den Code verlangsamen.
Belegung ist eine Ursache der Leistung, nicht die Zielfunktion.

### Schnelle Mathematik ohne Korrektheitsvalidierung aktivieren

Näherungsoperationen und Kontraktion können Ergebnisse ändern.
Fachliche Toleranzen und Stabilität sind über die gesamte Pipeline zu bewerten.

Die optimale CUDA-Konfiguration ändert sich mit GPU-Architektur und Toolkit.
Eine fest codierte Einstellung ist keine dauerhafte Regel; ein reproduzierbarer Benchmark muss gepflegt werden.

## 15. Offizielle Referenzen

- [CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
- [CUDA C++ Best Practices Guide](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- [Offizielle Dokumentation zu Nsight Systems](https://docs.nvidia.com/nsight-systems/)
- [Offizielle Dokumentation zu Nsight Compute](https://docs.nvidia.com/nsight-compute/)
- [Offizielle Dokumentation zu Compute Sanitizer](https://docs.nvidia.com/compute-sanitizer/)

## 16. Fazit

CUDA-Leistung entsteht aus Speicherverhalten, Ausführung und Anwendungsstruktur.
Der APOD-Zyklus zusammen mit Korrektheitstests verhindert Illusionen aus Mikrobenchmarks und bewahrt nur Verbesserungen, die sich unter realen Lasten reproduzieren lassen.
