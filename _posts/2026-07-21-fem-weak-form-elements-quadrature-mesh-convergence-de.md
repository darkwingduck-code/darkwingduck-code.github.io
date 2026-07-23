---
title: "Das Rückgrat der Finite-Elemente-Methode: schwache Formen, Elemente, Quadratur und Netzkonvergenz"
date: 2026-07-21 12:43:00 +0900
categories: [Scientific Computing, Finite Element Method]
tags: [fem, weak-form, galerkin, finite-element, quadrature, mesh-convergence]
description: "Die Kernstruktur der FEM verbinden – von der Herleitung der schwachen aus der starken Form über Funktionenräume, Randbedingungen, Elementinterpolation, Quadratur und Assemblierung bis zu linearen Lösern und Netzkonvergenz."
math: true
mermaid: true
lang: de-DE
translation_key: fem-weak-form-elements-quadrature-mesh-convergence
hidden: true
---

{% include language-switcher.html %}

Die Finite-Elemente-Methode (FEM) ist mehr als ein Verfahren, eine Geometrie in kleine Teile zu zerlegen.
Sie transformiert eine Differentialgleichung in eine integrierbare schwache Form und projiziert ein Problem aus einem unendlichdimensionalen Funktionenraum auf einen endlichdimensionalen Unterraum.
Ist diese Perspektive klar, verbinden sich Elementtypen und Solver-Optionen über eine einzige mathematische Struktur.

## 1. Mit der starken Form beginnen

Betrachten wir das Poisson-Problem.

$$
-\nabla\cdot(k\nabla u)=f \quad \text{in }\Omega,
$$

$$
u=g_D \quad \text{auf }\Gamma_D,
\qquad
-k\nabla u\cdot n=g_N \quad \text{auf }\Gamma_N.
$$

Die starke Form verlangt, dass \(u\) punktweise hinreichend differenzierbar ist und Gleichung sowie Randbedingungen punktweise erfüllt.
Bei komplexen Koeffizienten, diskontinuierlichen Materialien und nicht glatten Gebieten kann diese Forderung zu streng sein.

## 2. Testfunktionen und partielle Integration

Mit einer Testfunktion \(v\), die am Dirichlet-Rand null ist, multiplizieren und integrieren.

$$
\int_\Omega -v\nabla\cdot(k\nabla u)\,d\Omega
=\int_\Omega vf\,d\Omega.
$$

Partielle Integration beziehungsweise die Greensche Identität ergibt

$$
\int_\Omega k\nabla v\cdot\nabla u\,d\Omega
-\int_{\partial\Omega}v k\nabla u\cdot n\,d\Gamma
=\int_\Omega vf\,d\Omega.
$$

Einsetzen der Neumann-Bedingung liefert die schwache Form

$$
a(u,v)=\ell(v)
$$

mit

$$
a(u,v)=\int_\Omega k\nabla v\cdot\nabla u\,d\Omega,
$$

$$
\ell(v)=\int_\Omega vf\,d\Omega+\int_{\Gamma_N}vg_N\,d\Gamma
$$

Die Ableitungsordnung von \(u\) ist von zwei auf eins gesunken, und die natürliche Randbedingung ist als Randintegral eingegangen.

## 3. Wesentliche und natürliche Randbedingungen

- Eine Dirichlet-Bedingung beschränkt den Ansatzraum selbst und heißt daher wesentliche Bedingung.
- Eine Neumann-Bedingung erscheint natürlich auf der rechten Seite der schwachen Form und heißt daher natürliche Bedingung.

Diese Unterscheidung ist auch für die Implementierung wichtig.
Werden Dirichlet-Freiheitsgrade aus der Matrix eliminiert oder als Beschränkungen behandelt, müssen Symmetrie und Berechnung der Reaktionskräfte bewahrt werden.

Ein reines Neumann-Problem besitzt einen Nullraum, weil auch jede um eine Konstante verschobene Lösung möglich ist.
Es verlangt die Kompatibilitätsbedingung

$$
\int_\Omega f\,d\Omega+\int_{\Gamma_N}g_N\,d\Gamma=0
$$

und eine Mittelwertbeschränkung oder Referenz.

## 4. Bedeutung der Funktionenräume

Der natürliche Raum des Poisson-Problems ist der Sobolev-Raum \(H^1(\Omega)\).

$$
H^1(\Omega)=
\{v\in L^2(\Omega):\nabla v\in[L^2(\Omega)]^d\}.
$$

Funktion und erste schwache Ableitung müssen also lediglich quadratintegrierbar sein.
Die zentrale Anforderung ist eine integrierbare Energienorm, nicht punktweise Glattheit.

Die Galerkin-FEM verwendet für Ansatz- und Testraum denselben endlichdimensionalen Unterraum.

$$
V_h=\mathrm{span}\{N_1,\ldots,N_n\}.
$$

## 5. Elementinterpolation und Freiheitsgrade

Die angenäherte Lösung wird dargestellt als

$$
u_h(\mathbf x)=\sum_{j=1}^{n}N_j(\mathbf x)U_j
$$

