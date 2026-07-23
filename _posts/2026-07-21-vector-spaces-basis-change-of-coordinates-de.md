---
title: "Von Vektorräumen zum Basiswechsel: Die Struktur der linearen Algebra verstehen"
date: 2026-07-21 09:00:00 +0900
categories: [Mathematics, Linear Algebra]
tags: [vector-space, subspace, span, linear-independence, basis, dimension, change-of-basis]
description: "Untervektorräume, Spann, lineare Unabhängigkeit, Basen, Dimensionen und Koordinatentransformationen durch Definitionen, durchgerechnete Beispiele und praktische Validierungsverfahren verbinden."
math: true
lang: de-DE
translation_key: vector-spaces-basis-change-of-coordinates
hidden: true
---

{% include language-switcher.html %}

Ein großer Teil der Verwirrung in der linearen Algebra beginnt nicht bei Rechenmethoden, sondern beim **Vermischen von Konzepten unterschiedlicher Ebenen**. Ein Vektorraum ist der Rahmen, in dem Operationen gültig sind; ein Untervektorraum ist ein kleinerer, unter diesen Operationen abgeschlossener Rahmen. Der Spann ist der Bereich, der aus gegebenen Vektoren erzeugt werden kann, lineare Unabhängigkeit bedeutet Redundanzfreiheit der Darstellung, und eine Basis ist ein Koordinatensystem, das beide Eigenschaften erfüllt.

Ziel dieses Artikels ist nicht, Begriffe getrennt auswendig zu lernen, sondern folgende Fragen konsistent zu beantworten.

- Ist eine gegebene Menge wirklich ein Untervektorraum?
- Welchen Raum spannen gegebene Vektoren auf?
- Wie wird Redundanz aus einem Erzeugendensystem entfernt?
- Wann können Vektoren eine Basis bilden?
- Wie ändern sich bei einem Basiswechsel der Vektor selbst und seine Koordinaten?

## 1. Vektorräume: Mengen, in denen Linearkombinationen sicher enthalten bleiben

Ein Vektorraum $V$ über einem Körper $\mathbb F$ ist eine Menge mit Vektoraddition und Skalarmultiplikation. In der Praxis stammen die Skalare meist aus $\mathbb R$ oder $\mathbb C$. Axiome wie Assoziativität, Kommutativität und Distributivität werden nicht jedes Mal einzeln geprüft; ihr Kern lässt sich auf folgende Aussage verdichten.

> Für $u,v\in V$ und $a,b\in\mathbb F$ muss auch jede Linearkombination $au+bv$ zu $V$ gehören.

Vektoren sind nicht auf Zahlenfolgen beschränkt. Auch Polynome, Matrizen, Funktionen und Signale sind Vektoren, wenn ihre Addition und Skalarmultiplikation die Axiome erfüllen. Das Wesen der linearen Algebra ist daher nicht die Geometrie von Pfeilen, sondern eine **Struktur, die Linearkombinationen bewahrt**.

## 2. Untervektorräume: Ein einzeiliger Test, der stärker ist als drei Einzelbedingungen

Damit $W\subseteq V$ ein Untervektorraum ist, muss er folgende Bedingungen erfüllen.

1. Der Nullvektor gehört zu $W$.
2. Er ist unter Addition abgeschlossen.
3. Er ist unter Skalarmultiplikation abgeschlossen.

Zu einem einzigen Test verbunden ergibt sich:

$$
u,v\in W,\quad a,b\in\mathbb F
\quad\Longrightarrow\quad
au+bv\in W.
$$

Prüfen Sie außerdem $W\neq\varnothing$, damit die leere Menge nicht fälschlich besteht.

### Homogene Constraints erzeugen Untervektorräume, inhomogene im Allgemeinen nicht

Für eine Matrix $A$ ist

$$
W=\{x\mid Ax=0\}
$$

immer ein Untervektorraum. Wenn $Au=0$ und $Av=0$, dann gilt wegen der Linearität

$$
A(au+bv)=aAu+bAv=0
$$

Deshalb ist ein Nullraum ein Untervektorraum.

Dagegen enthält

