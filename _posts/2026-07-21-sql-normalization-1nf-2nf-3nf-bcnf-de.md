---
title: "Prinzipien und praktische Abwägungen der SQL-Normalisierung: 1NF, 2NF, 3NF und BCNF"
date: 2026-07-21 09:50:00 +0900
categories: [Data Engineering, Database Design]
tags: [sql, normalization, 1nf, 2nf, 3nf, bcnf, functional-dependency, data-modeling]
description: "Ausgehend von funktionalen Abhängigkeiten und Kandidatenschlüsseln erklärt dieser Leitfaden die Beurteilung von 1NF, 2NF, 3NF und BCNF sowie praktische Kriterien für verlustfreie Zerlegung, Abhängigkeitserhaltung und Denormalisierung."
math: true
lang: de-DE
hidden: true
translation_key: sql-normalization-1nf-2nf-3nf-bcnf
---

{% include language-switcher.html %}

Normalisierung ist keine Regel, nach der eine Tabelle in möglichst viele Teile zerlegt werden soll. Ihr Kern besteht darin, **jede Tatsache an genau einer Stelle zu verwalten und dadurch Änderungsanomalien zu verringern**. Für eine korrekte Anwendung werden zuerst die funktionalen Abhängigkeiten – also die Geschäftsregeln – notiert, statt lediglich die Spaltennamen zu betrachten.

Dieser Artikel beurteilt Normalformen in der folgenden Reihenfolge.

$$
\text{Geschäftsregeln}
\rightarrow
\text{Funktionale Abhängigkeiten}
\rightarrow
\text{Kandidatenschlüssel}
\rightarrow
\text{Normalformen}
\rightarrow
\text{Verlustfreie, abhängigkeitserhaltende Zerlegung}
$$

## 1. Die drei Anomalien, die Normalisierung verhindert

Werden unterschiedliche Tatsachen redundant in einer Relation gespeichert, entstehen folgende Probleme.

- **Änderungsanomalie**: Dieselbe Tatsache steht in mehreren Zeilen, aber nur einige davon werden aktualisiert.
- **Einfügeanomalie**: Eine eigenständige Tatsache kann erst erfasst werden, wenn gleichzeitig eine andere Tatsache vorliegt.
- **Löschanomalie**: Beim Löschen einer Zeile verschwindet zugleich die einzige Ausprägung einer anderen Tatsache.

Wird etwa der Anzeigename eines Kunden in jeder Bestellzeile wiederholt, müssen bei einer Namensänderung sämtliche historischen Zeilen geändert werden. Soll dagegen der „Anzeigename zum Zeitpunkt der Bestellung“ erhalten bleiben, kann die Wiederholung ein beabsichtigter Schnappschuss und keine Redundanz sein. Ob normalisiert werden sollte, hängt nicht von der Form einer Spalte ab, sondern davon, **ob ihr Wert eine gegenwärtige oder eine historische Tatsache darstellt**.

## 2. Funktionale Abhängigkeiten: Regeln, keine Daten

Für Attributmengen \(X,Y\) in einer Relation \(R\) bedeutet

$$
X\to Y
$$

dass zwei beliebige Tupel mit demselben Wert für \(X\) stets auch denselben Wert für \(Y\) besitzen müssen. \(X\) bestimmt \(Y\) funktional.

Wichtig ist: Eine funktionale Abhängigkeit entsteht nicht schon deshalb, weil die aktuelle Stichprobe zufällig keine Duplikate enthält. Sie muss eine Geschäftsregel sein, die für alle künftig zulässigen Daten gilt.

### Triviale Abhängigkeit

Gilt \(Y\subseteq X\), ist \(X\to Y\) trivial. Zum Beispiel gilt

$$
\{A,B\}\to A
$$

unabhängig von der Bedeutung der Werte immer.

### Abschluss

Der Abschluss \(X^+\) einer Attributmenge \(X\) umfasst alle Attribute, die \(X\) unter den gegebenen funktionalen Abhängigkeiten bestimmen kann. Mithilfe des Abschlusses werden Kandidatenschlüssel ermittelt.

1. Beginne mit \(X^+=X\).
2. Füge für jedes \(Y\to Z\), bei dem \(Y\subseteq X^+\) gilt, \(Z\) zu \(X^+\) hinzu.
3. Wiederhole dies, bis sich die Menge nicht mehr ändert.
4. Gilt \(X^+=R\), ist \(X\) ein Superschlüssel.
5. Ist keine echte Teilmenge von \(X\) ein Superschlüssel, ist \(X\) ein Kandidatenschlüssel.

## 3. Schlüsselbegriffe genau unterscheiden

