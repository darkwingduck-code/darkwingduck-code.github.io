---
title: "De la planification d’expériences à l’UQ et au calibrage : une carte complète pour concevoir une étude de simulation"
date: 2026-07-21 09:30:00 +0900
categories: [Scientific Computing, Research Methods]
tags: [doe, sensitivity-analysis, uncertainty-quantification, calibration, identifiability, surrogate-model]
description: "Distinguer la planification d’expériences, les sensibilités locale et globale, la propagation des incertitudes et le calibrage des paramètres, puis les relier dans un flux de travail reproductible d’étude par simulation."
math: true
lang: fr-FR
translation_key: doe-sensitivity-uq-calibration
hidden: true
---

{% include language-switcher.html %}

Modifier quelques entrées d’une simulation et comparer les courbes de sortie ne suffit pas à étayer des conclusions solides. Les effets des variables, leurs interactions, l’incertitude des entrées, l’estimation des paramètres et l’erreur du modèle se retrouvent alors entremêlés.

Pour les séparer, il faut d’abord distinguer le rôle de quatre outils.

- **Planification d’expériences (DOE)** : décide quelles combinaisons d’entrées calculer ou mesurer.
- **Analyse de sensibilité (SA)** : cherche quelle part de la variation de sortie est expliquée par chaque entrée.
- **Quantification des incertitudes (UQ)** : cherche comment l’incertitude des entrées et des modèles se propage dans celle des sorties.
- **Calibrage** : utilise des observations pour estimer les paramètres inconnus.

Ces outils sont complémentaires, mais ne se remplacent pas. Une bonne planification d’expériences ne quantifie pas automatiquement l’incertitude, et un bon ajustement de calibrage ne signifie pas que la validation est terminée.

## 1. Premier tableau à construire : classification des entrées et des incertitudes

Ne traitez pas toutes les entrées \(x=(x_1,\dots,x_d)\) comme si elles étaient de même nature.

| Classe | Signification | Traitement courant |
|---|---|---|
| facteur contrôlable | Le concepteur choisit ses niveaux | plan factoriel ou optimal |
| variable de scénario ou de contexte | Possède une plage d’intérêt, mais n’est pas directement contrôlée | mise en blocs, stratification |
| variable aléatoire | Modélisée comme une variabilité intrinsèque | loi de probabilité et propagation directe |
| paramètre épistémique | Incertain faute de connaissances suffisantes | calibrage, mise à jour d’un intervalle ou d’un a priori |
| paramètre de nuisance | N’est pas lui-même d’intérêt, mais influe sur les résultats | marginalisation, profilage |
| écart du modèle | Différence entre la structure des équations et la réalité | modèle d’écart distinct ou budget de biais |

Une même grandeur physique peut être classée différemment selon l’objectif. Plus que son nom, il importe de décider à l’avance **quelles informations serviront à la mettre à jour et de quelle manière**.

Chaque entrée doit posséder au minimum les métadonnées suivantes :

- définition et unités
- plage autorisée et justification
- distribution ou niveaux du plan
- corrélations et contraintes entre entrées
- statut fixe ou estimé
- caractère mesurable ou non
- emplacement de son intervention dans le modèle

## 2. DOE : transformer un budget d’exécution en information

### Limites de la variation d’un seul facteur à la fois

La méthode OFAT, qui modifie une variable à la fois, est facile à comprendre, mais elle ignore les interactions. Par exemple,

$$
y=\beta_0+\beta_1x_1+\beta_2x_2+\beta_{12}x_1x_2
$$

lorsque \(\beta_{12}\) est grand, l’effet de \(x_1\) change avec le niveau de \(x_2\). Une étude OFAT autour d’un seul point de référence permet difficilement d’identifier cette structure.

### Types de plans et objectifs

