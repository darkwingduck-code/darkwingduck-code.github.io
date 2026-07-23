---
title: "Reproduzierbare Forschungssoftware veröffentlichen: Releases, CITATION.cff und Zenodo-DOIs"
date: 2026-07-21 10:00:00 +0900
categories: [Research Engineering, Reproducibility]
tags: [research-software, reproducibility, release, git-tag, citation-cff, zenodo, software-doi, preprint]
description: "Ein Verfahren, um aus einem Forschungssoftware-Repository ein reproduzierbares Release zu erstellen und CITATION.cff, Langzeitarchiv und Software-DOI zu verbinden, ohne die Kennungen von Fachartikel und Preprint zu vermischen."
lang: de-DE
hidden: true
translation_key: reproducible-research-software-release-doi
---

{% include language-switcher.html %}

Allein die Tatsache, dass Forschungscode in einem öffentlichen Repository liegt, macht ihn weder reproduzierbar noch zitierfähig. Der Standard-Branch verändert sich fortlaufend, Abhängigkeiten verschwinden, und Leser können kaum erkennen, mit welchem Commit die Ergebnisse erzeugt wurden.

Für eine ordnungsgemäße Veröffentlichung von Forschungssoftware sind vier Objekte zu unterscheiden.

1. Das **Quellcode-Repository**, in dem die Entwicklung weitergeht
2. Ein **versioniertes Release samt Tag**, das einen aussagekräftigen Zustand einfriert
3. Ein **archivierter Software-Datensatz samt DOI** für Langzeitaufbewahrung und Zitierung
4. Ein **Fachartikel oder Preprint**, der Forschungsfrage, Methoden und Ergebnisse erläutert

Dieser Beitrag beschreibt ein praktisches Verfahren, um diese vier Objekte nachvollziehbar miteinander zu verknüpfen, ohne sie gleichzusetzen.

## 1. Zuerst klären, was jede Kennung identifiziert

| Objekt | Hauptzweck | Veränderbarkeit | Typische Kennung |
|---|---|---|---|
| Repository | Zusammenarbeit und laufende Entwicklung | Branches ändern sich fortlaufend | Repository-URL |
| Commit | Quellcode-Schnappschuss | inhaltsadressiert und praktisch unveränderlich | Commit-Hash |
| Tag | menschenlesbare Versionsbezeichnung | sollte laut Richtlinie unveränderlich sein | Tag-Name + Ziel-Commit |
| Release | Veröffentlichungshinweise und Artefaktpaket | Release Notes können bearbeitbar sein | Version + Release-URL |
| Softwarearchiv | langfristig aufbewahrtes Forschungsobjekt | Dateien eines Versionsdatensatzes sind fixiert | Software-DOI |
| Preprint/Artikel | Forschungsaussagen und Darstellung | Versionsrichtlinie hängt von der Plattform ab | Publikations-DOI oder Kennung |
| Datensatz | Ein- oder Ausgabedatenobjekt | sollte je Version fixiert sein | Datensatz-DOI |

Ein Commit-Hash verweist auf exakten Quellcode, liefert jedoch weder wissenschaftliche Metadaten noch eine Strategie zur Langzeitaufbewahrung. Eine DOI ermöglicht dauerhafte Identifikation und Metadatenverknüpfung, stellt aber die Ausführungsumgebung nicht automatisch wieder her. Beides gehört zusammen.

## 2. Den Grad der Reproduzierbarkeit angeben

Bezeichnen Sie etwas nicht lediglich als „reproduzierbar“, sondern definieren Sie den unterstützten Umfang.

- **Quellcode-Reproduzierbarkeit**: Derselbe Quellbaum lässt sich beschaffen.
- **Build-Reproduzierbarkeit**: In der angegebenen Umgebung lässt sich dasselbe Programm oder Paket bauen.
- **Rechnerische Reproduzierbarkeit**: Aus denselben Eingaben entsteht innerhalb einer zulässigen Toleranz dieselbe Ausgabe.
- **Ergebnisreproduzierbarkeit**: Abbildungen, Tabellen und Kennzahlen des Artikels lassen sich erneut erzeugen.
- **Auditierbarkeit**: Code, Konfiguration und Datenherkunft lassen sich von einem Ergebnis aus rückwärts verfolgen.