- **Superschlüssel**: Eine Attributmenge, die eine Zeile eindeutig identifiziert. Sie darf überflüssige Attribute enthalten.
- **Kandidatenschlüssel**: Ein minimaler Superschlüssel, der sich nicht weiter verkleinern lässt.
- **Primärschlüssel**: Der Kandidatenschlüssel, der in der Implementierung als repräsentativer Schlüssel gewählt wurde.
- **Alternativschlüssel**: Jeder Kandidatenschlüssel, der nicht als Primärschlüssel ausgewählt wurde.
- **Primattribut**: Ein Attribut, das in mindestens einem Kandidatenschlüssel enthalten ist.
- **Fremdschlüssel**: Ein Attribut, das auf einen Kandidaten- oder Eindeutigkeitsschlüssel einer anderen Relation verweist.

Das Hinzufügen einer automatisch hochgezählten ID als Primärschlüssel beseitigt weder die ursprünglichen fachlichen Kandidatenschlüssel noch die funktionalen Abhängigkeiten. Ein natürlicher Schlüssel, der keine Duplikate enthalten darf, benötigt weiterhin eine eigene `UNIQUE`-Bedingung.

## 4. 1NF: ein Wert je Attributposition einer Relation

Die erste Normalform folgt dem relationalen Prinzip, dass jede Schnittstelle von Tupel und Attribut genau einen Wert aus der jeweiligen Domäne enthält. Sich wiederholende Spalten und Listen variabler Länge in einer einzelnen Zelle werden üblicherweise in eigene Relationen ausgelagert.

Fehlerhafte Form:

| item_id | labels |
|---|---|
| eine Kennung | mehrere kommagetrennte Bezeichnungen |

Normalisierte Form:

~~~sql
CREATE TABLE item (
    item_id BIGINT PRIMARY KEY
);

CREATE TABLE label (
    label_id BIGINT PRIMARY KEY,
    label_name TEXT NOT NULL UNIQUE
);

CREATE TABLE item_label (
    item_id BIGINT NOT NULL REFERENCES item(item_id),
    label_id BIGINT NOT NULL REFERENCES label(label_id),
    PRIMARY KEY (item_id, label_id)
);
~~~

### „Atomar“ bezieht sich auf die Abfragesemantik, nicht auf die Größe des Datentyps

Ein Datum muss für die 1NF nicht in Jahr, Monat und Tag aufgespalten werden. Wird eine Datumsdomäne als ein Wert behandelt, ist eine Datumsspalte atomar. Umgekehrt verletzt eine vollständige Adresse als Zeichenkette nicht zwingend die 1NF; sind jedoch Suche und Validierung nach Ort erforderlich, ist eine getrennte Struktur geeigneter.

Statt JSON- oder Array-Typen pauschal als Verstoß gegen die 1NF zu bezeichnen, sollten folgende Fragen gestellt werden:

- Müssen die enthaltenen Elemente an relationalen Bedingungen und Joins teilnehmen?
- Werden einzelne Elemente unabhängig voneinander aktualisiert?
- Muss die Datenbank Regeln zu Kardinalität und Duplikaten durchsetzen?
- Handelt es sich um eine externe Nutzlast, die eine Schemaentwicklung benötigt?

## 5. 2NF: Tatsachen entfernen, die nur von einem Teil eines zusammengesetzten Kandidatenschlüssels abhängen

Die zweite Normalform verlangt, dass eine Relation:

1. in der 1NF ist und
2. kein Nicht-Primattribut funktional von einer echten Teilmenge irgendeines Kandidatenschlüssels abhängt.

Sie beseitigt also partielle Abhängigkeiten. Besteht jeder Kandidatenschlüssel aus nur einem Attribut, kann kein Verstoß gegen die 2NF auftreten.

Betrachten wir folgende Relation.

~~~text
order_line(
  order_id,
  product_id,
  order_time,
  customer_id,
  customer_name,
  product_name,
  quantity,
  agreed_unit_price
)
~~~

Darf ein Produkt in einer Bestellung nur einmal vorkommen, ist \((order\_id, product\_id)\) der Kandidatenschlüssel. Nehmen wir folgende Geschäftsregeln an:

$$
order\_id\to order\_time, customer\_id
$$

$$
product\_id\to product\_name
$$

$$
(order\_id,product\_id)
\to quantity,agreed\_unit\_price.
$$

`order_time` und `customer_id` hängen nur von `order_id`, also einem Schlüsselteil, ab; `product_name` hängt nur von `product_id` ab. Diese Abhängigkeiten verletzen die 2NF.

Die Relation wird zerlegt in:

