---
title: "Bien utiliser les moindres carrés : projection, conditionnement, QR et SVD"
date: 2026-07-21 09:10:00 +0900
categories: [Mathematics, Numerical Linear Algebra]
tags: [least-squares, projection, conditioning, qr, svd, pseudoinverse, regularization]
description: "Interpréter les moindres carrés comme un problème de projection orthogonale et relier nombres de condition, QR, SVD, pseudo-inverses et régularisation sous l’angle de la stabilité numérique."
math: true
lang: fr-FR
translation_key: least-squares-projection-conditioning-svd
hidden: true
---

{% include language-switcher.html %}

Lorsque l’équation d’observation \(Ax=b\) n’admet pas de solution exacte, on apprend souvent à « multiplier les deux membres par \(A^\mathsf T\) ». Pourtant, l’essence des moindres carrés ne réside pas dans la mémorisation d’une formule, mais dans trois questions.

1. Que cherchons-nous à minimiser ?
2. Pourquoi la solution est-elle liée à la projection orthogonale sur l’espace colonne ?
3. Quel algorithme calculera cette même solution mathématique de façon stable ?

Cet article organise en une progression cohérente la géométrie des moindres carrés, le danger des équations normales, le rôle de QR et de la SVD, la déficience de rang et la régularisation.

## 1. Définir le problème des moindres carrés

Pour \(A\in\mathbb R^{m\times n}\) et \(b\in\mathbb R^m\), le système surdéterminé \(Ax=b\) n’a généralement pas de solution exacte. Les moindres carrés minimisent la norme euclidienne du résidu

$$
r(x)=b-Ax
$$

de la manière suivante.

$$
x_\star
=
\arg\min_x \|Ax-b\|_2^2.
$$

\(Ax\) appartient toujours à \(\mathcal C(A)\), l’espace colonne de \(A\). Le problème consiste donc à trouver l’élément \(\hat b=Ax_\star\) de cet espace qui est le plus proche de \(b\).

## 2. Projection orthogonale et équations normales

Au point le plus proche, le résidu \(r_\star=b-Ax_\star\) est orthogonal à toutes les directions de l’espace colonne.

$$
A^\mathsf T r_\star=0.
$$

Développer cette expression donne les équations normales.

$$
A^\mathsf T A x_\star=A^\mathsf T b.
$$

Si \(A\) est de rang colonne plein, \(A^\mathsf T A\) est définie positive et la solution est unique.

$$
x_\star=(A^\mathsf T A)^{-1}A^\mathsf T b.
$$

Cette équation est cependant une **expression mathématique**, et non une procédure de calcul recommandée. Dans du code réel, mieux vaut généralement éviter à la fois de construire explicitement une inverse et de résoudre systématiquement les équations normales lorsque la précision importe.

La matrice de projection est

$$
P=A(A^\mathsf T A)^{-1}A^\mathsf T
$$

et \(\hat b=Pb\). Lorsque le rang colonne est plein, \(P\) vérifie

$$
P^\mathsf T=P,\qquad P^2=P
$$

La symétrie signifie que la projection est orthogonale, tandis que l’idempotence signifie que projeter une valeur déjà projetée ne la modifie pas.

## 3. Un exemple simple de régression

Supposons que nous ajustions un modèle linéaire \(y\approx\beta_0+\beta_1t\) à plusieurs points. La matrice de conception est

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

La solution des moindres carrés ne minimise pas la **distance perpendiculaire** entre les points et la droite. Elle minimise la somme des carrés des résidus dans la direction \(y\) spécifiée. Si les deux axes comportent des erreurs, une régression par distance orthogonale ou un modèle avec erreurs sur les variables peut être plus approprié.

De plus, si les valeurs absolues de \(t\) sont très grandes ou si son étendue se concentre d’un seul côté, il peut devenir numériquement difficile de distinguer la colonne de l’ordonnée à l’origine de celle de la pente. Centrer et mettre convenablement \(t\) à l’échelle améliore à la fois le nombre de condition et l’interprétation des coefficients.