Bitidentische Ausgaben auf jeder Plattform zu garantieren kann schwierig sein. Geben Sie dann unterstütztes Betriebssystem und Architektur, numerische Toleranzen sowie nichtdeterministische Komponenten an.

## 3. Ein Release legt vertraglich fest, welcher Commit zu zitieren ist

### Unterschied zwischen Tag, Release und Archiv

- Ein Git-Tag ist eine Bezeichnung, die einem bestimmten Commit zugeordnet ist.
- Ein Release beim Hostingdienst ist ein Verteilungsobjekt, das Release Notes und Binärartefakte mit einem Tag verbindet.
- Ein Archiv ist ein eigener Forschungsdatensatz, der Quellcode und Metadaten langfristig bewahrt.

Die Versionen aller drei Objekte müssen übereinstimmen.

~~~text
package metadata version
  = documentation version
  = CITATION.cff version
  = release title
  = git tag
  = archived record version
~~~

### Versionierungsrichtlinie

Semantic Versioning ist möglich; zunächst muss jedoch definiert werden, was die „öffentliche API“ der Forschungssoftware ausmacht.

- Kommandozeilenoptionen und Dateiformate
- Python-/C++-API
- Konfigurationsschema
- Semantik der numerischen Methode oder Standardwerte
- Ausgabeschema und Einheiten
- trainierte Gewichte oder Parameterpakete

Verändert eine numerische Methode oder ein Standardwert die wissenschaftliche Interpretation derselben Eingabe, ist sorgfältig zu prüfen, ob dies wirklich nur als Patch gelten darf. Der Kompatibilitätsvertrag ist wichtiger als die Versionsnummer.

### Tags nicht verschieben

Wird ein veröffentlichter Tag zwangsweise auf einen anderen Commit verschoben, bezeichnet derselbe Versionsname unterschiedlichen Quellcode. Erstellen Sie für eine Korrektur ein neues Patch-Release und dokumentieren Sie das bekannte Problem in der vorherigen Version.

## 4. Das Reproduzierbarkeitspaket eines Releases

Ein Release benötigt mindestens die folgenden Bestandteile.

### Verständnis und Ausführung

- README: Zweck, Umfang und Schnelleinstieg
- LICENSE: Bedingungen für die Nutzung von Quellcode und gebündelten Assets
- Umgebungs- beziehungsweise Lock-Datei
- Konfigurationsbeispiele und Schema
- Datenwörterbuch für Ein- und Ausgabe
- minimales End-to-End-Beispiel
- bekannte Einschränkungen

### Qualitätsnachweise

- Ergebnisse automatisierter Tests
- analytische Verifikation oder Benchmark-Verifikation
- numerische Toleranzen
- Vertrag über deterministisches und nichtdeterministisches Verhalten
- Matrix unterstützter Plattformen
- Changelog und Migrationshinweise

### Herkunft

- Quellcode-Revision
- Release-Datum und Version
- Digest der Dependency-Lock-Datei
- Container-Image-Digest, zusammen mit einem gegebenenfalls vorhandenen Tag
- Version oder Prüfsumme der Eingabedaten
- Befehle zum Erzeugen von Abbildungen und Tabellen

Nehmen Sie große erzeugte Ausgaben und Secrets nicht wahllos in ein Quellcodearchiv auf. Stellen Sie für reproduzierbare Ausgaben Rezepte und Prüfsummen bereit und verknüpfen Sie notwendige Daten nach Prüfung von Lizenz- und Datenschutzauflagen als eigenes Archivobjekt.

## 5. Die Rolle von CITATION.cff

