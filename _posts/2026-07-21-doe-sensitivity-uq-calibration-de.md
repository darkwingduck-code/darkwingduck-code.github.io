---
title: "Von DOE über UQ bis zur Kalibrierung: eine vollständige Landkarte für die Planung von Simulationsstudien"
date: 2026-07-21 09:30:00 +0900
categories: [Scientific Computing, Research Methods]
tags: [doe, sensitivity-analysis, uncertainty-quantification, calibration, identifiability, surrogate-model]
description: "Versuchsplanung, lokale und globale Sensitivität, Unsicherheitsfortpflanzung und Parameterkalibrierung unterscheiden und anschließend in einem reproduzierbaren Workflow für Simulationsstudien verbinden."
math: true
lang: de-DE
translation_key: doe-sensitivity-uq-calibration
hidden: true
---

{% include language-switcher.html %}

Einige Simulationseingaben zu ändern und Ausgabekurven zu vergleichen, reicht für belastbare Schlussfolgerungen nicht aus. Variableneffekte, Wechselwirkungen, Eingabeunsicherheit, Parameterschätzung und Modellfehler vermischen sich dabei.

Um sie zu trennen, werden zunächst die Rollen von vier Werkzeugen unterschieden.

- **Versuchsplanung (Design of Experiments, DOE)**: entscheidet, welche Eingabekombinationen berechnet oder gemessen werden.
- **Sensitivitätsanalyse (SA)**: fragt, welcher Anteil der Ausgabevariation durch jede Eingabe erklärt wird.
- **Unsicherheitsquantifizierung (UQ)**: fragt, wie sich Unsicherheit in Eingaben und Modellen auf die Ausgabeunsicherheit überträgt.
- **Kalibrierung**: schätzt unbekannte Parameter anhand von Beobachtungen.

Diese Werkzeuge ergänzen einander, sind aber kein Ersatz füreinander. Eine gute DOE quantifiziert Unsicherheit nicht automatisch, und eine gute Kalibrierungsanpassung bedeutet nicht, dass die Validierung abgeschlossen ist.

## 1. Die erste anzulegende Tabelle: Eingaben und Unsicherheit klassifizieren

Nicht jede Eingabe \(x=(x_1,\dots,x_d)\) darf als gleichartig behandelt werden.

| Klasse | Bedeutung | Typische Behandlung |
|---|---|---|
| kontrollierbarer Faktor | Seine Stufen werden vom Planer gewählt | faktorieller, optimaler Versuchsplan |
| Szenario-/Kontextvariable | Besitzt einen relevanten Bereich, wird aber nicht direkt kontrolliert | Blockbildung, Stratifizierung |
| aleatorische Variable | Wird als inhärente Variation modelliert | Wahrscheinlichkeitsverteilung und Vorwärtsfortpflanzung |
| epistemischer Parameter | Aufgrund unzureichenden Wissens unsicher | Kalibrierung, Intervall-/Prior-Aktualisierung |
| Störparameter | Nicht selbst von Interesse, beeinflusst aber Ergebnisse | Marginalisierung, Profilierung |
| Modelldiskrepanz | Abweichung der Gleichungsstruktur von der Realität | separates Diskrepanzmodell oder Bias-Budget |

Selbst dieselbe physikalische Größe kann je nach Ziel unterschiedlich klassifiziert werden. Wichtiger als ihr Name ist die vorab getroffene Entscheidung, **welche Informationen zu ihrer Aktualisierung verwendet werden und auf welche Weise**.

Jede Eingabe benötigt mindestens folgende Metadaten:

- Definition und Einheiten
- zulässiger Bereich und dessen Begründung
- Verteilung oder Entwurfsstufen
- Korrelationen und Beschränkungen zwischen Eingaben
- ob sie fixiert oder geschätzt wird
- ob sie messbar ist
- wo sie in das Modell eingeht

## 2. DOE: ein Ausführungsbudget in Information umwandeln

### Grenzen von One-factor-at-a-time

OFAT, bei dem jeweils eine Variable verändert wird, ist leicht verständlich, übersieht aber Wechselwirkungen. Zum Beispiel gilt

$$
y=\beta_0+\beta_1x_1+\beta_2x_2+\beta_{12}x_1x_2
$$

Wenn \(\beta_{12}\) groß ist, verändert sich der Effekt von \(x_1\) mit der Stufe von \(x_2\). OFAT um einen einzelnen Referenzpunkt macht diese Struktur schwer erkennbar.

### Entwurfsarten und Ziele