## 4. Nombres de condition : amplification des erreurs d’entrée dans la solution

Le nombre de condition en norme 2 d’une matrice carrée inversible est

$$
\kappa_2(A)
=
\|A\|_2\|A^{-1}\|_2
=
\frac{\sigma_{\max}}{\sigma_{\min}}
$$

Pour une matrice rectangulaire de rang colonne plein, le rapport entre la plus grande valeur singulière et la plus petite valeur singulière non nulle a la même signification.

Un grand nombre de condition entraîne les phénomènes suivants.

- De petites erreurs dans l’entrée \(b\) sont fortement amplifiées dans \(x\).
- Des colonnes presque identiques font varier brutalement les coefficients.
- Les estimations des paramètres peuvent être instables même si le résidu est faible.
- Les erreurs d’arrondi en virgule flottante ont davantage d’effet.

Les équations normales présentent un problème décisif.

$$
\kappa_2(A^\mathsf T A)=\kappa_2(A)^2.
$$

Un nombre de condition déjà médiocre est mis au carré. Former \(A^\mathsf T A\) peut aussi faire perdre des chiffres significatifs.

> Un petit résidu et des paramètres exacts ne sont pas synonymes. Même si \(b\) est proche de l’espace colonne, des colonnes presque dépendantes peuvent permettre à des coefficients très différents de produire des prédictions semblables.

## 5. Résoudre les moindres carrés avec QR

Supposons que \(A\) soit de rang colonne plein et que

$$
A=QR,
$$

où les colonnes de \(Q\in\mathbb R^{m\times n}\) sont orthonormées et où \(R\in\mathbb R^{n\times n}\) est triangulaire supérieure. Alors

$$
\|Ax-b\|_2^2
=
\|Rx-Q^\mathsf Tb\|_2^2
+\|(I-QQ^\mathsf T)b\|_2^2.
$$

Comme le second terme ne dépend pas de \(x\), nous pouvons résoudre

$$
Rx=Q^\mathsf T b
$$

par remontée.

En pratique, la factorisation QR de Householder est généralement plus stable que Gram–Schmidt classique. En cas de doute sur le rang, utilisez une factorisation QR avec pivotement de colonnes

$$
AP=QR
$$

afin de placer les colonnes importantes en tête et de diagnostiquer le rang effectif.

## 6. SVD et pseudo-inverse

La SVD décompose une matrice comme suit :

$$
A=U\Sigma V^\mathsf T
$$

Les colonnes de \(U\) et de \(V\) sont orthonormées, et les éléments diagonaux \(\sigma_i\) de \(\Sigma\) sont les valeurs singulières.

La pseudo-inverse de Moore–Penrose est

$$
A^+=V\Sigma^+U^\mathsf T
$$

et la solution de norme minimale parmi toutes les solutions des moindres carrés est

$$
x_\star=A^+b
=
\sum_{\sigma_i>0}
\frac{u_i^\mathsf Tb}{\sigma_i}v_i
$$

Cette équation révèle directement l’origine du mauvais conditionnement. Dans les directions où \(\sigma_i\) est petite, même un faible bruit dans \(u_i^\mathsf Tb\) est amplifié par \(1/\sigma_i\).

### Quand la SVD est particulièrement utile

- Lorsqu’il existe ou que l’on soupçonne une déficience de rang
- Pour examiner le noyau et les directions identifiables
- Lorsqu’une solution de norme minimale est nécessaire
- Pour diagnostiquer le conditionnement à partir du spectre singulier
- Pour appliquer une régularisation telle que la SVD tronquée

La SVD offre la plus grande puissance de diagnostic, mais peut coûter davantage en calcul et en mémoire que QR. Choisissez selon la taille, la parcimonie et la précision requise du problème.

## 7. Déficience de rang et solutions non uniques

