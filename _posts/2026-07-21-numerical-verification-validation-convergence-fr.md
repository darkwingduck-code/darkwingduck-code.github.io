---
title: "Vérification et validation des résultats numériques : convergence, indépendance du maillage et du pas de temps, conservation"
date: 2026-07-21 09:20:00 +0900
categories: [Scientific Computing, Verification and Validation]
tags: [verification, validation, convergence, mesh-independence, time-step, conservation, numerical-error]
description: "Une démarche pour distinguer la vérification du code, la vérification de la solution et la validation expérimentale, puis évaluer la fiabilité des résultats numériques par la convergence, l’indépendance du maillage et du pas de temps, et la conservation."
math: true
lang: fr-FR
hidden: true
translation_key: numerical-verification-validation-convergence
---

{% include language-switcher.html %}

Des contours plausibles et des courbes lisses ne prouvent pas l’exactitude d’un calcul. Pour qu’une simulation numérique soit digne de confiance, il faut au minimum distinguer les questions suivantes.

- Le code résout-il correctement les équations ?
- Les erreurs de discrétisation et d’itération de ce calcul sont-elles suffisamment faibles ?
- Les équations et les données d’entrée choisies décrivent-elles suffisamment bien les grandeurs réelles qui nous intéressent ?
- Cette conclusion est-elle valable pour l’usage prévu et dans la tolérance admise ?

Regrouper ces questions sous le seul mot « vérification » empêche de savoir ce qui a été établi et ce qui reste à examiner. C’est précisément pourquoi on distingue verification et validation.

## 1. La frontière entre verification et validation

| Niveau | Question centrale | Éléments de preuve représentatifs |
|---|---|---|
| code verification | Les équations ont-elles été implémentées comme prévu ? | exact solution, manufactured solution, benchmark, unit test |
| solution verification | Quelle est l’erreur numérique du calcul actuel ? | iterative convergence, mesh/time-step refinement, error estimate |
| validation | Le modèle reproduit-il les grandeurs réelles pertinentes pour l’objectif visé ? | comparaison avec des mesures indépendantes, validation uncertainty, applicability |
| calibration | Des parameter inconnus ont-ils été estimés à partir des données ? | objective/likelihood, posterior, identifiability |

En bref, la verification consiste à demander « résout-on correctement les équations ? », tandis que la validation revient plutôt à demander « a-t-on choisi les bonnes équations ? ». La validation ne démontre toutefois pas qu’un modèle est vrai dans l’absolu. Elle accumule des **éléments de preuve relatifs à un usage, à une plage de conditions et à des grandeurs d’intérêt précis**.

Employer les mêmes données pour la calibration et la validation revient à demander au modèle de retrouver ce qu’il a déjà vu. Il faut si possible séparer ces jeux de données ; si leur rareté impose de les réutiliser, il faut indiquer explicitement qu’il ne s’agit pas d’une vérification indépendante.

## 2. Commencer par décomposer les erreurs

L’écart entre le résultat calculé et la réalité mêle plusieurs causes.

$$
\text{écart total}
=
\text{erreur de forme du modèle}
+\text{incertitude sur les paramètres et les entrées}
+\text{erreur de discrétisation}
+\text{erreur d’itération}
+\text{erreur d’implémentation}
+\text{erreur de mesure}.
$$

Cette expression ne constitue pas un modèle probabiliste rigoureux dans lequel les termes seraient simplement additifs et indépendants. Il s’agit d’une décomposition conceptuelle destinée à ne négliger aucune cause. Ces contributions peuvent interagir et ne sont pas toujours entièrement séparables à partir des seules observations.

Un bon plan de V&V commence par définir les quantity of interest (QoI). Plutôt que de considérer tout le field, il précise quelle moyenne, quelle valeur maximale, quelle quantité intégrée, quel temps d’arrivée ou quel flux de bord intervient dans la décision. La convergence du maillage et les résultats de validation peuvent varier d’une QoI à l’autre.

## 3. Code verification : rechercher les erreurs d’implémentation