| Entwurf | Vorteil | Vorsichtspunkt |
|---|---|---|
| vollständiger faktorieller Entwurf | schätzt Haupteffekte und Wechselwirkungen systematisch | Laufanzahl explodiert mit wachsender Dimension |
| fraktioneller faktorieller Entwurf | Screening mit weniger Läufen | Alias-Struktur muss interpretiert werden |
| Central Composite / Box–Behnken | effizient für eine quadratische Antwortfläche | anfällig für Extrapolation außerhalb des festgelegten Bereichs |
| Latin Hypercube | stratifiziert jede Achse gleichmäßig | Projektionsqualität und Korrelation prüfen |
| Folge mit geringer Diskrepanz | gut für Integration und globale SA geeignet | von unabhängigen Zufallsreplikaten unterscheiden |
| D-/I-optimaler Entwurf | für das Ziel eines bestimmten Regressionsmodells optimiert | Effizienz sinkt bei falschem angenommenen Modell |
| adaptiver/sequenzieller Entwurf | konzentriert Budget auf unsichere oder wichtige Bereiche | Stoppregel und Selektionsbias verwalten |

DOE bedeutet nicht nur, „den Raum gleichmäßig zu füllen“. Ein guter Entwurf hängt davon ab, ob das Ziel Screening, Surrogattraining, Optimierung, Parameteridentifikation oder Validierung ist.

### Randomisierung, Replikation und Blockbildung

- **Randomisierung** verringert die Gefahr, dass Zeitdrift oder Reihenfolgeeffekte mit einem bestimmten Faktor konfundiert werden.
- **Replikation** schätzt Variation unter identischen Bedingungen. Bei einem vollständig deterministischen Simulator liefert die einfache Wiederholung mit demselben Binary und derselben Umgebung keine neue Information; für einen stochastischen Löser oder nichtdeterministische Ausführung ist sie jedoch nötig.
- **Blockbildung** trennt schwer eliminierbare Störvariation, etwa Gerät, Charge, Datum oder Netzfamilie.

Auch in einer Simulationskampagne können Ausführungsreihenfolge, Rechenumgebung und Solver-Version Block- oder Provenienzvariablen sein.

## 3. Sensitivitätsanalyse: zuerst die Definition von Einfluss wählen

Welche Variable „am wichtigsten“ ist, hängt von der Metrik ab.

### Lokale Sensitivität

Die Ableitung um einen Referenzpunkt \(x_0\),

$$
S_i^{\mathrm{local}}
=
\left.
\frac{\partial f}{\partial x_i}
\right|_{x=x_0}
$$

beschreibt den Effekt einer kleinen Störung. Unterscheiden sich die Einheiten, ist ein dimensionsloser Index wie

$$
S_i^{\mathrm{scaled}}
=
\frac{x_i}{f}
\frac{\partial f}{\partial x_i}
$$

zu erwägen. Lokale Ableitungen sind effizient für gradientenbasierte Optimierung und linearisierte Unsicherheit, können aber Nichtlinearität, Schwellenwerte, Wechselwirkungen und die Abhängigkeit vom Referenzpunkt übersehen.

### Screening: die Morris-Familie

Werden elementare Effekte gesammelt, die durch einmaliges Verschieben jeder Eingabe an mehreren Stellen entstehen, zeigt ihr mittlerer Absolutwert den Gesamteinfluss, während ihre Varianz auf mögliche Nichtlinearität oder Wechselwirkungen hinweist. Dies ist nützlich, um in hohen Dimensionen unwichtige Variablen auszufiltern, stellt aber keine exakte Varianzzerlegung dar.

### Globale varianzbasierte Sensitivität

Unter der Annahme unabhängiger Eingaben kann die Ausgabevarianz in ANOVA-Form zerlegt werden.

$$
\operatorname{Var}(Y)
=
\sum_i V_i
+\sum_{i<j}V_{ij}
+\cdots
$$

Sobol-Index erster Ordnung und Total-Effect-Index lassen sich schreiben als

$$
S_i=\frac{V_i}{\operatorname{Var}(Y)},
\qquad
S_{T_i}
=
1-
\frac{
\operatorname{Var}_{X_{\sim i}}
\left(
\mathbb E[Y\mid X_{\sim i}]
\right)
}{
\operatorname{Var}(Y)
}
$$

\(S_i\) ist der alleinige Effekt von \(X_i\), während \(S_{T_i}\) jede Wechselwirkung mit \(X_i\) einschließt. Ein großes \(S_{T_i}-S_i\) signalisiert wichtige Wechselwirkungen.