| Plan | Avantage | Point d’attention |
|---|---|---|
| factoriel complet | Estime systématiquement les effets principaux et les interactions | Le nombre d’exécutions explose avec la dimension |
| factoriel fractionnaire | Effectue un criblage avec moins d’exécutions | La structure d’alias doit être interprétée |
| composite centré / Box–Behnken | Efficace pour une surface de réponse quadratique | Vulnérable à l’extrapolation hors de la région définie |
| hypercube latin | Stratifie uniformément chaque axe | Vérifier la qualité des projections et les corrélations |
| suite à faible discrépance | Bien adaptée à l’intégration et à l’analyse de sensibilité globale | La distinguer de répétitions aléatoires indépendantes |
| plan D-/I-optimal | Optimisé pour l’objectif d’un modèle de régression donné | L’efficacité chute si le modèle supposé est erroné |
| plan adaptatif ou séquentiel | Concentre le budget dans les régions incertaines ou importantes | Gérer la règle d’arrêt et le biais de sélection |

La DOE ne consiste pas uniquement à « remplir uniformément l’espace ». Un bon plan dépend de l’objectif : criblage, entraînement d’un substitut, optimisation, identification de paramètres ou validation.

### Randomisation, répétition et mise en blocs

- **La randomisation** réduit le risque de confondre une dérive temporelle ou un effet d’ordre avec un facteur particulier.
- **La répétition** estime la variation dans des conditions identiques. Pour un simulateur entièrement déterministe, répéter simplement l’exécution avec le même binaire et le même environnement n’apporte aucune information nouvelle ; en revanche, la répétition est nécessaire pour un solveur stochastique ou une exécution non déterministe.
- **La mise en blocs** sépare les variations de nuisance difficiles à éliminer, telles que l’équipement, le lot, la date ou la famille de maillages.

Même dans une campagne de simulation, l’ordre des exécutions, l’environnement de calcul et la version du solveur peuvent constituer des variables de bloc ou de provenance.

## 3. Analyse de sensibilité : commencer par choisir une définition de l’influence

La « variable la plus importante » change avec la métrique.

### Sensibilité locale

La dérivée autour d’un point de référence \(x_0\),

$$
S_i^{\mathrm{local}}
=
\left.
\frac{\partial f}{\partial x_i}
\right|_{x=x_0}
$$

décrit l’effet d’une petite perturbation. Lorsque les unités diffèrent, envisagez un indice sans dimension tel que

$$
S_i^{\mathrm{scaled}}
=
\frac{x_i}{f}
\frac{\partial f}{\partial x_i}
$$

Les dérivées locales sont efficaces pour l’optimisation par gradient et l’incertitude linéarisée, mais elles peuvent manquer la non-linéarité, les seuils, les interactions et la dépendance au point de référence.

### Criblage : famille de Morris

Lorsque l’on recueille les effets élémentaires obtenus en déplaçant une fois chaque entrée à plusieurs emplacements, leur valeur absolue moyenne indique l’influence globale, tandis que leur variance signale une éventuelle non-linéarité ou des interactions. Cette méthode est utile pour éliminer les variables peu importantes en grande dimension, mais elle ne constitue pas une décomposition exacte de la variance.

### Sensibilité globale fondée sur la variance

Sous l’hypothèse d’entrées indépendantes, la variance de sortie peut être décomposée sous forme ANOVA.

$$
\operatorname{Var}(Y)
=
\sum_i V_i
+\sum_{i<j}V_{ij}
+\cdots
$$

L’indice de Sobol de premier ordre et l’indice d’effet total peuvent s’écrire

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

\(S_i\) représente l’effet propre de \(X_i\), tandis que \(S_{T_i}\) inclut toutes les interactions impliquant \(X_i\). Une grande différence \(S_{T_i}-S_i\) indique que les interactions sont importantes.

### Le piège des entrées corrélées

La décomposition de Sobol standard suppose les entrées indépendantes. Si les combinaisons physiquement réalisables présentent des corrélations ou des contraintes, un échantillonnage indépendant peut créer des états impossibles. Dans ce cas, envisagez des méthodes respectant la structure de dépendance, telles que l’échantillonnage conditionnel, les indices groupés et les effets de Shapley, et indiquez la distribution jointe utilisée.