$$
S=\{x\mid Ax=c\},\qquad c\neq 0
$$

im Allgemeinen den Nullvektor nicht und ist daher kein Untervektorraum. Existieren Lösungen, ist $S$ eine durch Verschiebung des Nullraums entstandene **affine Menge**. Eine Gerade oder Ebene, die nicht durch den Ursprung verläuft, ist ein typisches Beispiel.

## 3. Spann: Alles, was sich aus den gegebenen Bausteinen erzeugen lässt

Der Spann der Vektoren $v_1,\dots,v_k$ ist die Menge all ihrer Linearkombinationen.

$$
\operatorname{span}(v_1,\dots,v_k)
=
\left\{
\sum_{i=1}^{k}a_i v_i
\;\middle|\;
a_i\in\mathbb F
\right\}.
$$

Der Spann ist der **kleinste Untervektorraum**, der alle $v_1,\dots,v_k$ enthält. Das Hinzufügen weiterer Spannvektoren erhöht die Dimension nicht zwingend. Liegt ein neuer Vektor bereits im vorhandenen Spann, wird nur die Darstellung redundant; der Raum bleibt unverändert.

Die Matrix

$$
A=[v_1\;v_2\;\cdots\;v_k]
$$

macht $\operatorname{span}(v_1,\dots,v_k)$ zum Spaltenraum von $A$. Ob ein Vektor $y$ zu diesem Spann gehört, entscheidet die Lösbarkeit von $Ac=y$.

## 4. Lineare Unabhängigkeit: Eindeutigkeit der Darstellung des Nullvektors

Die Vektormenge $\{v_1,\dots,v_k\}$ ist linear unabhängig, wenn

$$
a_1v_1+\cdots+a_kv_k=0
$$

nur die Lösung $a_1=\cdots=a_k=0$ besitzt. Können von null verschiedene Koeffizienten den Nullvektor erzeugen, ist die Menge linear abhängig.

Aus Sicht der Matrix sind folgende Aussagen äquivalent.

- $v_1,\dots,v_k$ sind linear unabhängig.
- Die einzige Lösung von $Ac=0$ ist $c=0$.
- Die Zahl der Pivotspalten in $A$ ist $k$.
- $\operatorname{rank}(A)=k$.
- Die Nullität ist 0.

### Eine häufig falsche Aussage: „Ein Basisvektor muss nur von null verschieden sein“

Für einen einzelnen Vektor $v$ mit $v\neq0$ ist $\{v\}$ eine Basis des von ihm erzeugten eindimensionalen Untervektorraums $\operatorname{span}(v)$. Er ist jedoch keine Basis eines beliebigen größeren Untervektorraums. Für eine Basis müssen Vektoren nicht nur **linear unabhängig** sein, sondern auch den gesamten Zielraum **aufspannen**.

## 5. Basis und Dimension: Minimales Erzeugendensystem und maximale unabhängige Menge

Eine Basis $B=(b_1,\dots,b_n)$ eines Untervektorraums $W$ erfüllt beide Bedingungen.

1. $\operatorname{span}(b_1,\dots,b_n)=W$
2. $b_1,\dots,b_n$ sind linear unabhängig.

Damit lässt sich eine Basis auf zwei Arten verstehen.

- Ein **minimales Erzeugendensystem**, das nach Entfernen eines Vektors nicht mehr den gesamten Raum aufspannt
- Eine **maximale unabhängige Menge**, die nach Hinzufügen eines weiteren Vektors abhängig wird

Jede Basis eines endlichdimensionalen Raums besitzt dieselbe Zahl von Vektoren. Diese Zahl ist die Dimension $\dim W$. Für eine Matrix $A\in\mathbb F^{m\times n}$ gilt

$$
\operatorname{rank}(A)+\operatorname{nullity}(A)=n
$$

Das bedeutet, dass die $n$ Eingabefreiheitsgrade in beobachtbare Richtungen des Spaltenraums und von $A$ ausgelöschte Richtungen des Nullraums zerfallen.

## 6. Durchgerechnetes Beispiel: Die Basis einer Ebene auf zwei Wegen finden

Betrachten Sie die homogene Ebene