- order_header(order_id, order_time, customer_id)
- product(product_id, product_name)
- order_line(order_id, product_id, quantity, agreed_unit_price)

Der vereinbarte Stückpreis ist hier der für diese Bestellposition vereinbarte Preis und nicht der aktuelle Produktpreis; er hängt daher vom gesamten zusammengesetzten Schlüssel ab. Ihn allein aufgrund ähnlich klingender Namen in die Produktrelation zu verschieben, würde die historische Tatsache zerstören.

## 6. 3NF: indirekte Abhängigkeiten über Nichtschlüsselattribute entfernen

Die Intuition hinter der dritten Normalform lautet, dass ein Nichtschlüsselattribut nicht indirekt über ein anderes Nichtschlüsselattribut bestimmt werden soll.

Gilt im vorigen Beispiel

$$
order\_id\to customer\_id
$$

und

$$
customer\_id\to customer\_name
$$

entsteht die transitive Abhängigkeit

$$
order\_id\to customer\_name
$$

Den aktuellen Namen des Kunden in jeder Bestellung zu speichern, verursacht eine Änderungsanomalie. Daher wird zerlegt in:

- customer(customer_id, current_name)
- order_header(order_id, order_time, customer_id)

### Das genaue Kriterium der 3NF

Eine Relation ist in der 3NF, wenn für jede nichttriviale funktionale Abhängigkeit \(X\to A\) mindestens eine der folgenden Aussagen gilt:

1. \(X\) ist ein Superschlüssel.
2. \(A\) ist ein Primattribut.

Diese Definition ist für Relationen mit mehreren Kandidatenschlüsseln präziser als der Merksatz „Bestimmt ein Nichtschlüssel einen Nichtschlüssel, liegt immer ein Verstoß vor“.

## 7. BCNF: Jede Determinante ist ein Superschlüssel

Die Boyce-Codd-Normalform verlangt für jede nichttriviale funktionale Abhängigkeit \(X\to Y\), dass \(X\) ein Superschlüssel ist.

$$
X\to Y\text{ nichttrivial}
\quad\Longrightarrow\quad
X\text{ ist ein Superschlüssel}.
$$

BCNF ist strenger als 3NF.

$$
\mathrm{BCNF}\subseteq\mathrm{3NF}.
$$

Jede BCNF-Relation ist in der 3NF, aber nicht jede 3NF-Relation in der BCNF.

### Beispiel: 3NF, aber nicht BCNF

Betrachten wir die Relation

~~~text
assignment(student, course, instructor)
~~~

mit folgenden Regeln:

1. Ein Student wird für einen bestimmten Kurs genau einem Dozenten zugeordnet.
2. Jeder Dozent unterrichtet genau einen Kurs.

Die funktionalen Abhängigkeiten lauten:

$$
(student,course)\to instructor
$$

$$
instructor\to course
$$

Die Kandidatenschlüssel sind \((student,course)\) und \((student,instructor)\). Damit ist jedes Attribut ein Primattribut, sodass die Bedingungen der 3NF erfüllt sind.

`instructor` allein ist jedoch kein Superschlüssel, bestimmt aber `course`; die Relation verletzt daher die BCNF.

Eine BCNF-Zerlegung kann wie folgt aussehen:

- instructor_course(instructor, course)
- student_instructor(student, instructor)

Dies verringert Duplikate, doch die ursprüngliche Bedingung \((student,course)\to instructor\) lässt sich möglicherweise nur schwer anhand lokaler Bedingungen der einzelnen Tabellen prüfen. Hier zeigt sich die Abwägung zwischen BCNF und Abhängigkeitserhaltung.

## 8. Zwei Bedingungen für eine gute Zerlegung

### Verlustfreier Join

Ein natürlicher Join der zerlegten Relationen muss die ursprüngliche Relation ohne unechte Tupel wiederherstellen.

Eine Zerlegung in zwei Relationen \(R_1,R_2\) ist verlustfrei, wenn im Abschluss der funktionalen Abhängigkeiten mindestens eine der folgenden Beziehungen gilt:

$$
(R_1\cap R_2)\to R_1
$$

oder

$$
(R_1\cap R_2)\to R_2.
$$

Anschaulich müssen die gemeinsamen Attribute für mindestens eine der Relationen als Schlüssel wirken.

### Abhängigkeitserhaltung

Eine Zerlegung ist abhängigkeitserhaltend, wenn sich die ursprünglichen funktionalen Abhängigkeiten ohne Join durch lokale Bedingungen der einzelnen Relationen durchsetzen lassen.