### Die Falle korrelierter Eingaben

Die Standard-Sobol-Zerlegung setzt unabhängige Eingaben voraus. Besitzen physikalisch mögliche Eingabekombinationen Korrelationen oder Beschränkungen, kann unabhängiges Sampling unmögliche Zustände erzeugen. In diesem Fall sind Verfahren zu erwägen, die die Abhängigkeitsstruktur berücksichtigen, etwa bedingtes Sampling, gruppierte Indizes und Shapley-Effekte; die verwendete gemeinsame Verteilung ist anzugeben.

## 4. UQ: Unsicherheit in eine Ausgabeverteilung fortpflanzen

Das grundlegende Vorwärts-UQ-Problem besteht darin, Verteilung, Mittelwert, Varianz, Quantile und Ausfallwahrscheinlichkeit von \(Y\) in

$$
X\sim p_X(x),\qquad Y=f(X)
$$

zu schätzen.

### Monte Carlo

Unabhängige Stichproben \(x^{(j)}\) erzeugen und \(y^{(j)}=f(x^{(j)})\) berechnen. Dieser Ansatz ist relativ unempfindlich gegenüber der Dimension und einfach zu implementieren, bei seltenen Ereignissen oder teuren Simulationen jedoch kostspielig. Zusammen mit der Stichprobenzahl wird der Monte-Carlo-Standardfehler oder ein Konfidenzintervall angegeben.

### Surrogatgestützte UQ

Ist das ursprüngliche Modell teuer, wird eine Antwortfläche, ein gaußscher Prozess, Polynomial Chaos, ein neuronales Surrogat oder ein ähnliches Modell eingesetzt. Der Gesamtfehler zerfällt dann mindestens in folgende Terme.

$$
\text{UQ-Fehler}
=
\text{Stichprobenfehler}
+\text{Surrogatfehler}
+\text{Eingabemodellfehler}
+\text{numerischer Simulationsfehler}.
$$

Ein kleiner Surrogat-Testfehler allein garantiert weder genaue Randwahrscheinlichkeiten noch Sensitivitätsindizes. Fehler in für das UQ-Ziel wichtigen Bereichen – insbesondere nahe Grenzen, in Tails und an Beschränkungen – werden gesondert untersucht.

### Seltene Ereignisse

Bei einer kleinen Ausfallwahrscheinlichkeit liefert einfaches Monte Carlo fast keine Ausfallstichproben. Verfahren wie Importance Sampling, Subset Simulation, Splitting oder adaptive Surrogate können nötig sein. Wurde der Vorschlag nach Sichtung der Ergebnisse willkürlich angepasst, sind Schätzer-Bias und Gewichtsberechnung zu prüfen.

## 5. Kalibrierung: Parameter als inverses Problem schätzen

Für Beobachtungen \(d\), Simulator \(f(\theta,z)\), Parameter \(\theta\) und Beobachtungsbedingungen \(z\) gilt

$$
d=f(\theta,z)+\delta(z)+\varepsilon
$$

- \(\delta(z)\): Modelldiskrepanz
- \(\varepsilon\): Messrauschen

### Optimierungsperspektive

Gewichtete kleinste Quadrate werden ausgedrückt als

$$
\hat\theta
=
\arg\min_\theta
(d-f(\theta))^\mathsf T
\Sigma^{-1}
(d-f(\theta))
$$

Grenzen, Regularisierung oder eine Prior-Strafe können ergänzt werden.

### Bayessche Perspektive

$$
p(\theta\mid d)
\propto
p(d\mid\theta)p(\theta)
$$

Dabei repräsentiert die Likelihood die Mess- und Modellreststruktur, der Prior die vor der Beobachtung verfügbare Information. Das Ergebnis ist eine Posterior-Verteilung, keine einzelne Punktschätzung.

Bayessche Verfahren liefern nicht automatisch korrekte Unsicherheit, wenn Likelihood oder Diskrepanzmodell falsch sind. Ein enger Posterior bedeutet, dass Information unter den Modellannahmen konzentriert ist; er bedeutet nicht, dass jeder Fehler in der Realität klein ist.

## 6. Identifizierbarkeit: Optimierungserfolg ist nicht gleich Parameterlernen

### Strukturelle Identifizierbarkeit

Erzeugen verschiedene Parameter selbst unter der Annahme von null Rauschen und stetigen Beobachtungen dieselbe Ausgabe, sind sie strukturell nicht identifizierbar.

### Praktische Identifizierbarkeit