$$
W=\{(x,y,z)^\mathsf T\in\mathbb R^3\mid x+y+z=0\}.
$$

Da aus dem Constraint $x=-y-z$ folgt,

$$
\begin{bmatrix}x\\y\\z\end{bmatrix}
=
y\begin{bmatrix}-1\\1\\0\end{bmatrix}
+
z\begin{bmatrix}-1\\0\\1\end{bmatrix}.
$$

ist eine Basiskandidatin

$$
B=
\left(
\begin{bmatrix}-1\\1\\0\end{bmatrix},
\begin{bmatrix}-1\\0\\1\end{bmatrix}
\right)
$$

Die beiden Vektoren sind keine skalaren Vielfachen voneinander und daher unabhängig; sie spannen jede Lösung auf. Somit ist $\dim W=2$.

Zum selben Ergebnis gelangen wir mit Rang und Nullität. Die Constraint-Matrix $A=[1\;1\;1]$ besitzt Rang 1, also ist ihre Nullität $3-1=2$. Dass verschiedene Ansätze dieselbe Dimension liefern, ist eine nützliche Verifikationstechnik.

## 7. Koordinaten vom Vektor selbst unterscheiden

Wenn die Koordinaten eines Vektors $v$ in der Basis $B=(b_1,\dots,b_n)$ als

$$
[v]_B=
\begin{bmatrix}c_1\\\vdots\\c_n\end{bmatrix}
$$

geschrieben werden, gilt

$$
v=c_1b_1+\cdots+c_nb_n
$$

Hier ist $v$ ein abstraktes Objekt, während $[v]_B$ eine von der gewählten Basis abhängige numerische Darstellung ist.

Im Folgenden wird angenommen, dass zwei Basen eines $n$-dimensionalen Raums in einem einzigen festen $n$-dimensionalen Referenzkoordinatensystem ausgedrückt sind, sodass ihre Basismatrizen quadratisch und invertierbar sind. Bezeichnet $B$ auch die Matrix mit den Basisvektoren als Spalten, dann gilt

$$
v=B[v]_B,\qquad [v]_B=B^{-1}v
$$

Sind $B$ und $C$ zwei Basen desselben Raums, dann

$$
[v]_C=C^{-1}B[v]_B.
$$

Die Matrix zur Umwandlung von $B$-Koordinaten in $C$-Koordinaten ist somit

$$
P_{C\leftarrow B}=C^{-1}B
$$

Den tiefgestellten Pfeil als „von der Eingabebasis zur Ausgabebasis“ zu lesen hilft, Fehler in der Multiplikationsreihenfolge zu vermeiden.

Wenn eine Unterraumbasis direkt in den Koordinaten eines größeren umgebenden Raums geschrieben ist, kann die Basismatrix rechteckig sein und $B^{-1}$ existiert nicht. Lösen Sie in diesem Fall $B[v]_B=v$ mit QR oder einem ähnlichen Verfahren oder wählen Sie zuerst eine feste Referenzbasis im Unterraum und drücken Sie sie als quadratische Koordinatenmatrix aus.

### Auch die Matrix einer linearen Abbildung hängt von der Basis ab

Ist $A$ die Standardbasismatrix einer linearen Abbildung $T:V\to V$ und $B$ die neue Basismatrix, dann

$$
[T]_B=B^{-1}AB.
$$

Die Sequenz überführt einen Vektor von den neuen Koordinaten in Standardkoordinaten, wendet $A$ an und führt ihn in die neuen Koordinaten zurück. Da $A$ und $B^{-1}AB$ dieselbe lineare Abbildung in verschiedenen Koordinatensystemen ausdrücken, teilen sie Ähnlichkeitsinvarianten wie Spur, Determinante und Eigenwerte.

## 8. Praktischer Lösungsworkflow

### Wenn eine Menge gegeben ist

1. Umgebenden Raum und Skalarkörper angeben.
2. Zuerst prüfen, ob sie den Nullvektor enthält.
3. Für beliebige $u,v$ und Skalare $a,b$ verifizieren, dass $au+bv$ die definierende Bedingung bewahrt.
4. Bei einem inhomogenen konstanten Term, einer Ungleichung oder einer festen Norm zuerst untersuchen, ob vermutlich kein Untervektorraum vorliegt.