Si \(\operatorname{rank}(A)<n\), des valeurs distinctes de \(x\) peuvent produire le même \(Ax\). Pour \(z\in\mathcal N(A)\),

$$
A(x+z)=Ax
$$

donc, si \(x\) est une solution des moindres carrés, \(x+z\) a le même résidu. La solution par pseudo-inverse sélectionne celle dont \(\|x\|_2\) est la plus petite.

Le rang n’est pas une notion binaire dans les données numériques. Pour un seuil de valeurs singulières \(\tau\), on peut écarter les directions qui satisfont

$$
\sigma_i\le\tau
$$

mais \(\tau\) n’est pas un simple détail d’implémentation. C’est un choix de modélisation concernant les directions à considérer comme non identifiables ; il doit refléter l’échelle, le niveau de bruit et l’objectif.

## 8. Moindres carrés pondérés et covariance

Si les composantes du résidu ont des variances différentes ou sont corrélées, l’hypothèse de pondération égale des moindres carrés ordinaires est inadaptée. Si la covariance de l’erreur est \(\Sigma_b\), alors

$$
x_\star
=
\arg\min_x
(Ax-b)^\mathsf T\Sigma_b^{-1}(Ax-b).
$$

Une matrice de blanchiment vérifiant \(W^\mathsf TW=\Sigma_b^{-1}\) transforme le problème en

$$
\min_x\|W(Ax-b)\|_2^2
$$

Ici, les poids ne doivent pas être des scores arbitraires choisis par commodité ; ils doivent être liés à la structure probabiliste des résidus.

## 9. La régularisation est une hypothèse supplémentaire, pas une astuce numérique

La régularisation de Tikhonov s’écrit

$$
x_\lambda
=
\arg\min_x
\left(
\|Ax-b\|_2^2
+\lambda^2\|L(x-x_0)\|_2^2
\right)
$$

- \(x_0\) : solution a priori ou de référence
- \(L\) : structure à pénaliser
- \(\lambda\) : compromis entre ajustement aux données et a priori

Avec \(L=I\) et \(x_0=0\), on obtient la forme ridge. La régularisation réduit la variance au prix d’un biais. Il faut donc la traiter comme une étape de modélisation qui indique quelles solutions sont plus plausibles, et non comme « l’ajout d’une petite valeur arbitraire parce que le nombre de condition est mauvais ».

\(\lambda\) peut être sélectionné par validation croisée, principe de l’écart, courbe en L, validation croisée généralisée ou d’autres méthodes. Quelle que soit la méthode, consignez le critère de sélection et l’indépendance des données d’évaluation.

## 10. Guide de sélection de l’algorithme

| Situation | Premier choix à envisager | Raison |
|---|---|---|
| Matrice dense, rang plein, conditionnement ordinaire | QR de Householder | Bon équilibre entre stabilité et coût |
| Rang incertain, diagnostic important | SVD | Révèle le spectre singulier et le noyau |
| Rang colonne à déterminer | QR avec pivotement ou SVD | Estime le rang effectif |
| Très grand problème creux | Solveur itératif de moindres carrés | Évite le coût d’une factorisation matricielle |
| Structure de covariance présente | Moindres carrés blanchis ou pondérés | Reflète le modèle d’erreur |
| Problème inverse mal posé | Solveur régularisé | Atténue les directions instables |
| Vitesse prioritaire et bon conditionnement | Envisager prudemment Cholesky sur les équations normales | Rapide, mais risque de mettre au carré le nombre de condition |

Par défaut, utilisez une fonction qui résout directement le système linéaire plutôt que de « calculer l’inverse et multiplier ». Les fonctions de bibliothèque telles que `solve`, `lstsq` et les solveurs creux exploitent leurs factorisations internes et leur gestion des exceptions.

## 11. Flux de travail pratique

