---
title: "Des espaces vectoriels au changement de base : comprendre la structure de l’algèbre linéaire"
date: 2026-07-21 09:00:00 +0900
categories: [Mathematics, Linear Algebra]
tags: [vector-space, subspace, span, linear-independence, basis, dimension, change-of-basis]
description: "Reliez sous-espaces, espaces engendrés, indépendance linéaire, bases, dimensions et transformations de coordonnées au moyen de définitions, d’exemples détaillés et de procédures de validation pratiques."
math: true
lang: fr-FR
translation_key: vector-spaces-basis-change-of-coordinates
hidden: true
---

{% include language-switcher.html %}

Une grande part de la confusion en algèbre linéaire ne vient pas des méthodes de calcul, mais du **mélange de concepts situés à des niveaux différents**. Un espace vectoriel est le cadre dans lequel les opérations sont valides ; un sous-espace est un cadre plus petit, fermé pour ces opérations. L’espace engendré est l’ensemble que l’on peut construire à partir de vecteurs donnés, l’indépendance linéaire signifie qu’une représentation ne comporte aucune redondance et une base est un système de coordonnées qui satisfait ces deux propriétés.

Cet article ne cherche pas à faire mémoriser des termes séparément, mais à répondre de façon cohérente aux questions suivantes.

- Un ensemble donné est-il réellement un sous-espace ?
- Quel espace un ensemble de vecteurs engendre-t-il ?
- Comment supprimer les redondances d’une famille génératrice ?
- Quand une famille de vecteurs peut-elle former une base ?
- Lorsque la base change, comment le vecteur lui-même et ses coordonnées changent-ils ?

## 1. Espaces vectoriels : des ensembles dans lesquels les combinaisons linéaires restent contenues

Un espace vectoriel \(V\) sur un corps \(\mathbb F\) est un ensemble muni d’une addition vectorielle et d’une multiplication par un scalaire. En pratique, les scalaires proviennent généralement de \(\mathbb R\) ou \(\mathbb C\). On ne vérifie pas à chaque fois tous les axiomes, comme l’associativité, la commutativité et la distributivité, mais leur essence tient dans l’énoncé suivant.

> Pour \(u,v\in V\) et \(a,b\in\mathbb F\), toute combinaison linéaire \(au+bv\) doit elle aussi appartenir à \(V\).

Les vecteurs ne se limitent pas à des suites de nombres. Les polynômes, les matrices, les fonctions et les signaux sont également des vecteurs si leur addition et leur multiplication par un scalaire satisfont les axiomes. L’essence de l’algèbre linéaire n’est donc pas la géométrie des flèches, mais une **structure qui préserve les combinaisons linéaires**.

## 2. Sous-espaces : un test en une ligne plus puissant que trois conditions séparées

Pour que \(W\subseteq V\) soit un sous-espace, il doit satisfaire les conditions suivantes.

1. Le vecteur nul appartient à \(W\).
2. Il est fermé pour l’addition.
3. Il est fermé pour la multiplication par un scalaire.

En regroupant ces conditions, on obtient le test suivant.

$$
u,v\in W,\quad a,b\in\mathbb F
\quad\Longrightarrow\quad
au+bv\in W.
$$

Vérifiez aussi \(W\neq\varnothing\), afin que l’ensemble vide ne réussisse pas le test à tort.

### Les contraintes homogènes créent des sous-espaces ; les contraintes non homogènes, en général, n’en créent pas

Pour une matrice \(A\),

$$
W=\{x\mid Ax=0\}
$$

est toujours un sous-espace. Si \(Au=0\) et \(Av=0\), alors

$$
A(au+bv)=aAu+bAv=0
$$

par linéarité. C’est pourquoi un noyau est un sous-espace.

En revanche,

$$
S=\{x\mid Ax=c\},\qquad c\neq 0
$$

ne contient généralement pas le vecteur nul et n’est donc pas un sous-espace. Si des solutions existent, \(S\) est un **ensemble affine** obtenu en translatant le noyau. Une droite ou un plan ne passant pas par l’origine en est un exemple typique.

## 3. Espace engendré : tout ce que l’on peut construire avec les éléments donnés

L’espace engendré par les vecteurs \(v_1,\dots,v_k\) est l’ensemble de toutes leurs combinaisons linéaires.

$$
\operatorname{span}(v_1,\dots,v_k)
=
\left\{
\sum_{i=1}^{k}a_i v_i
\;\middle|\;
a_i\in\mathbb F
\right\}.
$$

Il s’agit du **plus petit sous-espace** contenant chacun des vecteurs \(v_1,\dots,v_k\). Ajouter des vecteurs à une famille génératrice n’augmente pas nécessairement la dimension. Si un nouveau vecteur appartient déjà à l’espace engendré, seule la représentation devient redondante ; l’espace reste inchangé.

Construire la matrice

$$
A=[v_1\;v_2\;\cdots\;v_k]
$$

revient à faire de \(\operatorname{span}(v_1,\dots,v_k)\) l’espace colonne de \(A\). On détermine si un vecteur \(y\) appartient à cet espace selon que \(Ac=y\) possède ou non une solution.