### Exact solution et benchmark

Lorsqu’une analytic solution existe pour des conditions aux limites ou une géométrie simplifiées, elle permet de comparer directement l’erreur de calcul. Même si le cas diffère d’un production case complexe, il reste précieux pour tester isolément l’opérateur, les conditions aux limites et l’implémentation du source term.

### Method of Manufactured Solutions

On choisit d’abord une fonction régulière \(u_m(x,t)\), puis on la substitue dans l’opérateur \(\mathcal L\) de la governing equation afin de construire le source

$$
f_m=\mathcal L(u_m)
$$

Si le code est configuré pour résoudre

$$
\mathcal L(u)=f_m
$$

on connaît la solution exacte \(u_m\) et l’on peut tester conjointement l’interior operator, la boundary condition, l’intégration temporelle et l’observed order.

Une manufactured solution n’a pas besoin de représenter un phénomène réel. Elle doit en revanche respecter les conditions suivantes.

- Activer tous les termes principaux du chemin de code.
- Ne pas masquer les bugs par une symétrie excessive.
- Posséder la différentiabilité nécessaire.
- Déduire de façon cohérente les conditions aux limites et le source.

### Implémentations indépendantes et limiting case

Le fait que des codes différents produisent le même résultat est un indice utile, mais ils peuvent partager des hypothèses ou des bugs communs. Il faut donc le combiner à d’autres types de preuves : limites dans lesquelles un term tend vers zéro, symmetry, analyse dimensionnelle ou lois de conservation.

## 4. Solution verification : l’erreur numérique du calcul actuel

### Séparer iterative error et discretization error

Modifier le maillage avant que le solver linéaire ou non linéaire ait suffisamment convergé mélange iterative error et discretization error. Sur chaque maillage, la residual tolerance doit être suffisamment inférieure aux écarts de discrétisation ; il faut aussi vérifier la stabilité des QoI, pas seulement le residual.

La diminution de l’algebraic residual ne garantit pas nécessairement celle de la solution error. Dans un badly conditioned system, un faible residual peut coexister avec une forte solution error.

### Domaine de convergence asymptotique

Si \(h\) désigne le pas du maillage et \(p\) l’ordre théorique, on s’attend, pour un maillage suffisamment fin, à une relation de la forme

$$
\phi(h)=\phi_0+Ch^p+\mathcal O(h^{p+1})
$$

où \(\phi\) est une QoI. Lorsque le refinement ratio est constant et que

$$
h_3=rh_2=r^2h_1,\qquad r>1
$$

avec \(h_1\) le maillage le plus fin, l’observed order peut être estimé par

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

Dans le domaine asymptotique et en présence d’une convergence monotone, la Richardson extrapolation donne

$$
\phi_{\mathrm{ext}}
=
\phi_1+
\frac{\phi_1-\phi_2}{r^{p_{\mathrm{obs}}}-1}
$$

Si les trois valeurs convergent de manière oscillatoire ou si leurs écarts sont du même ordre que le noise, cette formule devient instable. Plutôt que de produire systématiquement un apparent order unique, il faut d’abord présenter la forme de la convergence et vérifier que les hypothèses sont satisfaites.

## 5. Pourquoi employer avec prudence l’expression « indépendance du maillage »

Sur un maillage fini, il est rare que la discretization error soit exactement nulle. Mieux vaut donc fournir les informations concrètes suivantes que déclarer une simple « indépendance ».

- La refinement family employée et le \(h\) caractéristique
- Le refinement ratio
- Le nombre de cell/DOF de chaque maillage
- La qualité du maillage et la résolution de la couche limite
- Les valeurs et variations relatives de chaque QoI
- L’observed order ou l’error estimate
- Le critère de tolérance ayant conduit au choix du maillage final

La proximité des résultats de deux maillages ne suffit pas. Elle peut provenir d’une compensation fortuite des erreurs, d’une non-monotonic convergence ou d’un même goulot d’étranglement de résolution. Si possible, on utilise au moins trois niveaux et l’on vérifie que les maillages forment une systematic refinement family partageant la même topology et la même stretching rule.