`CITATION.cff` ist eine YAML-basierte Datei mit Zitationsmetadaten, die Menschen lesen und Werkzeuge auswerten können. Im Repository-Stammverzeichnis ermöglicht sie unterstützten Hosting-Oberflächen, Zitationsangaben anzuzeigen. Die aktuelle offizielle CFF-Anleitung und die GitHub-Dokumentation verwenden in ihren Beispielen das Format `cff-version: 1.2.0`.

Die folgende allgemeine Vorlage veranschaulicht den Aufbau.

~~~yaml
cff-version: 1.2.0
message: "If you use this software, please cite this version."
title: "Example Scientific Software"
type: software
version: 1.0.0
date-released: 2026-07-21
license: MIT
repository-code: "https://example.org/example-software"
authors:
  - family-names: "Replace-With-Family-Name"
    given-names: "Replace-With-Given-Name"
~~~

Ersetzen Sie die Platzhalter durch tatsächliche öffentliche Metadaten und prüfen Sie die Datei mit einem CFF-Validator. Eine persönliche E-Mail-Adresse ist für eine Zitierung nicht erforderlich; lassen Sie sie weg, sofern kein Grund für ihre Veröffentlichung besteht.

### Felder, die mindestens übereinstimmen müssen

- Softwaretitel
- Urheber und ihre Reihenfolge
- Version
- Veröffentlichungsdatum
- Repository-URL
- Lizenz
- versionsspezifische Software-DOI

Leiten Sie die Reihenfolge der Mitwirkenden nicht automatisch aus der Anzahl ihrer Commits ab. Legen Sie Kriterien für Autorenschaft und Rollen der Mitwirkenden vorab fest und stellen Sie bei Bedarf eigene Contributor-Metadaten bereit.

### Software und Fachartikel miteinander verknüpfen

Ein zugehöriger Fachartikel kann über `preferred-citation` angegeben werden. Dadurch kann die Zitationsoberfläche des Repositorys jedoch die Zitierung des Artikels statt der Software priorisieren. Wenn die Anerkennung der Software selbst und die Reproduzierbarkeit einer exakten Version wichtig sind, sollte die primäre Zitierung auf den Software-Datensatz verweisen und der Artikel über Referenzen oder verwandte Kennungen verknüpft werden.

## 6. Vor Vergabe einer DOI das Archiv verstehen

Eine DOI ist keine dekorative Nummer im Quellcode, sondern eine dauerhafte Kennung für ein bestimmtes Forschungsobjekt. Nach der aktuellen Zenodo-Anleitung wird beim Veröffentlichen eines Datensatzes eine DOI registriert; eine neue Version mit geänderten Dateien wird als eigener Datensatz mit eigener dauerhafter Kennung geführt.

### Versions-DOI und Konzept-DOI

Die DOI-Versionierung von Zenodo stellt bei der ersten Veröffentlichung zwei DOI-Kategorien bereit.

- **Versions-DOI**: identifiziert die Dateien eines bestimmten Releases
- **Konzept-DOI**: identifiziert die Sammlung aller Versionen und verweist auf die Landingpage der neuesten Version

Für die Zitierung des exakt zur Reproduktion verwendeten Codes ist die Versions-DOI die übliche Wahl. Die Konzept-DOI eignet sich gegebenenfalls für einen Verweis auf das sich weiterentwickelnde Softwareprojekt als Ganzes.

Erzeugen Sie Versionen nicht, indem Sie willkürlich einen Zusatz wie `.v2` an eine DOI-Zeichenfolge hängen. Die Versionsbeziehungen werden in den Archivmetadaten abgebildet.

## 7. Sicheres Verfahren zum Verknüpfen von Zenodo und Release

Bei Verwendung einer Git-Hosting-Integration ist der übliche Ablauf wie folgt.