Selbst theoretisch identifizierbare Parameter lassen sich mit realen Daten schwer unterscheiden, wenn Beobachtungsorte, Bereiche, Rauschen oder Eingabeanregung unzureichend sind.

Hilfreiche Diagnosen:

- singuläres Spektrum von Jacobi-Matrix oder Fisher-Information
- Parameter-Profil-Likelihood
- Posterior-Korrelation
- Optimierung aus mehreren Anfangswerten
- synthetischer Wiederherstellungstest
- erwartete Information unter neuen Beobachtungsbedingungen

Sind Parameter stark korreliert, können einzelne Werte instabil sein, obwohl eine bestimmte Kombination oder Vorhersage stabil ist. Es ist zu unterscheiden, ob die Parameter selbst oder die Vorhersage das Ziel bilden.

## 7. Konfundierung von Modelldiskrepanz und Parametern

Wird der Modellstrukturfehler \(\delta(z)\) ignoriert, können Parameter diesen Fehler stattdessen absorbieren. Solche „effektiven Parameter“ passen die Kalibrierungsbedingungen gut an, können unter neuen Bedingungen aber ihre physikalische Bedeutung oder Vorhersagekraft verlieren.

Wird umgekehrt ein hochflexibles Diskrepanzmodell zugelassen, kann \(\delta\) jede Abweichung erklären und das Lernen der Parameter verhindern. Ein Problem, das Parameter und Diskrepanz gleichzeitig frei schätzt, kann inhärent konfundiert sein.

Strategien zur Minderung:

- vielfältige Bedingungen und Beobachtungstypen einbeziehen
- für jeden Parameter sensitive QoIs entwerfen
- physikalisch begründete Priors und Grenzen verwenden
- Glätte und Struktur der Diskrepanz beschränken
- Kalibrierungs- und Validierungsbedingungen trennen
- Parameterunsicherheit und Vorhersagediskrepanz getrennt berichten

## 8. Empfohlener End-to-End-Workflow

### Schritt 1: Ziel und Ausgaben definieren

Zuerst Entscheidung, QoI, akzeptablen Fehler und relevanten Eingabebereich fixieren. Statt „das Modell gut anpassen“ wird angegeben, welche Vorhersagen über welchen Bereich unterstützt werden sollen.

### Schritt 2: Eingabe-Audit

Eine Tabelle mit Eingabeeinheiten, Bereichen, gemeinsamen Verteilungen, physikalischen Beschränkungen und Informationsquellen erstellen. Epistemische und aleatorische Unsicherheit unterscheiden; bei mehrdeutiger Grenze mehrere Interpretationen als Szenarien behandeln.

### Schritt 3: Screening-DOE

Bei hoher Dimension Variablen mit geringem Einfluss durch faktorielle/fraktionelle Entwürfe, Morris-Verfahren, Ableitungs-Screening oder ähnliche Werkzeuge herausfiltern. Screening-Schwelle und möglicherweise übersehene Wechselwirkungen aufzeichnen.

### Schritt 4: Raumfüllende oder zielgerichtete DOE

Je nach Ziel – Surrogatmodellierung, globale SA oder Kalibrierung – LHS, eine Folge geringer Diskrepanz oder einen optimalen Entwurf wählen. Physikalisch unmögliche Kombinationen durch beschränkungsbewusstes Sampling ausschließen.

### Schritt 5: Numerische Qualitätskontrolle

Konvergenz, Erhaltung, Fehlercode und Netz-/Zeitschritt-Provenienz jedes Laufs aufzeichnen. Solver-Fehler einfach zu löschen kann die geschätzte zulässige Region verzerren; der Fehler selbst wird daher als Ergebnis verwaltet.

### Schritt 6: Surrogatvalidierung

Einen vom Training unabhängigen Testentwurf verwenden. Neben dem mittleren Fehler auch den schlechtesten Bereich, Tails, Ableitungen und die Region prüfen, in der sich der Kalibrierungs-Posterior konzentrieren wird.

### Schritt 7: Globale SA und Vorwärts-UQ

Das gemeinsame Eingabemodell angeben und auch die Monte-Carlo-Unsicherheit der Sensitivitätsindizes berechnen. Prüfen, ob Rangfolgen der Eingabewichtigkeit gegenüber Stichprobengröße und Surrogatwahl stabil sind.

### Schritt 8: Kalibrierung

Likelihood, Prior, Grenzen, Diskrepanzannahmen sowie Optimizer-/Sampler-Diagnosen aufzeichnen. Identifizierbarkeit durch synthetische Wiederherstellung und Multi-Start-Läufe prüfen.