### Wenn Spannvektoren gegeben sind

1. Eine Matrix mit den Vektoren als Spalten erstellen.
2. Pivotspalten per Zeilenreduktion finden.
3. Die Pivotspalten der **ursprünglichen Matrix** als Basis des Spaltenraums auswählen.
4. Rang mit der Zahl der Basisvektoren vergleichen.

Die Spalten einer zeilenreduzierten Matrix können einen anderen Spaltenraum als das Original besitzen. Zeilenoperationen bewahren den Zeilenraum, im Allgemeinen jedoch nicht den Spaltenraum selbst.

### Wenn eine Koordinatentransformation gegeben ist

1. Das Koordinatensystem angeben, in dem jeder Basisvektor geschrieben ist.
2. Spaltenreihenfolge der Basismatrix an die Reihenfolge der Koordinatenkomponenten anpassen.
3. $P_{C\leftarrow B}=C^{-1}B$ berechnen.
4. Verifizieren, dass $CP_{C\leftarrow B}=B$.
5. Für einen beliebigen Testvektor prüfen, dass $B[v]_B=C[v]_C$.

## 9. Checkliste zur Validierung

- [ ] Wurde eine Menge ohne Nullvektor als Untervektorraum bezeichnet?
- [ ] Wurde ein Spann von der Menge selbst unterschieden?
- [ ] Wurden „spannt auf“ und „ist unabhängig“ getrennt geprüft?
- [ ] Entspricht die Zahl der Basisvektoren der bekannten Dimension?
- [ ] Ist die Summe aus Rang und Nullität gleich der Spaltenzahl?
- [ ] Wurden Pivotspalten aus der ursprünglichen Matrix ausgewählt?
- [ ] Wurden Eingabe- und Ausgabebasisrichtung der Koordinatentransformation beschriftet?
- [ ] Wird der tatsächliche Vektor nach der Transformation unverändert rekonstruiert?
- [ ] Wurde die Toleranz der Rangerkennung für numerische Berechnungen erfasst?

## 10. Fallstricke und Grenzen

### Alles mit einer Determinante entscheiden wollen

Die Determinante ist nur für quadratische Matrizen definiert. Bei Fragen zu Unabhängigkeit, Spann und Rang rechteckiger Matrizen sind Zeilenreduktion, QR und SVD allgemeiner.

### Der numerische Rang ist keine exakte ganze Zahl

Bei Gleitkommadaten wird entschieden, ob ein Singulärwert „hinreichend klein“ ist, statt ob er exakt null ist. Da eine Schwellenänderung den geschätzten Rang verändern kann, sollten Skala und Toleranz gemeinsam berichtet werden.

### Annehmen, eine Basis sei eindeutig

Die Dimension ist fest, doch es gibt unendlich viele Basen. Eine gute Basis hängt vom Zweck ab. Eine Orthonormalbasis stabilisiert Berechnungen, eine Eigenbasis vereinfacht Operationen und eine dünn besetzte Basis kann Interpretation und Speicherung erleichtern.

### Endlichdimensionale Intuition überdehnen

In unendlichdimensionalen Räumen wie Funktionenräumen wird eine algebraische Basis von einer analytischen Basis mit Konvergenz unterschieden. Sobald unendliche Summen, Normen und Vollständigkeit auftreten, reicht die Intuition endlicher Matrizen nicht mehr aus.

## Fazit

Der wesentliche Ablauf ist einfach.

$$
\text{Untervektorraum}
\longrightarrow
\text{Spann}
\longrightarrow
\text{lineare Unabhängigkeit}
\longrightarrow
\text{Basis}
\longrightarrow
\text{Dimension und Koordinaten}
$$

Eine Basis ist nicht einfach eine „Liste von Richtungsvektoren“. Sie ist eine **Schnittstelle, die jedes Element eines Raums ohne Redundanz darstellt**. Mit dieser Sichtweise verbinden sich Projektion, kleinste Quadrate, SVD und Dimensionsreduktion in derselben Sprache.
