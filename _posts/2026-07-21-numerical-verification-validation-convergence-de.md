---
title: "V&V für vertrauenswürdige numerische Ergebnisse: Konvergenz, Netz- und Zeitschrittunabhängigkeit sowie Erhaltung"
date: 2026-07-21 09:20:00 +0900
categories: [Scientific Computing, Verification and Validation]
tags: [verification, validation, convergence, mesh-independence, time-step, conservation, numerical-error]
description: Ein praktisches Verfahren, um Code- und Lösungsverifikation von experimenteller Validierung zu unterscheiden und die Zuverlässigkeit numerischer Ergebnisse durch Konvergenz, Netz- und Zeitschrittunabhängigkeit sowie Erhaltung zu bewerten.
math: true
lang: de-DE
translation_key: numerical-verification-validation-convergence
hidden: true
---

{% include language-switcher.html %}

Eine plausible Kontur und eine glatte Kurve sind kein Genauigkeitsnachweis. Damit eine numerische Simulation vertrauenswürdig ist, müssen mindestens folgende Fragen getrennt betrachtet werden.

- Löst der Code die Gleichungen korrekt?
- Sind Diskretisierungs- und iterative Fehler dieser Berechnung ausreichend klein?
- Erklären die gewählten Gleichungen und Eingaben die interessierenden Größen der Realität angemessen?
- Gilt diese Schlussfolgerung innerhalb des Verwendungszwecks und zulässigen Fehlers?

Werden diese Fragen unter dem einzelnen Wort „Verifikation“ zusammengefasst, bleibt unklar, was geprüft wurde und was offen ist. Deshalb werden Verifikation und Validierung unterschieden.

## 1. Grenze zwischen Verifikation und Validierung

| Ebene | Kernfrage | Typischer Nachweis |
|---|---|---|
| Codeverifikation | Wurden die Gleichungen wie beabsichtigt implementiert? | exakte Lösung, hergestellte Lösung, Benchmark, Unit-Test |
| Lösungsverifikation | Wie groß ist der numerische Fehler der aktuellen Berechnung? | iterative Konvergenz, Netz-/Zeitschrittverfeinerung, Fehlerschätzung |
| Validierung | Bildet das Modell reale Zielgrößen für seinen Zweck angemessen ab? | Vergleich mit unabhängigen Messungen, Validierungsunsicherheit, Anwendbarkeit |
| Kalibrierung | Wurden unbekannte Parameter aus Daten geschätzt? | Zielfunktion/Likelihood, Posterior, Identifizierbarkeit |

Kurz gesagt fragt Verifikation ungefähr „Lösen wir die Gleichungen richtig?“, Validierung dagegen „Lösen wir die richtigen Gleichungen?“ Validierung beweist jedoch nicht, dass ein Modell absolut wahr ist. Sie sammelt **Nachweise für einen bestimmten Verwendungszweck, Bedingungsbereich und eine bestimmte Zielgröße**.

Dieselben Daten für Kalibrierung und Validierung zu nutzen heißt, das Modell an bereits gesehenen Daten zu prüfen. Wenn möglich, werden beide getrennt; erfordert begrenzte Datenlage eine Wiederverwendung, wird ausdrücklich angegeben, dass keine unabhängige Validierung vorliegt.

## 2. Zuerst Fehler zerlegen

Die Differenz zwischen Rechenergebnis und Realität vereint mehrere Ursachen.

$$
\text{Gesamtabweichung}
=
\text{Modellformfehler}
+\text{Parameter-/Eingabeunsicherheit}
+\text{Diskretisierungsfehler}
+\text{Iterationsfehler}
+\text{Implementierungsfehler}
+\text{Messfehler}.
$$

Diese Gleichung ist kein strenges probabilistisches Modell aus einfach additiven, unabhängigen Termen, sondern eine konzeptionelle Zerlegung, die das Übersehen von Ursachen verhindern soll. Ursachen können wechselwirken und allein aus Beobachtungen möglicherweise nicht vollständig trennbar sein.

Ein guter V&V-Plan definiert zuerst die Quantity of Interest (QoI). Statt auf das gesamte Feld zu verweisen wird angegeben, welcher Mittelwert, Höchstwert, welches Integral, welche Ankunftszeit oder welcher Randfluss eine Entscheidung informiert. Netzkonvergenz und Validierungsergebnis können je QoI verschieden sein.

## 3. Codeverifikation: Stufe zum Finden von Implementierungsfehlern

### Exakte Lösungen und Benchmarks

Existiert eine analytische Lösung für vereinfachte Randbedingungen oder Geometrie, kann der Rechenfehler direkt verglichen werden. Auch wenn sie von einem komplexen Produktionsfall abweicht, ist sie wertvoll, um die Implementierung von Operatoren, Randbedingungen und Quelltermen isoliert zu testen.