## 4. Indépendance linéaire : unicité de la représentation du vecteur nul

La famille \(\{v_1,\dots,v_k\}\) est linéairement indépendante lorsque

$$
a_1v_1+\cdots+a_kv_k=0
$$

n’a que la solution \(a_1=\cdots=a_k=0\). Si des coefficients non nuls permettent de produire le vecteur nul, la famille est linéairement dépendante.

Du point de vue matriciel, tous les énoncés suivants sont équivalents.

- \(v_1,\dots,v_k\) sont linéairement indépendants.
- L’unique solution de \(Ac=0\) est \(c=0\).
- Le nombre de colonnes pivots de \(A\) est \(k\).
- \(\operatorname{rank}(A)=k\).
- La nullité vaut 0.

### Une affirmation souvent erronée : « un vecteur de base doit seulement être non nul »

Pour un seul vecteur \(v\), si \(v\neq0\), alors \(\{v\}\) est une base du sous-espace unidimensionnel \(\operatorname{span}(v)\) qu’il engendre. Ce n’est toutefois pas une base d’un sous-espace arbitraire plus grand. Pour former une base, les vecteurs doivent être à la fois **linéairement indépendants** et **engendrer** tout l’espace cible.

## 5. Base et dimension : une famille génératrice minimale et une famille libre maximale

Une base \(B=(b_1,\dots,b_n)\) d’un sous-espace \(W\) satisfait les deux conditions suivantes.

1. \(\operatorname{span}(b_1,\dots,b_n)=W\)
2. \(b_1,\dots,b_n\) sont linéairement indépendants.

On peut donc comprendre une base de deux façons.

- Une **famille génératrice minimale** qui cesse d’engendrer tout l’espace dès que l’on retire un vecteur
- Une **famille libre maximale** qui devient dépendante dès que l’on ajoute un vecteur

Toutes les bases d’un espace de dimension finie comportent le même nombre de vecteurs. Ce nombre est la dimension \(\dim W\). Pour une matrice \(A\in\mathbb F^{m\times n}\),

$$
\operatorname{rank}(A)+\operatorname{nullity}(A)=n
$$

Cette relation signifie que les \(n\) degrés de liberté en entrée se décomposent en directions observables de l’espace colonne et en directions du noyau effacées par \(A\).

## 6. Exemple détaillé : trouver la base d’un plan de deux façons

Considérons le plan homogène suivant.

$$
W=\{(x,y,z)^\mathsf T\in\mathbb R^3\mid x+y+z=0\}.
$$

Puisque la contrainte donne \(x=-y-z\),

$$
\begin{bmatrix}x\\y\\z\end{bmatrix}
=
y\begin{bmatrix}-1\\1\\0\end{bmatrix}
+
z\begin{bmatrix}-1\\0\\1\end{bmatrix}.
$$

Une base candidate est donc

$$
B=
\left(
\begin{bmatrix}-1\\1\\0\end{bmatrix},
\begin{bmatrix}-1\\0\\1\end{bmatrix}
\right)
$$

Les deux vecteurs ne sont pas des multiples scalaires l’un de l’autre : ils sont donc indépendants et engendrent toutes les solutions. Ainsi, \(\dim W=2\).

La relation rang-nullité conduit à la même conclusion. La matrice de la contrainte \(A=[1\;1\;1]\) est de rang 1 ; sa nullité vaut donc \(3-1=2\). Vérifier que plusieurs démarches donnent la même dimension est une technique de validation utile.

## 7. Distinguer les coordonnées du vecteur lui-même

Si les coordonnées d’un vecteur \(v\) dans la base \(B=(b_1,\dots,b_n)\) s’écrivent

$$
[v]_B=
\begin{bmatrix}c_1\\\vdots\\c_n\end{bmatrix}
$$

alors

$$
v=c_1b_1+\cdots+c_nb_n
$$

Ici, \(v\) est un objet abstrait, tandis que \([v]_B\) est une représentation numérique qui dépend de la base choisie.

Dans la suite, supposons que deux bases d’un espace à \(n\) dimensions soient exprimées dans un même système de coordonnées de référence à \(n\) dimensions ; leurs matrices de base sont donc carrées et inversibles. Si la matrice dont les colonnes sont les vecteurs de base est elle aussi notée \(B\), alors

$$
v=B[v]_B,\qquad [v]_B=B^{-1}v
$$

Si \(B\) et \(C\) sont deux bases du même espace, alors

$$
[v]_C=C^{-1}B[v]_B.
$$

Ainsi, la matrice qui convertit les coordonnées dans \(B\) en coordonnées dans \(C\) est

$$
P_{C\leftarrow B}=C^{-1}B
$$

Lire la flèche en indice comme « de la base d’entrée vers la base de sortie » aide à éviter les erreurs dans l’ordre des multiplications.