### Les grandeurs locales et intégrales ne convergent pas de la même manière

Une domain average ou un integral flux peut être stable alors qu’un point maximum, un gradient ou la position d’une discontinuité converge lentement. L’étude de maillage doit être menée pour chacune des QoI à présenter. Si la position du « maximum » se déplace d’un maillage à l’autre, il ne faut pas comparer directement la valeur des cells de même index.

## 6. Indépendance du pas de temps et combinaison des erreurs spatiales et temporelles

Pour le pas de temps \(\Delta t\), on peut également mener une refinement study de la forme

$$
\phi(\Delta t)=\phi_0+C_t(\Delta t)^q+\cdots
$$

Cependant, si l’erreur spatiale est grande, réduire le pas de temps peut ne produire aucun changement visible ; la réciproque est également vraie.

Une séquence pratique est la suivante.

1. Évaluer le spatial refinement avec un \(\Delta t\) suffisamment petit.
2. Évaluer le refinement de \(\Delta t\) sur le fine mesh retenu.
3. Au voisinage de la combinaison finale, faire varier ensemble le mesh et \(\Delta t\) afin d’examiner leur interaction.
4. En cas d’adaptive time stepping, consigner non seulement un nominal step, mais aussi la tolerance, l’accepted step history et les rejected steps.

Satisfaire une condition de stabilité et atteindre une précision suffisante sont deux choses différentes. L’absence de divergence d’une implicit method avec un grand pas de temps ne signifie pas que la transient phase et le peak time sont correctement résolus.

## 7. Conservation : un élément de preuve robuste, indépendant du graphe de convergence

Dans le control volume \(\Omega\) d’un problème conservatif, le bilan général s’écrit

$$
\frac{d}{dt}\int_{\Omega}U\,d\Omega
+
\int_{\partial\Omega}F\cdot n\,dS
=
\int_{\Omega}S\,d\Omega
$$

Dans un discrete calculation, on calcule sur un intervalle de temps donné

$$
\Delta \text{stockage}
+\text{débit net sortant}
-\text{source}
=
\text{défaut de bilan}
$$

La seule valeur absolue du defect compare mal des cases d’échelles différentes. On examine aussi une normalized balance error obtenue en divisant par un flux représentatif ou par la storage change. Si le denominator est proche de zéro, l’erreur relative explose ; il faut donc présenter simultanément la valeur absolue et l’échelle de référence.

La conservation est une condition nécessaire, mais non suffisante. On peut respecter la global conservation tout en répartissant incorrectement une même quantité entre différents emplacements. Il convient donc de distinguer les niveaux suivants.

- local cell balance
- flux balance pour chaque boundary
- global domain balance
- balance par espèce ou composant
- coupled balance, par exemple énergie, masse et quantité de mouvement

## 8. Concevoir une comparaison de validation

### Définir à l’avance la validation metric

Plutôt que de regarder une figure et de conclure que les courbes « se ressemblent », on définit d’abord la QoI et la metric. Par exemple :

- bias et normalized error
- profile norm
- amplitude et position du peak
- integral quantity
- temporal phase error
- coverage ou probabilistic score

### Combiner les incertitudes

Pour interpréter l’écart calcul-mesure

$$
E=S-D
$$

il faut tenir compte à la fois de la simulation numerical uncertainty, de l’input uncertainty et de la measurement uncertainty. Un faible \(|E|\) ne suffit pas à conclure que le modèle est juste ; il faut également vérifier si une uncertainty band très large ne masque pas simplement l’écart.

### Délimiter le validation domain

Une extrapolation hors de la plage de conditions validée bénéficie d’éléments de preuve plus faibles. Il faut consigner l’espace des entrées, le boundary regime, les dimensionless groups ainsi que la plage de material/state, puis évaluer la distance entre le prediction point et le validation domain.

## 9. Workflow de V&V recommandé