Die 3NF-Synthese eignet sich dazu, sowohl verlustfreie Joins als auch Abhängigkeitserhaltung zu erreichen. Eine BCNF-Zerlegung kann verlustfrei gestaltet werden, erhält jedoch nicht zwangsläufig jede Abhängigkeit. Daher ist die Aussage „Eine höhere Normalform ergibt immer ein besseres Schema“ falsch.

## 9. Praktischer Arbeitsablauf zur Normalisierung

### Schritt 1: Tatsachen als Sätze formulieren

Vor dem Zeichnen eines ERD werden die Geschäftsregeln beispielsweise so beschrieben:

- Ein A kann mehrere B besitzen.
- Jedes B gehört genau zu einem C.
- Ist ein Preis ein gegenwärtiges Attribut oder ein Schnappschuss zum Transaktionszeitpunkt?
- Wird eine Kennung während ihrer gesamten Lebensdauer niemals wiederverwendet?

### Schritt 2: Kandidatenschlüssel und funktionale Abhängigkeiten auflisten

Nicht nur den Primärschlüssel betrachten, sondern jeden Kandidatenschlüssel ermitteln. Eindeutigkeitsbedingungen, nullable Spalten und zeitliche Gültigkeit sind einzubeziehen.

### Schritt 3: Eine minimale Überdeckung ableiten

- Jede rechte Seite in einzelne Attribute aufteilen.
- Überflüssige Attribute von jeder linken Seite entfernen.
- Redundante Abhängigkeiten entfernen, die aus den übrigen folgen.

### Schritt 4: Normalform beurteilen

Mit 1NF beginnen und über 2NF und 3NF bis zur BCNF fortfahren. Jeder Verletzung wird eine konkrete Änderungs-, Einfüge- oder Löschanomalie zugeordnet.

### Schritt 5: Qualität der Zerlegung prüfen

Verlustfreiheit und Abhängigkeitserhaltung überprüfen. Wenn eine Bedingung mehrere Tabellen umfasst, werden die durchsetzende Transaktion, der Trigger, eine mögliche Assertion oder die Anwendungsinvariante dokumentiert.

### Schritt 6: Physisches Schema entwerfen

PK, UNIQUE, FK, NOT NULL, CHECK und Indizes hinzufügen. Nicht davon ausgehen, dass die Datenbank automatisch einen Index für Fremdschlüsselspalten erstellt; das Verhalten des eingesetzten DBMS ist zu prüfen.

### Schritt 7: An realen Abfragen und Schreibpfaden bewerten

Abfragepläne, Kardinalität, Sperren, Schreibverstärkung und Speicherbedarf messen. Nur dort bewusst denormalisieren, wo ein Leistungsproblem tatsächlich nachgewiesen wurde.

## 10. Wann Denormalisierung sinnvoll ist

Normalisierung ist der Standard für den Entwurf der logischen maßgeblichen Datenquelle. Abgeleitete Darstellungen können in folgenden Fällen angemessen sein.

### Leseleistung

Sind häufige Aggregationen oder mehrfache Joins tatsächlich ein Engpass, kommen eine materialisierte Sicht, eine indizierte Sicht oder eine Zusammenfassungstabelle infrage. Quellrelationen und Aktualisierungsrichtlinie müssen festgelegt werden.

### Analytische Modelle

Ein OLAP-Sternschema priorisiert einfache Abfragen und effiziente Scans um Fakten und Dimensionen. Es sollte sicherheitshalber als transformiertes Bereitstellungsmodell und nicht als direkter Ersatz des OLTP-Quellschemas verstanden werden.

### Ereignisse und Schnappschüsse

Eine unveränderliche Ereignisnutzlast darf einige Werte duplizieren, um den damaligen Zustand zu erhalten. Aktuelle Stammdaten und historische Ereigniswahrheit müssen unterschieden werden.

### Externe Dokumente erhalten

Muss die Nutzlast einer externen API in ihrer ursprünglichen Form erhalten bleiben, können rohes JSON und normalisierte Abfragetabellen nebeneinander bestehen. Die rohe Nutzlast als einziges Abfragemodell erschwert Bedingungen und Migrationen.

Für jede Denormalisierung sind außerdem festzulegen:

- die maßgebliche Quelle,
- die für Aktualisierungen verantwortliche Stelle,
- das synchrone oder asynchrone Aktualisierungsverfahren,
- die akzeptable Veraltung,
- das Wiederherstellungsverfahren und
- eine Abfrage zum Erkennen von Inkonsistenzen.

## 11. Zeit und Historie sind getrennte Dimensionen

„Der Name eines Kunden“ muss nicht ein einziger aktueller Wert sein.