Jedes \(N_j\) ist eine Formfunktion, jedes \(U_j\) ein Knotenwert oder verallgemeinerter Freiheitsgrad.

Wird jede Basisfunktion \(N_i\) als Testfunktion eingesetzt, ergeben sich

$$
K_{ij}=\int_\Omega k\nabla N_i\cdot\nabla N_j\,d\Omega,
\qquad
F_i=\ell(N_i)
$$

und das globale System wird zu

$$
\mathbf K\mathbf U=\mathbf F
$$

## 6. Referenzelement und Abbildung

Das physikalische Element \(\Omega_e\) wird vom Referenzelement \(\hat\Omega\) abgebildet.

$$
\mathbf x(\boldsymbol\xi)=
\sum_a N_a(\boldsymbol\xi)\mathbf x_a.
$$

Die Jacobi-Matrix lautet

$$
J=\frac{\partial\mathbf x}{\partial\boldsymbol\xi}
$$

und transformiert sowohl Gradient als auch Volumenelement.

$$
\nabla_x N=J^{-T}\nabla_\xi N,
\qquad
d\Omega=|\det J|d\hat\Omega.
$$

Ein Element mit \(\det J\le0\) ist invertiert oder degeneriert.
Ein kleiner Determinantenwert und eine große Konditionszahl verschlechtern Gradientenberechnung und Konditionierung der Steifigkeit.

## 7. Quadratur ist Teil des Modells

Das Elementintegral wird durch Quadratur angenähert.

$$
\int_{\hat\Omega}g(\xi)d\xi
\approx
\sum_{q=1}^{n_q}w_q g(\xi_q).
$$

Ist die Integrationsordnung zu niedrig, werden Steifigkeit und innere Kräfte möglicherweise ungenau aufgebaut; Hourglass- oder Nullenergiemoden können entstehen.
Übermäßige Quadratur erhöht dagegen womöglich nur die Kosten, ohne Locking zu beheben.

### Reduzierte und selektive Integration

Reduzierte Integration kann Locking mindern, birgt aber die Gefahr unechter Moden.
Es ist zu prüfen, dass die Stabilisierung die physikalische Energie nicht verfälscht.

### Nichtlineare Materialien und Quadraturpunkte

Interne Zustandsvariablen werden gewöhnlich an Quadraturpunkten aktualisiert.
Eine konsistente Tangente kann die Newton-Konvergenz stark verbessern.
Konsistenz zwischen Zustandsaktualisierung, Rollback und Wiederholung eines Lastschritts ist wichtig.

## 8. Assemblierung ist eine lokale-zu-globale Erhaltungskonvention

Jede Elementmatrix \(\mathbf K^e\) und jeder Vektor \(\mathbf F^e\) werden mithilfe der Freiheitsgradzuordnung in das globale System addiert.

```mermaid
flowchart LR
  A[Referenzelement] --> B[Geometrieabbildung]
  B --> C[Auswertung am Quadraturpunkt]
  C --> D[Elementmatrix/-vektor]
  D --> E[Lokale-zu-globale Assemblierung]
  E --> F[Beschränkungen und Randterme]
  F --> G[Lineare/nichtlineare Lösung]
  G --> H[Fehler- und Bilanzprüfungen]
```

Die Freiheitsgrade eines gemeinsam genutzten Knotens vereinen Beiträge benachbarter Elemente.
Bei Kanten- oder Flächenelementen mit Vorzeichen und Orientierungen ist die lokale Orientierung an der globalen Konvention auszurichten.

## 9. Konformität, Stabilität und Locking

Eine Erhöhung der Polynomordnung allein löst nicht jedes Problem.

- **Konformität**: Erfüllt der Approximationsraum die geforderte Stetigkeit?
- **Koerzivität/Inf-sup-Stabilität**: Ist das diskrete Problem stabil?
- **Locking**: Wird die Formulierung bei dünnen Strukturen oder nahezu inkompressiblen Bedingungen übermäßig steif?
- **Unechter Modus**: Gibt es einen Modus, der sich ohne physikalische Energie verformt?

In gemischten Problemen muss die Kombination der Verschiebungs- und Druckräume die Inf-sup-Bedingung erfüllen.
Eine bedingungslose Interpolation gleicher Ordnung kann Druckoszillationen erzeugen.

## 10. h-, p- und hp-Verfeinerung

- h-Verfeinerung: Elementgröße verringern.
- p-Verfeinerung: Basisordnung erhöhen.
- hp-Verfeinerung: Beides entsprechend der Glattheit kombinieren.

Bei ausreichender Regularität besitzt ein typischer Fehler in der Energienorm die Form

$$
\|u-u_h\|_{H^1}\le C h^p|u|_{H^{p+1}}
$$

Bei Ecksingularitäten, diskontinuierlichen Koeffizienten oder Kontakt kann geringe Regularität verhindern, dass die nominelle Ordnung auftritt.

## 11. A-priori- und A-posteriori-Fehler

Eine A-priori-Schätzung erklärt die Konvergenzrate mit Lösungsregularität und Netzweite.
Ein A-posteriori-Schätzer nutzt Residuen und Sprünge der berechneten Lösung, um Verfeinerungsorte zu bestimmen.