1. Bestätigen Sie, dass das Repository öffentlich werden darf.
2. Führen Sie Secret-Scan, Historienprüfung und Lizenzprüfung durch.
3. Aktivieren Sie das Repository in der Archivintegration.
4. Frieren Sie den Commit des Release Candidates ein.
5. Führen Sie Tests, Dokumentations-Build und Beispielreproduktion aus.
6. Stimmen Sie die Versionsmetadaten mit `CITATION.cff` ab.
7. Erstellen Sie einen unveränderlichen Tag und ein Release.
8. Prüfen Sie Titel, Urheber, Ressourcentyp, Version und Lizenz des Archivdatensatzes.
9. Erfassen Sie nach der Veröffentlichung Versions-DOI und Konzept-DOI getrennt.
10. Ergänzen Sie die richtigen Beziehungen auf Release-Seite, in README, CFF und Artikelmetadaten.

Die offizielle GitHub-Anleitung erläutert, dass die Zenodo-Integration eine DOI für ein Repository-Archiv vergeben kann und das eingebundene Repository öffentlich sein muss. Bei Organisations-Repositorys kann eine gesonderte Genehmigung des Integrationszugriffs erforderlich sein.

### Wenn die DOI bereits vor dem Release in Dateien stehen soll

Es gibt zwei Vorgehensweisen.

- Reservieren Sie vorab eine DOI im Archiv und tragen Sie sie anschließend in die Release-Metadaten ein.
- Archivieren Sie das erste Release, fügen Sie die DOI dem Standard-Branch hinzu und synchronisieren Sie die Versionsmetadaten ab dem nächsten Release vollständig.

Beim Löschen eines Entwurfs mit reservierter DOI kann die Reservierung verloren gehen; prüfen Sie daher die aktuelle Richtlinie des Archivs. Besitzt dasselbe Objekt bereits eine DOI, vergeben Sie keine doppelte DOI, sondern tragen die vorhandene in die Metadaten ein.

## 8. Software-DOI und Preprint-DOI identifizieren nie dasselbe Objekt

Software und Preprint sind unterschiedliche Forschungsergebnisse.

| Merkmal | Software-Datensatz | Preprint-Datensatz |
|---|---|---|
| Inhalt | Quellcode, Paket, Programm, Dokumentation | Forschungsfrage, Methoden, Ergebnisse, Interpretation |
| Ressourcentyp | Software | Preprint/Publikation |
| Bedeutung der Version | Code-Release | Manuskriptrevision |
| Primäres Zitationsziel | exakt ausgeführte Softwareversion | gelesene und diskutierte Dokumentversion |
| Kennung | Software-DOI | Preprint-DOI/-Kennung |

Vermeiden Sie daher Folgendes.

- eine Preprint-DOI in das Software-DOI-Feld von `CITATION.cff` einzutragen
- eine Preprint-Datei mit einem Softwarearchiv zu vermischen und beide als einen Ressourcentyp auszugeben
- die DOI eines Zeitschriftenartikels für einen ergänzenden Code-Upload wiederzuverwenden
- Code-Release-Versionen und Manuskriptrevisionen in dasselbe Nummerierungsschema zu zwingen

Verknüpfen Sie die Beziehungen stattdessen in den Archivmetadaten.

- Software **IsSupplementTo** Fachartikel
- Software **IsDocumentedBy** Fachartikel oder eigener Dokumentationsdatensatz
- Fachartikel **References** Software
- Software **Requires** Eingabedatensatz; Datensatz **IsRequiredBy** Software

Prüfen Sie die tatsächlichen Bezeichnungen der Beziehungstypen im Metadatenvokabular des Archivs und deren Richtung. Maschinenlesbare verwandte Kennungen sind besser als reine Prosaangaben.

## 9. Quellcode, Umgebung und Daten gemeinsam fixieren

Auch mit einer Software-DOI lassen sich Ergebnisse ohne Abhängigkeiten und Eingaben nicht reproduzieren.

### Quellcode

- exakter Tag und Commit
- Submodule-Revisionen
- Generatorversion für erzeugten Quellcode
- Build-Skripte

### Umgebung

- Dependency-Lock-Datei
- Compiler-/Interpreterversion
- Betriebssystem und Architektur
- numerische Bibliotheken und Accelerator-Laufzeit
- Container-Digest oder Umgebungsexport

Nur das Container-Tag `latest` zu erfassen kann im Laufe der Zeit auf ein anderes Image verweisen. Erfassen Sie zusätzlich einen unveränderlichen Digest.

