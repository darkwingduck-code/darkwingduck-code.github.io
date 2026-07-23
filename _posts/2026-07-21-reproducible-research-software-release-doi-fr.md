---
title: "Publier un logiciel de recherche reproductible : releases, CITATION.cff et DOI Zenodo"
date: 2026-07-21 10:00:00 +0900
categories: [Research Engineering, Reproducibility]
tags: [research-software, reproducibility, release, git-tag, citation-cff, zenodo, software-doi, preprint]
description: "Une procédure pour transformer un dépôt de code de recherche en release reproductible et relier CITATION.cff, une archive de conservation et un DOI logiciel tout en séparant les identifiants d’article et de prépublication."
lang: fr-FR
hidden: true
translation_key: reproducible-research-software-release-doi
---

{% include language-switcher.html %}

Le simple fait qu’un code de recherche se trouve dans un dépôt public ne le rend ni reproductible ni citable. La branche par défaut continue d’évoluer, des dépendances disparaissent et les lecteurs peinent à savoir quel commit a produit les résultats.

Pour publier correctement un logiciel de recherche, distinguez quatre objets.

1. Le **dépôt source**, dans lequel le développement se poursuit
2. Une **release versionnée et un tag** qui figent un état significatif
3. Une **notice d’archive logicielle et un DOI** pour la conservation et la citation à long terme
4. Un **article ou une prépublication** qui expose la question de recherche, les méthodes et les résultats

Cet article présente une procédure pratique pour relier ces quatre objets de manière traçable sans les confondre.

## 1. Commencer par distinguer ce qu’identifie chaque identifiant

| Objet | Rôle principal | Mutabilité | Identifiant typique |
|---|---|---|---|
| dépôt | collaboration et développement continu | les branches continuent d’évoluer | URL du dépôt |
| commit | instantané du code source | adressé par contenu et effectivement figé | hash du commit |
| tag | étiquette de version lisible par les humains | doit être immuable par politique | nom du tag + commit cible |
| release | notes de distribution et ensemble d’artefacts | les notes de release peuvent être modifiables | version + URL de la release |
| archive logicielle | objet de recherche conservé à long terme | les fichiers d’une notice de version sont figés | DOI du logiciel |
| prépublication/article | affirmations scientifiques et exposé | la politique de version dépend de la plateforme | DOI ou identifiant de publication |
| jeu de données | objet de données d’entrée ou de sortie | doit être figé pour chaque version | DOI du jeu de données |

Un hash de commit désigne le code source exact, mais n’apporte ni métadonnées académiques ni politique de conservation à long terme. Un DOI assure une identification persistante et des liens de métadonnées, mais ne restaure pas automatiquement l’environnement d’exécution. Utilisez les deux conjointement.

## 2. Indiquer le niveau de reproductibilité

Ne vous contentez pas de dire « reproductible » ; définissez le périmètre pris en charge.

- **Reproductibilité du code source** : le même arbre source peut être obtenu.
- **Reproductibilité du build** : le même exécutable ou package peut être construit dans l’environnement indiqué.
- **Reproductibilité computationnelle** : le même résultat peut être obtenu à partir des entrées dans une tolérance autorisée.
- **Reproductibilité des résultats** : les figures, tableaux et métriques de l’article peuvent être régénérés.
- **Auditabilité** : la provenance du code, de la configuration et des données peut être remontée à partir d’un résultat.

Garantir une sortie identique bit à bit sur toutes les plateformes peut s’avérer difficile. Dans ce cas, précisez le système d’exploitation et l’architecture pris en charge, la tolérance numérique et les composants non déterministes.

## 3. Une release est un contrat qui précise quel commit citer

### Différence entre tag, release et archive

- Un tag Git est un nom associé à un commit précis.
- Une release d’un service d’hébergement est un objet de distribution qui relie des notes de release et des artefacts binaires à un tag.
- Une archive est une notice de recherche distincte qui conserve le code source et les métadonnées à long terme.

Les versions de ces trois objets doivent correspondre.

~~~text
package metadata version
  = documentation version
  = CITATION.cff version
  = release title
  = git tag
  = archived record version
~~~

### Politique de versionnement

Vous pouvez utiliser le versionnement sémantique, mais commencez par définir ce qui constitue l’« API publique » du logiciel de recherche.

- options de ligne de commande et formats de fichiers
- API Python/C++
- schéma de configuration
- sémantique de la méthode numérique ou des valeurs par défaut
- schéma et unités de sortie
- poids entraînés ou ensembles de paramètres

Si la modification d’une méthode numérique ou d’une valeur par défaut change l’interprétation scientifique d’une même entrée, demandez-vous soigneusement si elle doit être traitée comme un simple patch. Le contrat de compatibilité prime sur le numéro de version.

### Ne pas déplacer les tags