Ein konzeptioneller Residuenschätzer kombiniert Elementresiduum \(R_e\) und Flusssprung zwischen Elementen \(J_f\), etwa als

$$
\eta^2=\sum_e h_e^2\|R_e\|^2
+\sum_f h_f\|J_f\|^2
$$

An Benchmarks wird geprüft, dass der Effektivitätsindex über die Problemfamilie stabil ist.

## 12. Nichtlineare Probleme und Newton-Verfahren

Ist der Residuenvektor \(\mathbf R(\mathbf U)=0\), lautet der Newton-Schritt

$$
\mathbf J(\mathbf U^k)\Delta\mathbf U
=-\mathbf R(\mathbf U^k),
$$

$$
\mathbf U^{k+1}=\mathbf U^k+\alpha\Delta\mathbf U
$$

Eine konsistente Jacobi-Matrix, Line Search, Steuerung von Last- oder Zeitinkrementen und Zustands-Rollback bestimmen die Robustheit.

## 13. Empfohlener Workflow

1. Starke Form, Gebiet und Randaufteilung angeben.
2. Mit einer Testfunktion multiplizieren und die schwache Form durch partielle Integration von Hand herleiten.
3. Ansatz- und Testräume sowie wesentliche Beschränkungen definieren.
4. Referenzelement, Abbildung und Formfunktionen verifizieren.
5. Quadraturordnung an Integrand und Nichtlinearität anpassen.
6. Patch-Test auf Elementebene und Test mit hergestellter Lösung durchführen.
7. Globale Bilanz, Reaktionskräfte und Energie prüfen.
8. Systematische Verfeinerung auf mindestens drei Stufen durchführen.
9. Konvergenz und Fehlerschätzer für jede QoI berichten.

## 14. Prüfliste zur Verifikation

- [ ] Das Vorzeichen des Randterms der schwachen Form wurde neu hergeleitet.
- [ ] Wesentliche und natürliche Randbedingungen wurden unterschieden.
- [ ] Nullraum und Kompatibilität des reinen Neumann-Problems wurden behandelt.
- [ ] Richtung der Jacobi-Abbildung vom Referenz- zum physikalischen Element ist konsistent.
- [ ] Jede Elementdeterminante ist positiv und ausreichend groß.
- [ ] Starrkörpermoden und erwarteter Nullraum wurden geprüft.
- [ ] Patch-Test und Konstantzustandstest bestanden.
- [ ] Empfindlichkeit gegenüber der Quadraturordnung wurde evaluiert.
- [ ] Summe von Reaktions- und äußeren Kräften ist im Gleichgewicht.
- [ ] Verzerrungsenergie und Arbeit sind konsistent.
- [ ] Beobachtete Ordnung wurde unter h- oder p-Verfeinerung berechnet.
- [ ] Ein Wert an einer Punktsingularität wird nicht als konvergierte QoI berichtet.

## 15. Häufige Fehlermuster und Einschränkungen

### Nur das Netz feiner machen

Verzerrte Elemente hinzuzufügen oder an einer Singularität nur gleichmäßig zu verfeinern liefert für die Kosten wenig Nutzen.

### Eine glatte Kontur für genau halten

Nachbearbeitung mit Knotenmittlelung kann diskontinuierliche Spannung glatt erscheinen lassen.
Die ursprünglichen Quadraturpunktwerte und das Gleichgewicht sind zu prüfen.

### Reduzierte Integration als universelles Mittel verwenden

Sie kann Locking verringern, aber Hourglass-Moden einführen.
Stabilisierungsenergie und Netzempfindlichkeit werden gemeinsam untersucht.

### Solver-Toleranz mit Diskretisierungsfehler verwechseln

Der Netzfehler kann trotz kleinem linearen Residuum groß bleiben.
Umgekehrt verfälscht ein großer algebraischer Fehler den Vergleich von Netzverfeinerungen und die beobachtete Ordnung.

### Nur die Maximalspannung an einem bestimmten Punkt vergleichen

Punktspannung kann an einer einspringenden Ecke oder konzentrierten Last divergieren.
Eine wohldefinierte QoI wie Integral, Mittelwert oder Bruchparameter ist zu wählen.

## 16. Offizielle und primäre Referenzen

- Galerkin, B. G., „Series Solution of Some Problems of Elastic Equilibrium“, 1915.
- Courant, R., „Variational Methods for the Solution of Problems of Equilibrium and Vibrations“, 1943.
- Ciarlet, P. G., *The Finite Element Method for Elliptic Problems*.
- NIST, [Dokumentation zur OOF-Finite-Elemente-Analyse](https://www.ctcms.nist.gov/oof/oof2/).
- PETSc, [Schnittstellen für finite Elemente und Diskretisierung](https://petsc.org/release/manual/dmplex/).
- The FEniCS Project, [Offizielle Dokumentation](https://docs.fenicsproject.org/).

Das Herz der FEM ist nicht die Form ihrer Elemente, sondern die Frage, **ob schwache Form, Funktionenräume, Quadratur, Assemblierung und Fehlerschätzung ein einziges konsistentes Approximationsproblem bilden**.