Lorsqu’une base de sous-espace est écrite directement dans les coordonnées d’un espace ambiant plus grand, sa matrice peut être rectangulaire et \(B^{-1}\) n’existe pas. Dans ce cas, résolvez \(B[v]_B=v\) avec QR ou une méthode similaire, ou choisissez d’abord une base de référence fixe dans le sous-espace et exprimez-la sous forme de matrice de coordonnées carrée.

### La matrice d’une transformation linéaire dépend elle aussi de la base

Si \(A\) est la matrice dans la base canonique d’une transformation linéaire \(T:V\to V\), et si \(B\) est la nouvelle matrice de base, alors

$$
[T]_B=B^{-1}AB.
$$

Cette suite convertit un vecteur des nouvelles coordonnées vers les coordonnées canoniques, applique \(A\), puis le ramène dans les nouvelles coordonnées. Comme \(A\) et \(B^{-1}AB\) expriment la même transformation linéaire dans des systèmes de coordonnées différents, elles possèdent les mêmes invariants de similitude, notamment la trace, le déterminant et les valeurs propres.

## 8. Démarche pratique de résolution

### Lorsqu’un ensemble est donné

1. Précisez l’espace ambiant et le corps des scalaires.
2. Vérifiez d’abord qu’il contient le vecteur nul.
3. Pour des \(u,v\) arbitraires et des scalaires \(a,b\), vérifiez que \(au+bv\) respecte la condition de définition.
4. S’il existe un terme constant non homogène, une inégalité ou une condition de norme fixée, envisagez d’abord qu’il ne s’agisse pas d’un sous-espace.

### Lorsque des vecteurs générateurs sont donnés

1. Construisez une matrice dont les colonnes sont ces vecteurs.
2. Trouvez les colonnes pivots par réduction en lignes.
3. Choisissez les colonnes pivots de la **matrice d’origine** comme base de l’espace colonne.
4. Comparez le rang au nombre de vecteurs de base.

Les colonnes d’une matrice réduite peuvent engendrer un espace colonne différent de celui de la matrice d’origine. Les opérations sur les lignes préservent l’espace ligne, mais ne préservent généralement pas l’espace colonne lui-même.

### Lorsqu’une transformation de coordonnées est donnée

1. Précisez le système de coordonnées dans lequel chaque vecteur de base est écrit.
2. Faites correspondre l’ordre des colonnes de la matrice de base avec celui des composantes des coordonnées.
3. Calculez \(P_{C\leftarrow B}=C^{-1}B\).
4. Vérifiez que \(CP_{C\leftarrow B}=B\).
5. Pour un vecteur test quelconque, vérifiez que \(B[v]_B=C[v]_C\).

## 9. Liste de contrôle de validation

- [ ] Avez-vous appelé sous-espace un ensemble qui ne contient pas le vecteur nul ?
- [ ] Avez-vous distingué l’espace engendré de l’ensemble lui-même ?
- [ ] Avez-vous vérifié séparément « engendre » et « est indépendant » ?
- [ ] Le nombre de vecteurs de base est-il égal à la dimension connue ?
- [ ] La somme du rang et de la nullité est-elle égale au nombre de colonnes ?
- [ ] Avez-vous sélectionné les colonnes pivots dans la matrice d’origine ?
- [ ] Avez-vous indiqué la direction entre les bases d’entrée et de sortie de la transformation de coordonnées ?
- [ ] Le vecteur réel est-il reconstruit sans changement après la transformation ?
- [ ] Avez-vous consigné la tolérance de détection du rang pour les calculs numériques ?

## 10. Pièges et limites

### Tenter de tout décider avec un seul déterminant

Le déterminant n’est défini que pour les matrices carrées. Pour les questions d’indépendance, d’espace engendré et de rang portant sur des matrices rectangulaires, la réduction en lignes, QR et la SVD sont plus générales.

### Le rang numérique n’est pas un entier exact

Avec des données en virgule flottante, on décide si une valeur singulière est « suffisamment petite », au lieu de vérifier si elle est exactement nulle. Puisque le rang estimé peut changer avec le seuil, indiquez ensemble l’échelle et la tolérance.

### Supposer qu’une base est unique

La dimension est fixe, mais il existe une infinité de bases. Une bonne base dépend de l’objectif. Une base orthonormée stabilise les calculs, une base propre simplifie les opérations et une base creuse peut faciliter l’interprétation et le stockage.

### Étendre à l’excès l’intuition de la dimension finie

Dans les espaces de dimension infinie, tels que les espaces de fonctions, une base algébrique se distingue d’une base analytique faisant intervenir la convergence. Dès que des sommes infinies, des normes et la complétude apparaissent, l’intuition issue des matrices finies ne suffit plus.

## Conclusion

Le cheminement essentiel est simple.

$$
\text{Sous-espace}
\longrightarrow
\text{espace engendré}
\longrightarrow
\text{indépendance linéaire}
\longrightarrow
\text{base}
\longrightarrow
\text{dimension et coordonnées}
$$

Une base n’est pas simplement une « liste de vecteurs directeurs ». C’est une **interface qui représente chaque élément d’un espace sans redondance**. Avec ce point de vue, la projection, les moindres carrés, la SVD et la réduction de dimension se relient dans un même langage.