### Method of Manufactured Solutions

Zuerst wird eine gewünschte glatte Funktion \(u_m(x,t)\) gewählt und dann in den Operator \(\mathcal L\) der maßgeblichen Gleichung eingesetzt, um die Quelle

$$
f_m=\mathcal L(u_m)
$$

zu konstruieren. Wird der Code zum Lösen von

$$
\mathcal L(u)=f_m
$$

konfiguriert, kann die bekannte Antwort \(u_m\) inneren Operator, Randbedingungen, Zeitintegration und beobachtete Ordnung gemeinsam testen.

Eine hergestellte Lösung muss kein reales Phänomen darstellen. Sie sollte stattdessen folgende Bedingungen erfüllen.

- Sie aktiviert alle wichtigen Terme des Codepfads.
- Sie verdeckt Fehler nicht durch übermäßige Symmetrie.
- Sie besitzt die erforderliche Differenzierbarkeit.
- Ihre Randbedingungen und Quelle sind konsistent hergeleitet.

### Unabhängige Implementierungen und Grenzfälle

Dass verschiedene Codes dieselbe Antwort erzeugen ist ein nützlicher Nachweis, doch sie können gemeinsame Annahmen oder Fehler teilen. Das Ergebnis wird mit anderen Nachweisarten wie Grenzfällen eines gegen null gehenden Terms, Symmetrie, Dimensionsanalyse und Erhaltungsgesetzen verbunden.

## 4. Lösungsverifikation: numerischer Fehler der aktuellen Berechnung

### Iterativen Fehler vom Diskretisierungsfehler trennen

Das Netz zu ändern, bevor ein nichtlinearer oder linearer Solver ausreichend konvergiert ist, vermischt iterativen und Diskretisierungsfehler. Auf jedem Netz wird die Residuums-Toleranz ausreichend kleiner als die Diskretisierungsdifferenz gemacht und neben dem Residuum auch die Stabilität der QoI geprüft.

Ein sinkendes algebraisches Residuum garantiert nicht zwingend einen sinkenden Lösungsfehler. In einem schlecht konditionierten System können kleines Residuum und großer Lösungsfehler gleichzeitig bestehen.

### Asymptotischer Konvergenzbereich

Ist die Netzweite \(h\) und die theoretische Ordnung \(p\), wird in einem ausreichend feinen Bereich erwartet:

$$
\phi(h)=\phi_0+Ch^p+\mathcal O(h^{p+1})
$$

wobei \(\phi\) eine QoI ist. Bei konstantem Verfeinerungsverhältnis und

$$
h_3=rh_2=r^2h_1,\qquad r>1
$$

mit \(h_1\) als feinster Weite kann die beobachtete Ordnung geschätzt werden als

$$
p_{\mathrm{obs}}
=
\frac{
\ln\left|
(\phi_3-\phi_2)/(\phi_2-\phi_1)
\right|
}{
\ln r
}
$$

Liegt die Folge im asymptotischen Bereich und konvergiert monoton, ergibt Richardson-Extrapolation

$$
\phi_{\mathrm{ext}}
=
\phi_1+
\frac{\phi_1-\phi_2}{r^{p_{\mathrm{obs}}}-1}
$$

Diese Formel wird instabil, wenn die drei Werte oszillatorisch konvergieren oder ihre Differenzen auf Rauschniveau liegen. Statt bedingungslos eine einzelne scheinbare Ordnung zu berichten, werden zunächst Konvergenzmuster und Erfüllung der Annahmen angegeben.

## 5. Warum die Formulierung „netzunabhängig“ Vorsicht verlangt

Diskretisierungsfehler ist auf einem endlichen Netz selten exakt null. Daher werden besser folgende Details berichtet, statt nur „Unabhängigkeit“ zu behaupten.

- Verfeinerungsfamilie und verwendetes charakteristisches \(h\)
- Verfeinerungsverhältnis
- Zell-/DOF-Größe jedes Netzes
- Netzqualität und Grenzschichtauflösung
- Werte und relative Änderungen jeder QoI
- beobachtete Ordnung oder Fehlerschätzung
- Akzeptanzkriterium zur Wahl des endgültigen Netzes

Dass Werte zweier Netze ähnlich sind genügt nicht. Zufällige Fehlerauslöschung, nichtmonotone Konvergenz oder derselbe Auflösungsengpass können vorliegen. Wenn möglich, werden mindestens drei Stufen eingesetzt und es wird geprüft, dass die Netze eine systematische Verfeinerungsfamilie mit gleicher Topologie und Streckungsregel bilden.

