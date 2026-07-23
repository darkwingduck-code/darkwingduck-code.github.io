---
title: "Kleinste Quadrate richtig anwenden: Projektion, Konditionierung, QR und SVD"
date: 2026-07-21 09:10:00 +0900
categories: [Mathematics, Numerical Linear Algebra]
tags: [least-squares, projection, conditioning, qr, svd, pseudoinverse, regularization]
description: "Kleinste Quadrate als orthogonales Projektionsproblem interpretieren und Konditionszahlen, QR, SVD, Pseudoinverse und Regularisierung aus Sicht numerischer Stabilität verbinden."
math: true
lang: de-DE
translation_key: least-squares-projection-conditioning-svd
hidden: true
---

{% include language-switcher.html %}

Wenn sich die Beobachtungsgleichung \(Ax=b\) nicht exakt lösen lässt, lernt man häufig, „beide Seiten mit \(A^\mathsf T\) zu multiplizieren“. Der Kern der kleinsten Quadrate ist jedoch kein Auswendiglernen einer Formel, sondern liegt in drei Fragen.

1. Was minimieren wir?
2. Warum hängt die Lösung mit der orthogonalen Projektion auf den Spaltenraum zusammen?
3. Welcher Algorithmus berechnet dieselbe mathematische Lösung stabil?

Dieser Artikel ordnet die Geometrie kleinster Quadrate, die Gefahr der Normalgleichungen, die Rollen von QR und SVD, Rangdefizienz und Regularisierung in einem zusammenhängenden Ablauf.

## 1. Definition des Problems der kleinsten Quadrate

Für \(A\in\mathbb R^{m\times n}\) und \(b\in\mathbb R^m\) besitzt das überbestimmte System \(Ax=b\) im Allgemeinen keine exakte Lösung. Die Methode der kleinsten Quadrate minimiert die euklidische Norm des Residuums

$$
r(x)=b-Ax
$$

wie folgt.

$$
x_\star
=
\arg\min_x \|Ax-b\|_2^2.
$$

\(Ax\) liegt stets in \(\mathcal C(A)\), dem Spaltenraum von \(A\). Gesucht wird daher das dem Vektor \(b\) nächstgelegene Element \(\hat b=Ax_\star\) dieses Spaltenraums.

## 2. Orthogonale Projektion und Normalgleichungen

Am nächstgelegenen Punkt steht das Residuum \(r_\star=b-Ax_\star\) senkrecht auf jeder Richtung im Spaltenraum.

$$
A^\mathsf T r_\star=0.
$$

Das Ausmultiplizieren ergibt die Normalgleichungen.

$$
A^\mathsf T A x_\star=A^\mathsf T b.
$$

Besitzt \(A\) vollen Spaltenrang, ist \(A^\mathsf T A\) positiv definit und die Lösung eindeutig.

$$
x_\star=(A^\mathsf T A)^{-1}A^\mathsf T b.
$$

Diese Gleichung ist jedoch ein **mathematischer Ausdruck**, kein empfohlenes Rechenverfahren. In echtem Code sollte bei geforderter Genauigkeit im Allgemeinen vermieden werden, eine Inverse ausdrücklich zu bilden oder die Normalgleichungen bedingungslos zu lösen.

Die Projektionsmatrix lautet

$$
P=A(A^\mathsf T A)^{-1}A^\mathsf T
$$

und \(\hat b=Pb\). Bei vollem Spaltenrang erfüllt \(P\)

$$
P^\mathsf T=P,\qquad P^2=P
$$

Symmetrie bedeutet, dass die Projektion orthogonal ist; Idempotenz bedeutet, dass erneutes Projizieren eines bereits projizierten Wertes ihn nicht verändert.

## 3. Einfaches Regressionsbeispiel

Angenommen, an mehrere Punkte wird ein lineares Modell \(y\approx\beta_0+\beta_1t\) angepasst. Die Entwurfsmatrix lautet

$$
A=
\begin{bmatrix}
1&t_1\\
1&t_2\\
\vdots&\vdots\\
1&t_m
\end{bmatrix},
\qquad
x=
\begin{bmatrix}\beta_0\\\beta_1\end{bmatrix},
\qquad
b=
\begin{bmatrix}y_1\\y_2\\\vdots\\y_m\end{bmatrix}.
$$

Die Least-Squares-Lösung minimiert nicht den **senkrechten Abstand** der Datenpunkte von der Geraden. Sie minimiert die Summe quadrierter Residuen in der angegebenen \(y\)-Richtung. Sind beide Achsen fehlerbehaftet, können orthogonale Distanzregression oder ein Errors-in-variables-Modell geeigneter sein.