Forcer la mise à jour d’un tag publié vers un autre commit fait désigner des codes source différents par le même nom de version. Si une correction est nécessaire, créez une nouvelle release de patch et documentez le problème connu dans la version précédente.

## 4. L’ensemble de reproductibilité à inclure dans une release

Une release doit au minimum comporter les éléments suivants.

### Compréhension et exécution

- README : objectif, périmètre et démarrage rapide
- LICENSE : conditions d’utilisation du code source et des ressources incluses
- fichier d’environnement/de verrouillage
- exemples de configuration et schéma
- dictionnaire des données d’entrée/de sortie
- exemple minimal de bout en bout
- limites connues

### Preuves de qualité

- résultats des tests automatisés
- vérification analytique ou par benchmark
- tolérance numérique
- contrat déterministe/non déterministe
- matrice des plateformes prises en charge
- changelog et notes de migration

### Provenance

- révision source
- date et version de la release
- digest du verrou des dépendances
- digest de l’image conteneur, enregistré avec le tag s’il en existe un
- version ou somme de contrôle des données d’entrée
- commandes de génération des figures et tableaux

N’incluez pas sans discernement de grandes sorties générées ni de secrets dans une archive source. Fournissez des recettes et des sommes de contrôle pour les sorties reproductibles, et reliez les données nécessaires comme un objet d’archive distinct après avoir vérifié leur licence et leurs contraintes de confidentialité.

## 5. Le rôle de CITATION.cff

`CITATION.cff` est un fichier de métadonnées de citation fondé sur YAML, lisible par les personnes et interprétable par les outils. Le placer à la racine du dépôt permet aux interfaces d’hébergement compatibles d’afficher les informations de citation. Les recommandations officielles actuelles de CFF et la documentation GitHub utilisent le format `cff-version: 1.2.0` dans leurs exemples.

Le modèle générique suivant illustre sa structure.

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

Remplacez les placeholders par de véritables métadonnées publiques et validez le fichier avec un validateur CFF. Une adresse e-mail personnelle n’est pas requise pour une citation ; omettez-la sauf s’il existe une raison de la publier.

### Champs qui doivent au minimum correspondre

- titre du logiciel
- créateurs et leur ordre
- version
- date de release
- URL du dépôt
- licence
- DOI du logiciel propre à la version

Ne déterminez pas automatiquement l’ordre des contributeurs à partir du nombre de commits. Établissez à l’avance les règles d’éligibilité à la qualité d’auteur et les politiques de rôles des contributeurs, et fournissez si nécessaire des métadonnées distinctes sur les contributeurs.

### Comment relier le logiciel lui-même et un article

Vous pouvez présenter un article associé au moyen de `preferred-citation`, mais cela peut conduire l’interface de citation du dépôt à privilégier l’article plutôt que le logiciel. Lorsque le crédit du logiciel lui-même et la reproductibilité de la version exacte sont importants, il est plus clair de conserver la citation racine comme notice logicielle et de relier l’article au moyen de références ou d’identifiants associés.

## 6. Comprendre l’archive avant d’attribuer un DOI

Un DOI n’est pas un numéro décoratif dans le code source, mais un identifiant persistant pour un objet de recherche précis. Selon les recommandations actuelles de Zenodo, la publication d’une notice enregistre un DOI, tandis qu’une nouvelle version dont les fichiers ont changé est gérée comme une notice et un identifiant persistant distincts.

### DOI de version et DOI de concept

Le versionnement des DOI Zenodo fournit deux catégories de DOI lors de la première publication.

- **DOI de version** : identifie les fichiers d’une release précise
- **DOI de concept** : identifie l’ensemble de toutes les versions et renvoie vers la page de présentation de la dernière version

Le DOI de version est le choix par défaut pour citer le code exact utilisé à des fins de reproductibilité. Le DOI de concept peut convenir lorsque l’on désigne le projet logiciel évolutif dans son ensemble.

Ne créez pas de versions en ajoutant arbitrairement un suffixe tel que `.v2` à une chaîne de DOI. Les métadonnées de l’archive relient les versions entre elles.

## 7. Procédure sûre pour relier Zenodo et une release

Le flux habituel avec une intégration d’hébergement Git est le suivant.

1. Confirmer que le dépôt peut être rendu public.
2. Effectuer une recherche de secrets, un audit de l’historique et un audit des licences.
3. Activer le dépôt dans l’intégration de l’archive.
4. Figer le commit candidat à la release.
5. Exécuter les tests, construire la documentation et reproduire l’exemple.
6. Aligner les métadonnées de version sur `CITATION.cff`.
7. Créer un tag et une release immuables.
8. Examiner le titre, les créateurs, le type de ressource, la version et la licence de la notice d’archive.
9. Après publication, enregistrer séparément le DOI de version et le DOI de concept.
10. Ajouter les bonnes relations à la page de release, au README, au CFF et aux métadonnées de l’article.