### Lokale und integrale Größen konvergieren verschieden

Ein Gebietsmittel oder Integralfluss kann stabil sein, während Punkthöchstwert, Gradient oder Diskontinuitätsposition langsam konvergieren. Für jede berichtete QoI wird eine eigene Netzstudie durchgeführt. Verschiebt sich der „Ort des Maximums“ zwischen Netzen, werden Werte am selben Zellindex nicht direkt verglichen.

## 6. Zeitschrittunabhängigkeit und Kopplung räumlicher sowie zeitlicher Fehler

Eine Verfeinerungsstudie kann auch für den Zeitschritt \(\Delta t\) in der Form

$$
\phi(\Delta t)=\phi_0+C_t(\Delta t)^q+\cdots
$$

durchgeführt werden. Ist jedoch der räumliche Fehler groß, kann eine Zeitschrittverringerung keine sichtbare Änderung erzeugen, und umgekehrt.

Praktische Reihenfolge:

1. Räumliche Verfeinerung mit ausreichend kleinem \(\Delta t\) bewerten.
2. \(\Delta t\)-Verfeinerung auf dem gewählten feinen Netz bewerten.
3. Um die endgültige Kombination Netz und \(\Delta t\) gemeinsam variieren, um ihre Wechselwirkung zu prüfen.
4. Bei adaptiven Zeitschritten Toleranzen, Historie akzeptierter Schritte und abgelehnte Schritte statt eines einzelnen nominellen Schritts erfassen.

Eine Stabilitätsbedingung zu erfüllen ist nicht dasselbe wie ausreichende Genauigkeit. Dass ein implizites Verfahren bei großem Zeitschritt nicht divergiert bedeutet nicht, dass Transientenphase und Spitzenzeit genau aufgelöst sind.

## 7. Erhaltung: starker Nachweis unabhängig von einem Konvergenzplot

Für ein Kontrollvolumen \(\Omega\) in einem konservativen Problem lautet eine allgemeine Bilanz

$$
\frac{d}{dt}\int_{\Omega}U\,d\Omega
+
\int_{\partial\Omega}F\cdot n\,dS
=
\int_{\Omega}S\,d\Omega
$$

Für eine diskrete Berechnung über ein festes Zeitintervall wird berechnet:

$$
\Delta \text{Speicheränderung}
+\text{Nettoabfluss}
-\text{Quelle}
=
\text{Bilanzdefekt}
$$

Nur den absoluten Defekt zu berichten erschwert Vergleiche zwischen Fällen verschiedener Skalen. Zusätzlich wird ein normalisierter Bilanzfehler betrachtet, geteilt durch einen repräsentativen Fluss oder eine Speicheränderung. Liegt der Nenner nahe null, explodiert der relative Fehler; absoluter Wert und Skala werden dann gemeinsam dargestellt.

Erhaltung ist notwendig, aber nicht hinreichend. Globale Erhaltung kann auch gelten, wenn dieselbe Gesamtmenge falsch räumlich verteilt ist. Daher werden folgende Ebenen unterschieden.

- lokale Zellbilanz
- Flussbilanz je Rand
- globale Gebietsbilanz
- Bilanz je Spezies oder Komponente
- gekoppelte Bilanzen wie Energie, Masse und Impuls

## 8. Validierungsvergleiche entwerfen

### Validierungsmetriken vorab definieren

Nicht einen Plot ansehen und als „ähnlich“ beurteilen, sondern QoI und Metrik zuerst definieren. Beispiele:

- Bias und normalisierter Fehler
- Profilnorm
- Größe und Ort der Spitze
- Integralgröße
- zeitlicher Phasenfehler
- Coverage oder probabilistischer Score

### Unsicherheiten kombinieren

Bei der Interpretation der Simulations-Mess-Differenz

$$
E=S-D
$$

werden numerische Unsicherheit der Simulation, Eingabeunsicherheit und Messunsicherheit gemeinsam berücksichtigt. Ein kleines \(|E|\) beweist allein keine Modellkorrektheit; ebenso ist zu prüfen, ob ein sehr breites Unsicherheitsband die Differenz nur verdeckt.

### Validierungsdomäne angeben

Extrapolation über den Bereich validierter Bedingungen hinaus schwächt die Nachweise. Eingaberaum, Randregime, dimensionslose Gruppen und Material-/Zustandsbereiche werden erfasst und der Abstand des Vorhersagepunkts von der Validierungsdomäne bewertet.

## 9. Empfohlener V&V-Workflow