- aktueller kanonischer Name
- Anzeigename zum Zeitpunkt der Bestellung
- rechtlicher Name während eines bestimmten Gültigkeitszeitraums
- im ursprünglichen Ereignis empfangener Rohname

Bei zeitlichen Anforderungen sind `valid_from`, `valid_to`, Systemzeit und Ereigniszeit zu unterscheiden. Ist die aktuelle Tabelle zwar normalisiert, werden Werte bei benötigter Historie jedoch einfach überschrieben, geht die Reproduzierbarkeit verloren.

## 12. Prüfliste zur Validierung

- [ ] Sind die funktionalen Abhängigkeiten Geschäftsregeln statt Zufällen in einer Stichprobe?
- [ ] Wurden neben dem Primärschlüssel alle Kandidatenschlüssel ermittelt?
- [ ] Verbirgt ein Surrogatschlüssel Duplikate in einem natürlichen Schlüssel?
- [ ] Wurde die Atomarität der 1NF anhand von Nutzung und Domänensemantik beurteilt?
- [ ] Wurden partielle Abhängigkeiten von einem zusammengesetzten Schlüssel geprüft?
- [ ] Wurden transitive Abhängigkeiten über Nichtschlüsselattribute geprüft?
- [ ] Wurde die Primattribut-Ausnahme der 3NF korrekt angewandt?
- [ ] Wurde die BCNF-Zerlegung auf einen Verlust der Abhängigkeitserhaltung geprüft?
- [ ] Wurde die Verlustfreiheit des Joins für die Zerlegung bestätigt?
- [ ] Werden die Regeln tatsächlich mit PK-, UNIQUE-, FK- und CHECK-Bedingungen durchgesetzt?
- [ ] Werden aktuelle Tatsachen von historischen Schnappschüssen unterschieden?
- [ ] Besitzt jeder denormalisierte Wert eine Quelle und eine Aktualisierungsrichtlinie?
- [ ] Wurden Leistungsaussagen anhand realer Abfragepläne überprüft?

## 13. Häufige Fallstricke

### Der Irrtum, eine ID in jeder Tabelle garantiere die 2NF

Dass ein Surrogat-Primärschlüssel aus einer einzigen Spalte besteht, beseitigt keine partiellen Abhängigkeiten von den ursprünglichen fachlichen Kandidatenschlüsseln. Die Anomalien bleiben bestehen.

### Der Irrtum, NULL vereinfache funktionale Abhängigkeiten

Die Semantik von SQL-NULL, dreiwertiger Logik und die Behandlung von NULL durch eine UNIQUE-Bedingung unterscheiden sich je nach DBMS und müssen geprüft werden. Eine erforderliche fachliche Kennung nullable zu machen, verschleiert die Überlegungen zu Kandidatenschlüsseln.

### Entwurf ausschließlich zur Verringerung von Joins

Joins sind eine grundlegende Operation relationaler Datenbanken. Tabellen wegen einer einzigen Leseabfrage zusammenzuführen und dabei die Kosten redundanter Aktualisierungen sowie das Konsistenzrisiko zu ignorieren, kann die Gesamtkosten des Systems erhöhen.

### Der Irrtum, Normalisierung löse sämtliche Integritätsprobleme

Normalformen behandeln funktionale Abhängigkeiten und Redundanz. Regeln zu Bereichsbedingungen, zeilenübergreifenden Aggregaten, zeitlichen Überschneidungen oder Zustandsübergängen erfordern zusätzliche Bedingungen und einen passenden Transaktionsentwurf.

### BCNF mechanisch über alles stellen

Eine Zerlegung kann die Abhängigkeitserhaltung verlieren und eine Regel ohne Joins oder komplexe Trigger unprüfbar machen. In der 3NF zu verbleiben, kann betrieblich mitunter sicherer sein.

## Fazit

1NF, 2NF, 3NF und BCNF sind keine bloß auswendig zu lernende Abfolge, sondern ein Rahmen, um unterschiedliche Ursachen von Redundanz zu erkennen und zu beseitigen.

- 1NF: relational genau ein Wert an jeder Attributposition
- 2NF: Entfernen nichtprimärer Tatsachen, die nur von einem Teil eines zusammengesetzten Kandidatenschlüssels abhängen
- 3NF: Kontrolle indirekter Abhängigkeiten über Nichtschlüsselattribute
- BCNF: Beschränkung jeder Determinante auf einen Superschlüssel

Das praktische Ziel ist nicht die höchste Zahl, sondern ein **Schema, in dem die Datenbank Geschäftsregeln konsistent durchsetzt, die Zerlegung verlustfrei ist und erforderliche Abhängigkeiten betrieblich praktikabel erhalten bleiben**.