Les recommandations officielles de GitHub expliquent que l’intégration Zenodo peut attribuer un DOI à l’archive d’un dépôt et que le dépôt intégré doit être public. Les dépôts d’une organisation peuvent exiger une approbation distincte pour l’accès à l’intégration.

### Pour inscrire le DOI dans les fichiers avant la release

Deux approches sont possibles.

- Réserver à l’avance un DOI dans l’archive, puis l’ajouter aux métadonnées de la release.
- Archiver la première release, ajouter le DOI à la branche par défaut, puis synchroniser entièrement les métadonnées de version à partir de la release suivante.

Supprimer un brouillon auquel un DOI est réservé peut faire perdre la réservation ; vérifiez donc la politique actuelle de l’archive. Si le même objet possède déjà un DOI, n’en attribuez pas un en double : saisissez le DOI existant dans les métadonnées.

## 8. Un DOI logiciel et un DOI de prépublication n’identifient jamais le même objet

Le logiciel et une prépublication sont des productions scientifiques distinctes.

| Distinction | Notice logicielle | Notice de prépublication |
|---|---|---|
| Contenu | code source, package, exécutable, documentation | question de recherche, méthodes, résultats, interprétation |
| Type de ressource | logiciel | prépublication/publication |
| Sens de la version | release du code | révision du manuscrit |
| Cible principale de la citation | version exacte du logiciel exécuté | version du document lue et discutée |
| Identifiant | DOI du logiciel | DOI/identifiant de la prépublication |

Évitez donc les pratiques suivantes.

- placer le DOI d’une prépublication dans le champ DOI du logiciel de `CITATION.cff`
- mélanger un fichier de prépublication à une archive logicielle et réduire les deux à un seul type de ressource
- réutiliser le DOI d’un article de revue comme DOI pour un dépôt de code complémentaire
- forcer les versions des releases du code et les révisions du manuscrit à suivre le même schéma de numérotation

Reliez plutôt les relations dans les métadonnées de l’archive.

- le logiciel **IsSupplementTo** l’article
- le logiciel **IsDocumentedBy** l’article ou une notice de documentation distincte
- l’article **References** le logiciel
- le logiciel **Requires** le jeu de données d’entrée ; le jeu de données **IsRequiredBy** le logiciel

Vérifiez les noms réels des types de relation dans le vocabulaire de métadonnées de l’archive et contrôlez leur direction. Mieux vaut fournir des identifiants associés lisibles par machine que de se contenter de descriptions en prose.

## 9. Figer ensemble le code source, l’environnement et les données

Même avec un DOI logiciel, il est impossible de reproduire les résultats sans les dépendances et les entrées.

### Code source

- tag et commit exacts
- révisions des sous-modules
- version du générateur pour le code source généré
- scripts de build

### Environnement

- fichier de verrouillage des dépendances
- version du compilateur/de l’interpréteur
- système d’exploitation et architecture
- bibliothèques numériques et runtime de l’accélérateur
- digest du conteneur ou export de l’environnement

Enregistrer uniquement le tag de conteneur `latest` peut pointer vers une autre image au fil du temps. Enregistrez également un digest immuable.

### Données et configuration

- version/DOI du jeu de données d’entrée
- somme de contrôle du fichier
- code et ordre du prétraitement
- fichier de configuration
- graine aléatoire et manifeste de partitionnement
- schéma et unités

Si les données brutes ne peuvent pas être publiées, fournissez un exemple synthétique ou minimal, un schéma, un générateur et les conditions d’accès, puis indiquez quels composants privés limitent la reproduction complète.

## 10. Garde-fous de release automatisables

Un workflow CI de release peut vérifier au moins les éléments suivants.

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

L’attribution d’un DOI est elle-même une publication qui modifie un état externe ; une simulation et une revue humaine sont donc plus sûres. Une notice d’archive publiée ne doit pas être traitée comme une branche ordinaire.

## 11. Runbook de release

### Préparation

- Classer les changements de périmètre et de compatibilité.
- Choisir la version.
- Rédiger le changelog et les notes de migration.
- Examiner les dépendances obsolètes et les licences.
- Examiner les métadonnées des auteurs de la citation et des contributeurs.

### Vérification

- Construire dans un environnement propre.
- Réexécuter l’exemple minimal depuis le début.
- Vérifier les commandes qui génèrent les principales figures et les principaux tableaux.
- Vérifier les tolérances numériques et les différences entre plateformes.
- Extraire et exécuter l’ensemble source exact qui sera archivé.

### Publication

- Fusionner le commit de release.
- Appliquer une politique de tag annoté/signé s’il en existe une.
- Publier les notes de release et les sommes de contrôle des artefacts.
- Effectuer une revue finale des métadonnées de la notice d’archive, puis la publier.
- Relier le DOI de version à la release et au CFF.