1. **Verwendungszweck und zulässigen Fehler definieren**: angeben, welche QoIs welche Entscheidungen informieren.
2. **Modellhierarchie aufbauen**: maßgebliche Gleichungen, Abschlüsse, Rand- und Anfangsbedingungen sowie Parameterquellen unterscheiden.
3. **Codeverifikation**: Implementierung mit Unit-Tests, exakten Lösungen oder MMS, Grenzfällen und Benchmarks testen.
4. **Iterative Konvergenz**: Gleichungsresiduen und QoI-Verläufe gemeinsam untersuchen.
5. **Räumliche Verfeinerung**: mindestens drei Stufen einer systematischen Netzfamilie vergleichen.
6. **Zeitliche Verfeinerung**: zeitliche QoIs, Phase und Spitzenzeit einbeziehen.
7. **Erhaltungsprüfungen**: lokale, randbezogene und globale Bilanzen automatisch berechnen.
8. **Eingabeunsicherheit fortpflanzen**: Eingabeunsicherheit im Validierungsvergleich abbilden.
9. **Unabhängige Validierung**: mit vorab definierten Metriken gegen nicht zur Kalibrierung verwendete Daten vergleichen.
10. **Anwendungsbereich und Grenzen erfassen**: nicht validierte Regime und dominante Unsicherheiten benennen.

## 10. Prüfliste zur Verifikation

- [ ] Wurden Verifikation, Validierung und Kalibrierung unterschieden?
- [ ] Wurden für Entscheidungen verwendete QoIs und Toleranzen zuerst definiert?
- [ ] Aktiviert der analytische/MMS-Test die Hauptterme des Produktionscodes?
- [ ] Ist der iterative Fehler ausreichend kleiner als die Differenzen zwischen Netzen?
- [ ] Wurden mindestens drei Stufen systematischer Verfeinerung verwendet?
- [ ] Wurde neben theoretischer auch beobachtete Ordnung geprüft?
- [ ] Wurden monotone, oszillatorische und divergente Konvergenz unterschieden?
- [ ] Wurden räumliche und zeitliche Verfeinerung getrennt durchgeführt?
- [ ] Wurden neben globaler auch lokale und randbezogene Erhaltung geprüft?
- [ ] Wurden Kalibrierungs- und Validierungsdaten getrennt?
- [ ] Wurden Mess-, Eingabe- und numerische Unsicherheit gemeinsam berichtet?
- [ ] Wurde Extrapolation außerhalb der Validierungsdomäne gekennzeichnet?

## 11. Häufige Fallstricke

### Aus kleinem Residuum auf eine korrekte Antwort schließen

Ein Residuum sagt nur, wie gut die diskreten algebraischen Gleichungen gelöst wurden; weder Diskretisierungs- noch Modellformfehler werden sichtbar.

### Nur zwei Netze vergleichen und Unabhängigkeit erklären

Zufällige Übereinstimmung zweier Werte begründet weder Konvergenzordnung noch asymptotischen Bereich. Mindestens drei Stufen und das Konvergenzmuster sind nötig.

### Jedes Feld mit einer einzigen Metrik bewerten

Selbst wenn der Mittelwert gut übereinstimmt, können Spitze, Gradient oder Phase falsch sein. Mehrere dem Verwendungszweck entsprechende QoIs sind erforderlich.

### Kalibrierungsleistung als Validierungsleistung berichten

Die Anpassung an zur Parameterabstimmung verwendete Daten ist ein Kalibrierungsergebnis. Zur Beurteilung der Vorhersageangemessenheit wird unabhängige Information benötigt.

### Annehmen, ein feineres Netz sei immer genauer

Bei falschen Randbedingungen, lockerer iterativer Toleranz, schlechter Netzqualität oder instabilem Schema garantiert eine Erhöhung der DOF allein keine Genauigkeit.

## 12. Einschränkungen und Berichtsgrundsätze

Bei komplexen nichtlinearen und mehrskaligen Problemen ist ein sauberer asymptotischer Bereich möglicherweise unerreichbar. Diskontinuitäten, bewegte Schnittstellen, chaotische Dynamik und adaptive Netze schwächen die Annahmen einfacher Richardson-Analyse. Statt in solchen Fällen eine einzelne „exakte Fehlerschätzung“ zu erzwingen, wird transparent berichtet, wie stabil die Schlussfolgerung über mehrere Auflösungen ist, welche Fehlerquelle dominiert und was nicht verifiziert werden konnte.

Das Produkt von V&V ist kein Bestanden-Stempel. Es ist **ein Nachweisnetz, das eine Schlussfolgerung stützt**. Deshalb sind Solver-Toleranzen, Verfeinerungsfamilien, Bilanzdefekte, Unsicherheiten und Anwendungsbereiche wichtiger als Plots.