### Daten und Konfiguration

- Version/DOI des Eingabedatensatzes
- Dateiprüfsumme
- Code und Reihenfolge der Vorverarbeitung
- Konfigurationsdatei
- Zufalls-Seed und Split-Manifest
- Schema und Einheiten

Können Rohdaten nicht veröffentlicht werden, stellen Sie ein synthetisches oder minimales Beispiel, Schema, Generator und Zugangsbedingungen bereit und benennen Sie die privaten Bestandteile, die eine vollständige Reproduktion einschränken.

## 10. Automatisierbare Release-Gates

Ein CI-Release-Workflow kann mindestens Folgendes prüfen.

~~~text
[quality]
unit + integration + numerical tests pass
example workflow reproduces expected metrics
documentation builds without broken internal links

[metadata]
package version == tag version
CITATION.cff parses and validates
release date and changelog entry exist
license and notices are present

[security]
secret scan passes
private paths and hostnames are absent
large or restricted data are not bundled

[archive readiness]
source archive is self-contained
dependency lock exists
input/output schema is documented
~~~

Die Vergabe einer DOI ist selbst eine Veröffentlichung, die externen Zustand verändert. Ein Probelauf und eine menschliche Prüfung erhöhen daher die Sicherheit. Ein veröffentlichter Archivdatensatz darf nicht wie ein gewöhnlicher Branch behandelt werden.

## 11. Release-Runbook

### Vorbereitung

- Umfang und Kompatibilitätsänderungen einordnen.
- Version festlegen.
- Changelog und Migrationshinweise verfassen.
- Veraltete Abhängigkeiten und Lizenzen prüfen.
- Autoren- und Contributor-Metadaten für die Zitierung prüfen.

### Verifikation

- In einer sauberen Umgebung bauen.
- Das minimale Beispiel von Anfang an erneut ausführen.
- Befehle prüfen, die zentrale Abbildungen und Tabellen erzeugen.
- Numerische Toleranzen und Plattformunterschiede prüfen.
- Das exakt zu archivierende Quellcodepaket entpacken und ausführen.

### Veröffentlichung

- Release-Commit mergen.
- Gegebenenfalls die Richtlinie für annotierte/signierte Tags anwenden.
- Release Notes und Artefaktprüfsummen veröffentlichen.
- Archivmetadaten abschließend prüfen und anschließend veröffentlichen.
- Versions-DOI mit Release und CFF verknüpfen.

### Nach der Veröffentlichung

- Bestätigen, dass die DOI auf die richtige Landingpage aufgelöst wird.
- Dateiliste und Prüfsummen des Archivs kontrollieren.
- Bestätigen, dass Konzept- und Versions-DOI wie vorgesehen erscheinen.
- Verwandte Kennungen in Repository, Dokumentation und Preprint aktualisieren.
- Für das nächste Release ein Runbook-Issue anlegen.

## 12. Prüfliste zur Verifikation

- [ ] Sind die Rollen von Repository, Commit, Tag, Release und Archiv voneinander abgegrenzt?
- [ ] Stimmen die Versionen von Tag, Paket, Dokumentation, CFF und Archiv überein?
- [ ] Verbietet eine Richtlinie das Verschieben veröffentlichter Tags?
- [ ] Läuft das End-to-End-Beispiel in einer sauberen Umgebung?
- [ ] Sind Versionen von Abhängigkeiten und Eingabedaten fixiert?
- [ ] Liegt `CITATION.cff` im Stammverzeichnis und besteht die Datei eine Validatorprüfung?
- [ ] Stimmen Softwaretitel, Urheberreihenfolge, Version und Lizenz mit den Archivmetadaten überein?
- [ ] Ist die Verwendung von Versions-DOI und Konzept-DOI klar getrennt?
- [ ] Werden Software-DOIs getrennt von Preprint-/Artikel-DOIs verwaltet?
- [ ] Sind verwandte DOIs über maschinenlesbare Beziehungen verknüpft?
- [ ] Sind Quellcode und Archive frei von Secrets, persönlichen Pfaden und privaten Daten?
- [ ] Ist neben dem Container-Tag ein unveränderlicher Digest erfasst?
- [ ] Prüft ein Mensch Metadaten und Dateipaket vor Veröffentlichung der DOI?