## 4. UQ : propager l’incertitude vers une distribution de sortie

Le problème élémentaire d’UQ directe consiste à estimer la distribution, la moyenne, la variance, les quantiles et la probabilité de défaillance de \(Y\) dans

$$
X\sim p_X(x),\qquad Y=f(X)
$$

### Monte-Carlo

Générez des échantillons indépendants \(x^{(j)}\) et calculez \(y^{(j)}=f(x^{(j)})\). Cette approche, simple à mettre en œuvre, est relativement peu sensible à la dimension, mais coûteuse pour les événements rares ou les simulations onéreuses. Présentez l’erreur type de Monte-Carlo ou l’intervalle de confiance avec le nombre d’échantillons.

### UQ fondée sur un modèle de substitution

Lorsque le modèle d’origine est coûteux, utilisez une surface de réponse, un processus gaussien, un chaos polynomial, un substitut neuronal ou un modèle analogue. L’erreur totale se sépare alors au moins en termes suivants.

$$
\text{Erreur UQ}
=
\text{erreur d’échantillonnage}
+\text{erreur du substitut}
+\text{erreur du modèle d’entrée}
+\text{erreur numérique de simulation}.
$$

Une faible erreur de test du substitut ne garantit pas à elle seule des probabilités de queue ou des indices de sensibilité exacts. Examinez séparément l’erreur dans les régions importantes pour l’objectif d’UQ, notamment près des frontières, des queues et des contraintes.

### Événements rares

Lorsque la probabilité de défaillance est faible, une méthode de Monte-Carlo brute ne produit presque aucun échantillon de défaillance. Des méthodes comme l’échantillonnage préférentiel, la simulation par sous-ensembles, le fractionnement ou les substituts adaptatifs peuvent être nécessaires. Si la proposition a été ajustée arbitrairement après observation des résultats, examinez le biais de l’estimateur et le calcul des poids.

## 5. Calibrage : estimer les paramètres comme un problème inverse

Étant donné des observations \(d\), un simulateur \(f(\theta,z)\), un paramètre \(\theta\) et des conditions d’observation \(z\), écrivons

$$
d=f(\theta,z)+\delta(z)+\varepsilon
$$

- \(\delta(z)\) : écart du modèle
- \(\varepsilon\) : bruit de mesure

### Point de vue de l’optimisation

Les moindres carrés pondérés s’écrivent

$$
\hat\theta
=
\arg\min_\theta
(d-f(\theta))^\mathsf T
\Sigma^{-1}
(d-f(\theta))
$$

On peut ajouter des bornes, une régularisation ou une pénalité a priori.

### Point de vue bayésien

$$
p(\theta\mid d)
\propto
p(d\mid\theta)p(\theta)
$$

La vraisemblance représente ici la structure des résidus de mesure et de modèle, tandis que l’a priori représente les informations disponibles avant l’observation. Le résultat est une distribution a posteriori et non une estimation ponctuelle unique.

Les méthodes bayésiennes ne fournissent pas automatiquement une incertitude correcte lorsque la vraisemblance ou le modèle d’écart est erroné. Un a posteriori étroit signifie que l’information est concentrée sous les hypothèses du modèle ; il ne signifie pas que toutes les erreurs réelles sont faibles.

## 6. Identifiabilité : réussir l’optimisation n’équivaut pas à apprendre les paramètres

### Identifiabilité structurelle

Si des paramètres différents produisent la même sortie même en supposant un bruit nul et des observations continues, ces paramètres ne sont pas structurellement identifiables.

### Identifiabilité pratique

Même des paramètres théoriquement identifiables sont difficiles à distinguer à partir des données réelles lorsque les emplacements d’observation, les plages, le bruit ou l’excitation des entrées sont insuffisants.

Les diagnostics suivants sont utiles :