Sind außerdem die Absolutwerte von \(t\) sehr groß oder liegt sein Bereich stark auf einer Seite, kann die numerische Unterscheidung von Achsenabschnitts- und Steigungsspalte schwierig werden. Zentrierung und geeignete Skalierung von \(t\) verbessern sowohl Konditionszahl als auch Interpretierbarkeit der Koeffizienten.

## 4. Konditionszahlen: Wie stark Eingabefehler in der Lösung verstärkt werden

Die Konditionszahl eines invertierbaren quadratischen Systems in der 2-Norm lautet

$$
\kappa_2(A)
=
\|A\|_2\|A^{-1}\|_2
=
\frac{\sigma_{\max}}{\sigma_{\min}}
$$

Für eine rechteckige Matrix mit vollem Spaltenrang besitzt das Verhältnis des größten zum kleinsten von null verschiedenen Singulärwert dieselbe Bedeutung.

Eine große Konditionszahl führt zu folgenden Erscheinungen.

- Kleine Fehler in der Eingabe \(b\) werden in \(x\) stark verstärkt.
- Nahezu identische Spalten lassen Koeffizienten stark schwanken.
- Parameterschätzungen können trotz kleinen Residuums instabil sein.
- Gleitkomma-Rundungsfehler wirken sich stärker aus.

Die Normalgleichungen besitzen ein entscheidendes Problem.

$$
\kappa_2(A^\mathsf T A)=\kappa_2(A)^2.
$$

Eine bereits schlechte Konditionszahl wird quadriert. Auch beim Bilden von \(A^\mathsf T A\) können signifikante Stellen verloren gehen.

> Ein kleines Residuum und genaue Parameter sind nicht dasselbe. Selbst wenn \(b\) nahe am Spaltenraum liegt, können bei nahezu abhängigen Spalten sehr unterschiedliche Koeffizienten ähnliche Vorhersagen erzeugen.

## 5. Kleinste Quadrate mit QR lösen

Angenommen, \(A\) besitzt vollen Spaltenrang und

$$
A=QR,
$$

wobei die Spalten von \(Q\in\mathbb R^{m\times n}\) orthonormal sind und \(R\in\mathbb R^{n\times n}\) eine obere Dreiecksmatrix ist. Dann gilt

$$
\|Ax-b\|_2^2
=
\|Rx-Q^\mathsf Tb\|_2^2
+\|(I-QQ^\mathsf T)b\|_2^2.
$$

Da der zweite Term unabhängig von \(x\) ist, kann

$$
Rx=Q^\mathsf T b
$$

durch Rückwärtseinsetzen gelöst werden.

In der Praxis ist Householder-QR gewöhnlich stabiler als klassisches Gram–Schmidt. Ist der Rang zweifelhaft, wird spaltenpivotiertes QR

$$
AP=QR
$$

verwendet, um wichtige Spalten nach vorn zu bringen und den effektiven Rang zu diagnostizieren.

## 6. SVD und Pseudoinverse

Die SVD zerlegt eine Matrix als

$$
A=U\Sigma V^\mathsf T
$$

Die Spalten von \(U\) und \(V\) sind orthonormal, und die Diagonaleinträge \(\sigma_i\) von \(\Sigma\) sind die Singulärwerte.

Die Moore-Penrose-Pseudoinverse lautet

$$
A^+=V\Sigma^+U^\mathsf T
$$

und die Lösung kleinster Norm unter allen Least-Squares-Lösungen ist

$$
x_\star=A^+b
=
\sum_{\sigma_i>0}
\frac{u_i^\mathsf Tb}{\sigma_i}v_i
$$

Diese Gleichung legt die Ursache schlechter Konditionierung unmittelbar offen. In Richtungen mit kleinem \(\sigma_i\) wird selbst geringes Rauschen in \(u_i^\mathsf Tb\) durch \(1/\sigma_i\) verstärkt.

### Wann SVD besonders nützlich ist

- Wenn Rangdefizienz vorliegt oder vermutet wird
- Wenn Nullraum und identifizierbare Richtungen untersucht werden sollen
- Wenn eine Lösung kleinster Norm benötigt wird
- Bei der Diagnose der Konditionierung aus dem Singulärspektrum
- Bei Regularisierung wie abgeschnittener SVD