1. **Définir l’usage prévu et la tolérance** : préciser la décision concernée et les QoI employées.
2. **Établir la hiérarchie du modèle** : distinguer governing equation, closure, boundary/initial condition et source des parameters.
3. **Code verification** : tester l’implémentation par unit test, exact/MMS, limiting case et benchmark.
4. **Iterative convergence** : examiner ensemble l’equation residual et l’historique des QoI.
5. **Spatial refinement** : comparer au moins trois niveaux d’une systematic mesh family.
6. **Temporal refinement** : inclure les QoI temporelles, la phase et l’instant du peak.
7. **Contrôle de conservation** : calculer automatiquement les balances local, boundary et global.
8. **Propagation de l’incertitude des entrées** : intégrer l’input uncertainty à la validation comparison.
9. **Validation indépendante** : comparer avec des données non utilisées pour la calibration et au moyen de metrics définies à l’avance.
10. **Documenter le champ d’application et les limites** : signaler les regimes non validés et la dominant uncertainty.

## 10. Checklist de vérification

- [ ] A-t-on distingué verification, validation et calibration ?
- [ ] Les QoI et la tolerance utilisées pour la décision ont-elles été définies en premier ?
- [ ] Le test analytic/MMS active-t-il les principaux terms du production code ?
- [ ] L’iterative error est-elle suffisamment inférieure aux écarts entre maillages ?
- [ ] A-t-on employé au moins trois niveaux de systematic refinement ?
- [ ] A-t-on vérifié l’observed order, et pas seulement le theoretical order ?
- [ ] A-t-on distingué les convergences monotonic, oscillatory et divergent ?
- [ ] Les spatial et temporal refinements ont-ils été menés séparément ?
- [ ] A-t-on vérifié la conservation local/boundary, et pas seulement global ?
- [ ] Les données de calibration et de validation ont-elles été séparées ?
- [ ] Les measurement, input et numerical uncertainties ont-elles été présentées ensemble ?
- [ ] L’extrapolation hors du validation domain a-t-elle été signalée ?

## 11. Pièges fréquents

### Conclure qu’un faible residual garantit la bonne solution

Le residual indique seulement dans quelle mesure l’équation algébrique discrète a été résolue. Il ne renseigne ni sur la discretization error ni sur la model-form error.

### Comparer seulement deux maillages et déclarer l’indépendance

Une coïncidence fortuite entre deux valeurs ne démontre ni l’ordre de convergence ni l’entrée dans le domaine asymptotique. Il faut au moins trois niveaux et examiner le motif de convergence.

### Évaluer tous les fields avec une metric unique

Même si la moyenne est correcte, le peak, le gradient ou la phase peuvent être faux. Plusieurs QoI adaptées à l’objectif sont nécessaires.

### Présenter les performances de calibration comme des performances de validation

L’ajustement aux données ayant servi à régler les parameters est un résultat de calibration. Évaluer la predictive adequacy exige des informations indépendantes.

### Supposer qu’un maillage plus fin est toujours plus précis

Une mauvaise boundary condition, une iterative tolerance insuffisante, une mauvaise mesh quality ou un scheme instable ne sont pas corrigés par la seule augmentation des DOF.

## 12. Limites et principes de compte rendu

Dans les problèmes non linéaires ou multi-échelles complexes, il peut être impossible d’atteindre un domaine asymptotique net. Les discontinuities, moving interfaces, chaotic dynamics et adaptive meshes affaiblissent les hypothèses de l’analyse simple de Richardson. Plutôt que de forcer la présentation d’une « erreur exacte unique », il faut alors exposer avec transparence la stabilité de la conclusion à plusieurs résolutions, la source d’erreur dominante et ce qui n’a pas pu être vérifié.

Le produit d’une démarche de V&V n’est pas un tampon de conformité. C’est **un réseau d’éléments de preuve qui soutient une conclusion**. Voilà pourquoi la solver tolerance, la refinement family, le balance defect, l’incertitude et le champ d’application comptent davantage que les figures.