### Schritt 9: Validierung

Beobachtungen unter nicht verwendeten Bedingungen und QoIs mit der Vorhersageverteilung vergleichen. Vorhersagen außerhalb der Stichprobe statt Kalibrierungsresiduen bewerten.

### Schritt 10: Sequenzielle Aktualisierung

Den nächsten Lauf oder die nächste Messung wählen, der beziehungsweise die die aktuelle Unsicherheit am stärksten verringert. Akquisitionsregel und Stoppkriterium vorab definieren, um endlose Exploration zu vermeiden.

## 9. Prüfliste zur Verifikation

- [ ] Werden die Ziele von DOE, Sensitivität, UQ und Kalibrierung getrennt gehalten?
- [ ] Besitzen Eingabebereiche und -verteilungen eine technische Begründung?
- [ ] Sind Korrelationen und physikalische Beschränkungen im gemeinsamen Sampling abgebildet?
- [ ] Wurde OFAT als alleinige Grundlage für die Schlussfolgerung vermieden, es gebe keine Wechselwirkungen?
- [ ] Ist die Replikation passend zum deterministischen oder stochastischen Verhalten entworfen?
- [ ] Sind Definition und Annahmen der Sensitivitätsmetrik angegeben?
- [ ] Wird die Sampling-Unsicherheit des Sensitivitätsindex selbst berichtet?
- [ ] Ist der Surrogatfehler in UQ-Ergebnissen enthalten oder getrennt quantifiziert?
- [ ] Wurde die Identifizierbarkeit der Kalibrierungsparameter diagnostiziert?
- [ ] Wurde geprüft, ob Modelldiskrepanz von Parametern absorbiert werden könnte?
- [ ] Sind Kalibrierungs- und Validierungsdaten getrennt?
- [ ] Werden Zufalls-Seed, Entwurfsgenerator, Ausführungsreihenfolge und fehlgeschlagene Läufe bewahrt?

## 10. Häufige Fallstricke und Einschränkungen

### Der Irrtum, breitere Bereiche seien immer konservativer

Eine unbegründet breite unabhängige Gleichverteilung kann in der Realität unmögliche Kombinationen erzeugen und Sensitivitätsrangfolgen künstlich verändern. Ein Bereich sollte neben Konservativität auch die gemeinsame Zulässigkeit widerspiegeln.

### Der Irrtum, ein Korrelationskoeffizient erfasse die gesamte Abhängigkeitsstruktur

Lineare Korrelation kann Tail-Abhängigkeit, nichtlineare Beschränkungen oder Multimodalität nicht beschreiben.

### Nur dem mittleren Testwert des Surrogats vertrauen

Ein kleiner globaler RMSE garantiert weder Genauigkeit um einen Schwellenwert noch in Tails oder Gradienten. Validierungsmetriken müssen zur nachgelagerten Aufgabe passen.

### Einen Parameter-Posterior als physikalische Konstante interpretieren

Ein unter Vernachlässigung der Modelldiskrepanz ermittelter Kalibrierungsparameter kann ein bedingungsabhängiger Korrekturwert sein.

### Jede insensitive Variable entfernen

Eine Variable ist nur für die aktuelle Ausgabe und den aktuellen Bereich insensitiv; für eine andere QoI, ein anderes Regime oder Tail-Ereignis kann sie dennoch wichtig sein.

### Übermäßige Dimension bei kleinem Rechenbudget

Hochdimensionale globale SA und flexible Kalibrierung gleichzeitig mit wenigen Läufen durchzuführen, macht die Schätzer instabil. Screening, strukturelle Dimensionsreduktion und informative Messungen sollten zuerst erfolgen.

## Fazit

Eine belastbare Simulationsstudie entsteht nicht durch möglichst viele Läufe, sondern durch **Läufe mit getrennten Informationsflüssen**. DOE bestimmt, wo gesucht wird, Sensitivitätsanalyse erklärt, was wichtig ist, UQ berechnet die Breite der Schlussfolgerung, und Kalibrierung aktualisiert unbekannte Parameter anhand von Beobachtungen.

Abschließend fragt die Validierung, ob Vorhersagen unter all diesen Annahmen beim Zusammentreffen mit neuen Informationen noch ihrem Zweck genügen. Schon die Trennung von Fragen und Daten dieser vier Stufen verringert Überanpassung, falsche Präzision und nicht interpretierbare Parameter erheblich.