SVD bietet die größte Diagnosekraft, kann aber mehr Rechenzeit und Speicher als QR benötigen. Die Wahl richtet sich nach Problemgröße, Dünnbesetztheit und geforderter Genauigkeit.

## 7. Rangdefizienz und nicht eindeutige Lösungen

Wenn \(\operatorname{rank}(A)<n\), können verschiedene Werte von \(x\) dasselbe \(Ax\) erzeugen. Für \(z\in\mathcal N(A)\) gilt

$$
A(x+z)=Ax
$$

Ist also \(x\) eine Least-Squares-Lösung, besitzt \(x+z\) dasselbe Residuum. Die Pseudoinversenlösung wählt jene mit kleinstem \(\|x\|_2\).

Rang ist bei numerischen Daten nicht binär. Für einen Singulärwert-Cutoff \(\tau\) können Richtungen verworfen werden, die

$$
\sigma_i\le\tau
$$

erfüllen. \(\tau\) ist jedoch kein bloßes Implementierungsdetail, sondern eine Modellierungsentscheidung darüber, welche Richtungen als nicht identifizierbar gelten. Sie sollte Skala, Rauschniveau und Zweck widerspiegeln.

## 8. Gewichtete kleinste Quadrate und Kovarianz

Besitzen Residuenkomponenten unterschiedliche Varianzen oder sind sie korreliert, ist die Gleichgewichtungsannahme gewöhnlicher kleinster Quadrate ungeeignet. Ist die Fehlerkovarianz \(\Sigma_b\), gilt

$$
x_\star
=
\arg\min_x
(Ax-b)^\mathsf T\Sigma_b^{-1}(Ax-b).
$$

Eine Whitening-Matrix mit \(W^\mathsf TW=\Sigma_b^{-1}\) transformiert das Problem zu

$$
\min_x\|W(Ax-b)\|_2^2
$$

Gewichte dürfen keine willkürlichen Komfortwerte sein, sondern müssen mit der Wahrscheinlichkeitsstruktur der Residuen verbunden sein.

## 9. Regularisierung ist eine zusätzliche Annahme, kein numerischer Trick

Tichonow-Regularisierung kann geschrieben werden als

$$
x_\lambda
=
\arg\min_x
\left(
\|Ax-b\|_2^2
+\lambda^2\|L(x-x_0)\|_2^2
\right)
$$

- \(x_0\): Prior- oder Referenzlösung
- \(L\): zu bestrafende Struktur
- \(\lambda\): Ausgleich zwischen Datenanpassung und Prior

Mit \(L=I\) und \(x_0=0\) entsteht die Ridge-Form. Regularisierung verringert Varianz um den Preis eines Bias. Sie ist daher als Modellierungsschritt zu behandeln, der plausiblere Lösungen festlegt, nicht als „beliebig kleinen Wert hinzufügen, weil die Konditionszahl schlecht ist“.

\(\lambda\) kann mit Kreuzvalidierung, Diskrepanzprinzip, L-Kurve, generalisierter Kreuzvalidierung und weiteren Methoden gewählt werden. Unabhängig vom Verfahren werden Auswahlkriterium und Unabhängigkeit der Evaluationsdaten aufgezeichnet.

## 10. Leitfaden zur Algorithmuswahl

| Situation | Zuerst zu erwägende Wahl | Grund |
|---|---|---|
| dicht, voller Rang, gewöhnliche Konditionierung | Householder-QR | verbindet Stabilität und Kosten |
| Rang unklar, Diagnose wichtig | SVD | zeigt Singulärspektrum und Nullraum |
| Spaltenrang muss bestimmt werden | pivotiertes QR oder SVD | schätzt effektiven Rang |
| sehr großes dünnbesetztes Problem | iterativer Least-Squares-Solver | vermeidet Kosten einer Matrixfaktorisierung |
| Kovarianzstruktur vorhanden | geweißte/gewichtete kleinste Quadrate | bildet das Fehlermodell ab |
| schlecht gestelltes inverses Problem | regularisierter Solver | unterdrückt instabile Richtungen |
| Geschwindigkeit entscheidend und Konditionierung gut | Cholesky auf den Normalgleichungen sorgfältig erwägen | schnell, aber Risiko der quadrierten Konditionszahl |

Standard sollte eine Funktion sein, die das lineare System direkt löst, statt „Inverse berechnen und multiplizieren“. Bibliotheksfunktionen wie `solve`, `lstsq` und Sparse-Solver nutzen interne Faktorisierungen und Fehlerbehandlung.

## 11. Praktischer Workflow