### Après la publication

- Confirmer que le DOI se résout vers la bonne page de présentation.
- Vérifier la liste des fichiers et leurs sommes de contrôle dans l’archive.
- Confirmer que les DOI de concept et de version apparaissent comme prévu.
- Mettre à jour les identifiants associés dans le dépôt, la documentation et la prépublication.
- Créer une issue de runbook pour la release suivante.

## 12. Liste de contrôle de vérification

- [ ] Les rôles du dépôt, du commit, du tag, de la release et de l’archive ont-ils été distingués ?
- [ ] Les versions du tag, du package, de la documentation, du CFF et de l’archive correspondent-elles ?
- [ ] Existe-t-il une politique interdisant le déplacement des tags publiés ?
- [ ] L’exemple de bout en bout s’exécute-t-il dans un environnement propre ?
- [ ] Les versions des dépendances et des données d’entrée sont-elles figées ?
- [ ] `CITATION.cff` est-il à la racine et passe-t-il un validateur ?
- [ ] Le titre du logiciel, l’ordre des créateurs, la version et la licence correspondent-ils aux métadonnées de l’archive ?
- [ ] Les usages du DOI de version et du DOI de concept sont-ils distingués ?
- [ ] Les DOI du logiciel sont-ils gérés séparément des DOI de prépublication/d’article ?
- [ ] Les DOI associés sont-ils reliés par des relations lisibles par machine ?
- [ ] Le code source et les archives sont-ils exempts de secrets, chemins personnels et données privées ?
- [ ] Un digest immuable est-il enregistré en plus du tag du conteneur ?
- [ ] Une personne examine-t-elle les métadonnées et l’ensemble de fichiers avant la publication du DOI ?

## 13. Pièges courants et limites

### « C’est dans Git, donc c’est conservé pour toujours »

Une URL d’hébergement et un compte ne sont pas des identifiants de conservation. Une archive et un DOI améliorent l’accessibilité à long terme, mais sans licence, métadonnées ni recette d’exécution, leur utilité reste limitée.

### « Cela possède un DOI, donc c’est reproductible »

Un DOI identifie un objet. Il ne fournit pas automatiquement les dépendances, les données, la configuration ni les tolérances numériques.

### Citer uniquement le DOI de concept le plus récent

Un lecteur peut recevoir une version ultérieure incompatible. Reproduire un résultat de recherche précis exige le DOI de version et la version de la release.

### Copier manuellement un DOI dans le README et créer des incohérences

Dans la mesure du possible, générez le CFF, les métadonnées du package, les notes de release et les métadonnées d’archive depuis une source unique, ou vérifiez-les entre elles dans la CI.

### Supposer que supprimer une notice d’un dépôt public supprime aussi ses secrets

Les secrets peuvent subsister dans l’historique, les forks, les journaux de CI, les artefacts de release et les archives. Après une exposition, ne vous contentez pas de les supprimer ; révoquez-les et faites-en immédiatement la rotation, puis inspectez chaque emplacement de conservation.

### Code source sans contrat d’exécution

Sans documentation sur les plateformes prises en charge, les tolérances, les composants non déterministes et la plage de temps d’exécution attendue, il est difficile de déterminer si un échec de reproduction est un bogue ou une différence d’environnement.

## 14. Références officielles

- [Recommandations officielles du Citation File Format](https://citation-file-format.github.io/)
- [Recommandations de GitHub sur les fichiers de citation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files)
- [Recommandations officielles pour conserver un dépôt GitHub avec un DOI](https://docs.github.com/repositories/archiving-a-github-repository/referencing-and-citing-content)
- [Cycle de vie des notices et versions Zenodo](https://help.zenodo.org/docs/deposit/about-records/)
- [Recommandations de Zenodo sur le versionnement des DOI](https://support.zenodo.org/help/en-gb/1-upload-deposit/97-what-is-doi-versioning)
- [Recommandations de Zenodo sur la réservation d’un DOI](https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/)
- [Définitions des relations d’identifiants associés DataCite](https://datacite-metadata-schema.readthedocs.io/en/4.6/appendices/appendix-1/relationType/)

## Conclusion

Les liens essentiels d’un logiciel de recherche reproductible sont les suivants.

~~~text
result
  -> input/data version
  -> configuration
  -> software version DOI
  -> release tag
  -> exact commit
  -> locked environment
~~~

Un article ou une prépublication est un objet distinct qui explique ces liens et formule des affirmations à leur sujet. Séparez les DOI du logiciel et des documents, puis reliez-les avec des identifiants associés afin de préserver à la fois le crédit et la reproductibilité.

Une bonne release n’est pas simplement « le jour où le code a été publié ». C’est l’état dans lequel une tierce partie n’a plus à deviner quelle version obtenir, quel environnement utiliser ni quoi exécuter.