- spectre singulier du jacobien ou de l’information de Fisher
- vraisemblance de profil des paramètres
- corrélation a posteriori
- optimisation depuis plusieurs valeurs initiales
- test de récupération synthétique
- information attendue dans de nouvelles conditions d’observation

Lorsque les paramètres sont fortement corrélés, leurs valeurs individuelles peuvent être instables alors qu’une combinaison particulière ou une prédiction reste stable. Il faut distinguer si l’objectif porte sur les paramètres eux-mêmes ou sur la prédiction.

## 7. Confusion entre écart du modèle et paramètres

Si l’erreur de structure du modèle \(\delta(z)\) est ignorée, les paramètres peuvent l’absorber. Ces « paramètres effectifs » ajustent bien les conditions de calibrage, mais peuvent perdre leur sens physique ou leur pouvoir prédictif dans de nouvelles conditions.

À l’inverse, si l’on autorise un modèle d’écart très souple, \(\delta\) peut expliquer toute différence et empêcher l’apprentissage des paramètres. Un problème qui estime simultanément et librement les paramètres et l’écart peut être intrinsèquement confondu.

Les stratégies d’atténuation comprennent :

- inclure des conditions et des types d’observations variés
- concevoir des grandeurs d’intérêt sensibles à chaque paramètre
- utiliser des a priori et des bornes justifiés physiquement
- contraindre la régularité et la structure de l’écart
- séparer les conditions de calibrage et de validation
- présenter séparément l’incertitude des paramètres et l’écart prédictif

## 8. Flux de travail de bout en bout recommandé

### Étape 1 : définir l’objectif et les sorties

Fixez d’abord la décision, la grandeur d’intérêt, l’erreur acceptable et la plage d’entrées étudiée. Au lieu de demander un « bon ajustement du modèle », indiquez quelles prédictions seront étayées et sur quelle plage.

### Étape 2 : auditer les entrées

Construisez un tableau des unités, plages, distributions jointes, contraintes physiques et sources d’information des entrées. Distinguez l’incertitude épistémique de l’incertitude aléatoire ; si la frontière est ambiguë, traitez plusieurs interprétations comme des scénarios.

### Étape 3 : DOE de criblage

En grande dimension, éliminez les variables à faible impact avec des plans factoriels ou fractionnaires, des méthodes de Morris, un criblage par dérivées ou des outils analogues. Consignez le seuil de criblage et les interactions susceptibles d’être manquées.

### Étape 4 : DOE à remplissage d’espace ou orientée vers l’objectif

Choisissez un hypercube latin, une suite à faible discrépance ou un plan optimal selon l’objectif : modèle de substitution, analyse de sensibilité globale ou calibrage. Excluez les combinaisons physiquement impossibles au moyen d’un échantillonnage respectant les contraintes.

### Étape 5 : contrôle de la qualité numérique

Consignez pour chaque exécution la convergence, la conservation, le code d’échec et la provenance du maillage ou du pas de temps. La simple suppression des échecs du solveur peut déformer la région réalisable estimée ; gérez donc l’échec lui-même comme un résultat.

### Étape 6 : validation du substitut

Utilisez un plan de test indépendant de l’entraînement. Vérifiez non seulement l’erreur moyenne, mais aussi la pire région, les queues, les dérivées et la région où se concentrera l’a posteriori du calibrage.

### Étape 7 : analyse de sensibilité globale et UQ directe

Indiquez le modèle d’entrée joint et calculez également l’incertitude de Monte-Carlo des indices de sensibilité. Vérifiez si le classement d’importance des entrées reste stable par rapport au nombre d’échantillons et au choix du substitut.

### Étape 8 : calibrage

Consignez la vraisemblance, l’a priori, les bornes, les hypothèses d’écart ainsi que les diagnostics de l’optimiseur ou de l’échantillonneur. Vérifiez l’identifiabilité par une récupération synthétique et des exécutions à démarrages multiples.