1. **Ziel definieren**: Ist Vorhersage oder Parameterinterpretation wichtig?
2. **Dimensionen und Einheiten prüfen**: Shapes und physikalische Einheiten von \(A\), \(x\) und \(b\) notieren.
3. **Skalieren**: Spaltennormen, Variablenbereiche und Einheiten untersuchen; bei Bedarf zentrieren und standardisieren.
4. **Rang diagnostizieren**: QR-Pivots oder Singulärspektrum untersuchen.
5. **Solver wählen**: Standardmäßig QR verwenden; für Rang- und Konditionierungsdiagnose SVD erwägen.
6. **Residuen analysieren**: Struktur, Bias, Heteroskedastizität und Korrelation statt nur einer Norm untersuchen.
7. **Orthogonalität verifizieren**: Prüfen, ob \(A^\mathsf Tr\) innerhalb der Toleranz null ist.
8. **Sensitivität prüfen**: Eingabe innerhalb ihres zulässigen Bereichs stören und Änderungen von Koeffizienten sowie Vorhersagen beobachten.
9. **Unsicherheit berichten**: Parameterunsicherheit berechnen, sofern Rauschmodell und Kovarianzannahmen gültig sind.
10. **Reproduzierbarkeitsdetails erfassen**: Solver, Toleranz, Skalierung, Rang-Cutoff und Auswahlverfahren der Regularisierung bewahren.

## 12. Prüfliste zur Verifikation

- [ ] Sind minimierte Norm und Gewichte angegeben?
- [ ] Liegt \(Ax_\star\) im Spaltenraum und gilt \(A^\mathsf Tr\approx0\)?
- [ ] Wurde der angenommene volle Rang tatsächlich verifiziert?
- [ ] Wurde eine Inverse von \(A^\mathsf TA\) vermieden?
- [ ] Wurden Konditionszahlen vor und nach Spaltenskalierung verglichen?
- [ ] Wurden Singulärwerte und Cutoff gemeinsam aufgezeichnet?
- [ ] Wurden Residuengröße und Parameterstabilität getrennt bewertet?
- [ ] Wurde eine Überanpassung des Regularisierungsparameters an Evaluationsdaten vermieden?
- [ ] Stimmen Gewichte der gewichteten kleinsten Quadrate mit dem Fehlermodell überein?
- [ ] Wurden Vorhersageintervalle von Parameterkonfidenzintervallen getrennt?

## 13. Fallstricke und Einschränkungen

### Ein hohes \(R^2\) mit einem gut gelösten Problem verwechseln

Hohe Erklärungskraft garantiert weder Residuenunabhängigkeit noch Modellangemessenheit oder Parameteridentifizierbarkeit. Bei Extrapolation ist dies besonders gefährlich.

### Eingabeeinheiten ändern und Koeffizientengrößen direkt vergleichen

Die Koeffizientengröße hängt von der Variablenskala ab. Vor dem Vergleich der Wichtigkeit müssen Einheiten und Skalierung übereinstimmen.

### Glauben, die Pseudoinverse stelle die „wahre Lösung“ wieder her

Die Pseudoinverse wählt lediglich anhand eines klaren Optimierungskriteriums eine repräsentative Lösung; aus den Daten verlorene Nullrauminformation kann sie nicht wiederherstellen.

### Modellstrukturfehler mit Regularisierung verbergen

Regularisierung mildert Schlechtgestelltheit, behebt aber weder ausgelassene Variablen noch einen falschen Beobachtungsoperator oder systematischen Bias.

### Grenzen linearisierter kleinster Quadrate

Ein nichtlineares Modell \(f(x)\) erfordert lokale Linearisierung und iterative Optimierung. Anfangswerte, lokale Minima und Konditionierung der Jacobi-Matrix werden zu zusätzlichen Fragen.

## Fazit

Kleinste Quadrate sind nicht bloß eine „Formel zur Verringerung der Summe quadrierter Fehler“, sondern ein **Projektionsproblem auf einen Unterraum**. QR ist das grundlegende Werkzeug, um diese Projektion stabil zu berechnen; SVD ist das Diagnosewerkzeug, das Rang und instabile Richtungen offenlegt. Die Konditionszahl fragt, ob die Berechnung vertrauenswürdig ist, und Regularisierung benennt ausdrücklich, welche Annahmen fehlende Informationen ersetzen.

Kleinste Quadrate werden zu einer reproduzierbaren Analyse, wenn Residuumsorthogonalität, Singulärspektrum, Skalierung, Solver und Toleranz zusammen mit den Endwerten bewahrt werden.