1. **Définir l’objectif** : la prédiction importe-t-elle, ou l’interprétation des paramètres ?
2. **Vérifier dimensions et unités** : notez les formes et unités physiques de \(A\), (x) et \(b\).
3. **Mettre à l’échelle** : examinez les normes des colonnes, les plages de variables et les unités ; centrez et normalisez si nécessaire.
4. **Diagnostiquer le rang** : examinez les pivots QR ou le spectre singulier.
5. **Choisir un solveur** : utilisez QR par défaut ; envisagez la SVD pour diagnostiquer le rang et le mauvais conditionnement.
6. **Analyser les résidus** : examinez structure, biais, hétéroscédasticité et corrélation, pas seulement une norme.
7. **Vérifier l’orthogonalité** : contrôlez si \(A^\mathsf Tr\) est nul à la tolérance près.
8. **Vérifier la sensibilité** : perturbez l’entrée dans sa plage admissible et observez la variation des coefficients et prédictions.
9. **Rapporter l’incertitude** : calculez l’incertitude des paramètres lorsque le modèle de bruit et les hypothèses de covariance sont valides.
10. **Consigner les détails de reproductibilité** : conservez le solveur, la tolérance, la mise à l’échelle, le seuil de rang et la méthode de sélection de la régularisation.

## 12. Liste de vérification

- [ ] La norme minimisée et les poids sont-ils précisés ?
- [ ] \(Ax_\star\) appartient-il à l’espace colonne et \(A^\mathsf Tr\approx0\) ?
- [ ] Si le rang plein était supposé, a-t-il réellement été vérifié ?
- [ ] A-t-on évité d’inverser \(A^\mathsf TA\) ?
- [ ] Les nombres de condition avant et après mise à l’échelle des colonnes ont-ils été comparés ?
- [ ] Les valeurs singulières et le seuil ont-ils été consignés ensemble ?
- [ ] L’amplitude du résidu et la stabilité des paramètres ont-elles été évaluées séparément ?
- [ ] A-t-on évité de surajuster le paramètre de régularisation aux données d’évaluation ?
- [ ] Les poids des moindres carrés pondérés correspondent-ils au modèle d’erreur ?
- [ ] Les intervalles de prédiction ont-ils été distingués des intervalles de confiance des paramètres ?

## 13. Pièges et limites

### Prendre un \(R^2\) élevé pour la preuve d’un problème bien résolu

Un fort pouvoir explicatif ne garantit ni l’indépendance des résidus, ni l’adéquation du modèle, ni l’identifiabilité des paramètres. C’est particulièrement dangereux en extrapolation.

### Changer les unités d’entrée puis comparer directement les coefficients

L’amplitude d’un coefficient dépend de l’échelle de la variable. Alignez unités et échelles avant de comparer leur importance.

### Croire que la pseudo-inverse retrouve la « vraie solution »

La pseudo-inverse se contente de choisir une solution représentative selon un critère d’optimisation explicite ; elle ne peut restituer l’information du noyau perdue dans les données.

### Masquer les erreurs de structure du modèle par la régularisation

La régularisation atténue le caractère mal posé, mais ne corrige ni les variables omises, ni un opérateur d’observation incorrect, ni un biais systématique.

### Limites des moindres carrés linéarisés

Un modèle non linéaire \(f(x)\) nécessite une linéarisation locale et une optimisation itérative. Les valeurs initiales, les minima locaux et le conditionnement de la jacobienne deviennent des préoccupations supplémentaires.

## Conclusion

Les moindres carrés ne sont pas seulement une « formule qui réduit la somme des carrés des erreurs » : il s’agit d’un **problème de projection sur un sous-espace**. QR est l’outil fondamental pour calculer cette projection de manière stable, tandis que la SVD est l’outil de diagnostic qui expose le rang et les directions instables. Le nombre de condition indique si le calcul est digne de confiance, et la régularisation exprime explicitement les hypothèses ajoutées pour remplacer l’information manquante.

L’analyse par moindres carrés devient reproductible lorsque l’orthogonalité des résidus, le spectre singulier, la mise à l’échelle, le solveur et la tolérance sont conservés avec les résultats finaux.