### Étape 9 : validation

Comparez les observations à la distribution prédictive dans des conditions et pour des grandeurs d’intérêt qui n’ont pas été utilisées. Évaluez la prédiction hors échantillon plutôt que les résidus de calibrage.

### Étape 10 : mise à jour séquentielle

Sélectionnez la prochaine exécution ou mesure qui réduira le plus l’incertitude actuelle. Définissez à l’avance la règle d’acquisition et le critère d’arrêt afin d’éviter une exploration sans fin.

## 9. Liste de contrôle de la vérification

- [ ] Les objectifs de la DOE, de l’analyse de sensibilité, de l’UQ et du calibrage restent-ils distincts ?
- [ ] Les plages et distributions des entrées ont-elles une justification technique ?
- [ ] Les corrélations et les contraintes physiques sont-elles reflétées dans l’échantillonnage joint ?
- [ ] A-t-on évité d’utiliser l’OFAT comme unique fondement pour conclure à l’absence d’interactions ?
- [ ] La répétition est-elle conçue en fonction du comportement déterministe ou stochastique ?
- [ ] La définition et les hypothèses de la métrique de sensibilité sont-elles indiquées ?
- [ ] L’incertitude d’échantillonnage de l’indice de sensibilité lui-même est-elle présentée ?
- [ ] L’erreur du substitut est-elle incluse dans les résultats d’UQ ou quantifiée séparément ?
- [ ] L’identifiabilité des paramètres de calibrage a-t-elle été diagnostiquée ?
- [ ] La possibilité que l’écart du modèle soit absorbé par les paramètres a-t-elle été examinée ?
- [ ] Les données de calibrage et de validation sont-elles séparées ?
- [ ] La graine aléatoire, le générateur du plan, l’ordre d’exécution et les exécutions échouées sont-ils conservés ?

## 10. Pièges fréquents et limites

### Croire que des plages plus larges sont toujours plus prudentes

Une distribution uniforme indépendante et exagérément large peut créer des combinaisons impossibles en réalité et modifier artificiellement le classement des sensibilités. Une plage doit refléter la faisabilité jointe aussi bien que la prudence.

### Croire qu’un coefficient de corrélation décrit toute la structure de dépendance

La corrélation linéaire peut ne pas décrire la dépendance dans les queues, les contraintes non linéaires ou la multimodalité.

### Se fier uniquement au score de test moyen du substitut

Une faible RMSE globale ne garantit pas l’exactitude autour d’un seuil, dans les queues ou dans les gradients. Les métriques de validation doivent correspondre à la tâche en aval.

### Interpréter l’a posteriori d’un paramètre comme une constante physique

Un paramètre de calibrage obtenu en ignorant l’écart du modèle peut être une valeur de correction dépendante des conditions.

### Supprimer toutes les variables insensibles

Une variable n’est insensible que pour la sortie et la plage actuelles ; cela ne garantit pas son absence d’importance pour une autre grandeur d’intérêt, un autre régime ou un événement de queue.

### Dimension excessive pour un faible budget de calcul

Mener simultanément une analyse de sensibilité globale en grande dimension et un calibrage flexible avec peu d’exécutions rend les estimateurs instables. Le criblage, la réduction structurelle de dimension et les mesures informatives doivent précéder ces étapes.

## Conclusion

Une étude de simulation solide ne naît pas d’un grand nombre d’exécutions, mais **d’exécutions dont les flux d’information sont séparés**. La DOE détermine où regarder, l’analyse de sensibilité explique ce qui compte, l’UQ calcule la portée de la conclusion et le calibrage met à jour les paramètres inconnus à partir des observations.

Enfin, la validation demande si les prédictions fondées sur toutes ces hypothèses restent adaptées à l’usage lorsqu’elles sont confrontées à de nouvelles informations. Le simple fait de séparer les questions et les données de ces quatre étapes réduit fortement le surajustement, la fausse précision et les paramètres ininterprétables.