## 13. Häufige Fallstricke und Grenzen

### „Es liegt in Git und ist daher dauerhaft bewahrt“

Hosting-URL und Benutzerkonto sind keine Archivierungskennungen. Archiv und DOI verbessern die langfristige Zugänglichkeit; ohne Lizenz, Metadaten und Ausführungsanleitung bleibt ihr Nutzen jedoch begrenzt.

### „Es besitzt eine DOI und ist daher reproduzierbar“

Eine DOI identifiziert ein Objekt. Sie stellt weder Abhängigkeiten, Daten und Konfiguration noch numerische Toleranzen automatisch bereit.

### Nur die neueste Konzept-DOI zitieren

Leser könnten dadurch eine spätere inkompatible Version erhalten. Zur Reproduktion eines bestimmten Forschungsergebnisses sind Versions-DOI und Release-Version erforderlich.

### Eine DOI manuell in die README kopieren und Widersprüche erzeugen

Erzeugen Sie CFF, Paketmetadaten, Release Notes und Archivmetadaten möglichst aus einer einzigen Quelle oder gleichen Sie sie in CI gegeneinander ab.

### Annehmen, das Löschen eines Eintrags aus einem öffentlichen Repository entferne auch seine Secrets

Secrets können in Historie, Forks, CI-Logs, Release-Artefakten und Archiven verbleiben. Löschen Sie sie nach einer Offenlegung nicht nur, sondern widerrufen und rotieren Sie sie sofort und prüfen Sie sämtliche Aufbewahrungsorte.

### Quellcode ohne Ausführungsvertrag

Ohne Dokumentation unterstützter Plattformen, Toleranzen, nichtdeterministischer Komponenten und erwarteter Laufzeit lässt sich schwer beurteilen, ob eine fehlgeschlagene Reproduktion auf einen Fehler oder einen Umgebungsunterschied zurückgeht.

## 14. Offizielle Referenzen

- [Offizielle Anleitung zum Citation File Format](https://citation-file-format.github.io/)
- [GitHub-Anleitung zu Zitationsdateien](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files)
- [Offizielle Anleitung zur Archivierung eines GitHub-Repositorys mit DOI](https://docs.github.com/repositories/archiving-a-github-repository/referencing-and-citing-content)
- [Lebenszyklus von Zenodo-Datensätzen und -Versionen](https://help.zenodo.org/docs/deposit/about-records/)
- [Zenodo-Anleitung zur DOI-Versionierung](https://support.zenodo.org/help/en-gb/1-upload-deposit/97-what-is-doi-versioning)
- [Zenodo-Anleitung zur DOI-Reservierung](https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/)
- [DataCite-Definitionen für Beziehungen verwandter Kennungen](https://datacite-metadata-schema.readthedocs.io/en/4.6/appendices/appendix-1/relationType/)

## Fazit

Die zentralen Verknüpfungen reproduzierbarer Forschungssoftware lauten wie folgt.

~~~text
result
  -> input/data version
  -> configuration
  -> software version DOI
  -> release tag
  -> exact commit
  -> locked environment
~~~

Ein Fachartikel oder Preprint ist ein eigenes Objekt, das diese Verknüpfungen erläutert und Aussagen dazu trifft. Trennen Sie die DOIs für Software und Dokumente und verbinden Sie sie anschließend über verwandte Kennungen, um sowohl Anerkennung als auch Reproduzierbarkeit zu erhalten.

Ein gutes Release ist nicht bloß „der Tag, an dem der Code veröffentlicht wurde“. Es ist der Zustand, in dem Dritte nicht mehr erraten müssen, welche Version sie beziehen, welche Umgebung sie verwenden oder welchen Befehl sie ausführen sollen.
