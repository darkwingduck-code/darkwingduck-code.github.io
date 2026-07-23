---
title: "L’ossature de la méthode des éléments finis : formes faibles, éléments, quadrature et convergence du maillage"
date: 2026-07-21 12:43:00 +0900
categories: [Scientific Computing, Finite Element Method]
tags: [fem, weak-form, galerkin, finite-element, quadrature, mesh-convergence]
description: "Relier toute la structure fondamentale des éléments finis : passage de la forme forte à la forme faible, espaces fonctionnels, conditions aux limites, interpolation élémentaire, quadrature, assemblage, solveurs linéaires et convergence du maillage."
math: true
mermaid: true
lang: fr-FR
translation_key: fem-weak-form-elements-quadrature-mesh-convergence
hidden: true
---

{% include language-switcher.html %}

La méthode des éléments finis (MEF) est bien plus qu’une technique de découpage d’une géométrie en petits morceaux.
Elle transforme une équation différentielle en une forme faible intégrable et projette un problème posé dans un espace fonctionnel de dimension infinie sur un sous-espace de dimension finie.
Une fois ce point de vue compris, types d’éléments et options de solveur se rattachent à une même structure mathématique.

## 1. Partir de la forme forte

Considérons le problème de Poisson.

$$
-\nabla\cdot(k\nabla u)=f \quad \text{in }\Omega,
$$

$$
u=g_D \quad \text{on }\Gamma_D,
\qquad
-k\nabla u\cdot n=g_N \quad \text{on }\Gamma_N.
$$

La forme forte exige que (u) soit suffisamment différentiable point par point et satisfasse en chaque point l’équation et les conditions aux limites.
Pour des coefficients complexes, des matériaux discontinus et des domaines non lisses, cette exigence peut être trop forte.

## 2. Fonctions tests et intégration par parties

Multiplions par une fonction test (v), nulle sur la frontière de Dirichlet, puis intégrons.

$$
\int_\Omega -v\nabla\cdot(k\nabla u)\,d\Omega
=\int_\Omega vf\,d\Omega.
$$

L’intégration par parties, ou identité de Green, donne

$$
\int_\Omega k\nabla v\cdot\nabla u\,d\Omega
-\int_{\partial\Omega}v k\nabla u\cdot n\,d\Gamma
=\int_\Omega vf\,d\Omega.
$$

En substituant la condition de Neumann, on obtient la forme faible

$$
a(u,v)=\ell(v)
$$

avec

$$
a(u,v)=\int_\Omega k\nabla v\cdot\nabla u\,d\Omega,
$$

$$
\ell(v)=\int_\Omega vf\,d\Omega+\int_{\Gamma_N}vg_N\,d\Gamma
$$

L’ordre de dérivation de (u) est passé du second au premier, et la condition naturelle aux limites est entrée sous forme d’intégrale de frontière.

## 3. Conditions aux limites essentielles et naturelles

- Une condition de Dirichlet restreint l’espace d’essai lui-même ; on la qualifie donc d’essentielle.
- Une condition de Neumann apparaît naturellement dans le membre de droite de la forme faible ; on la qualifie donc de naturelle.

Cette distinction importe aussi dans l’implémentation.
Lorsque vous éliminez de la matrice les degrés de liberté de Dirichlet ou les traitez comme des contraintes, préservez la symétrie et le calcul des réactions.

Un problème de Neumann pur possède un noyau, car toute solution décalée d’une constante est également possible.
Il requiert la condition de compatibilité

$$
\int_\Omega f\,d\Omega+\int_{\Gamma_N}g_N\,d\Gamma=0
$$

ainsi qu’une contrainte de valeur moyenne ou une référence.

## 4. Signification des espaces fonctionnels

L’espace naturel du problème de Poisson est l’espace de Sobolev (H^1(\Omega)).

$$
H^1(\Omega)=
\{v\in L^2(\Omega):\nabla v\in[L^2(\Omega)]^d\}.
$$

Autrement dit, il suffit que la fonction et sa première dérivée faible soient de carré intégrable.
L’exigence centrale porte sur une norme d’énergie intégrable, et non sur une régularité point par point.

La méthode de Galerkin utilise le même sous-espace de dimension finie pour les espaces d’essai et de test.

$$
V_h=\mathrm{span}\{N_1,\ldots,N_n\}.
$$

## 5. Interpolation élémentaire et degrés de liberté

Représentons la solution approchée par

$$
u_h(\mathbf x)=\sum_{j=1}^{n}N_j(\mathbf x)U_j
$$

Chaque (N_j) est une fonction de forme, et chaque (U_j) une valeur nodale ou un degré de liberté généralisé.

En utilisant chaque fonction de base (N_i) comme fonction test, on obtient

$$
K_{ij}=\int_\Omega k\nabla N_i\cdot\nabla N_j\,d\Omega,
\qquad
F_i=\ell(N_i)
$$

et le système global devient

$$
\mathbf K\mathbf U=\mathbf F
$$

## 6. Élément de référence et transformation

L’élément physique (Omega_e) est obtenu par transformation depuis l’élément de référence (hat\Omega).

$$
\mathbf x(\boldsymbol\xi)=
\sum_a N_a(\boldsymbol\xi)\mathbf x_a.
$$

La jacobienne est

$$
J=\frac{\partial\mathbf x}{\partial\boldsymbol\xi}
$$

et elle transforme à la fois le gradient et l’élément de volume.

$$
\nabla_x N=J^{-T}\nabla_\xi N,
\qquad
d\Omega=|\det J|d\hat\Omega.
$$

Un élément tel que (det J\le0) est inversé ou dégénéré.
Un petit déterminant et un grand nombre de condition détériorent le calcul des gradients et le conditionnement de la rigidité.

## 7. La quadrature fait partie du modèle

Approchons l’intégrale élémentaire par quadrature.

$$
\int_{\hat\Omega}g(\xi)d\xi
\approx
\sum_{q=1}^{n_q}w_q g(\xi_q).
$$

Si l’ordre d’intégration est trop faible, la rigidité et les forces internes peuvent être mal construites, ce qui produit des modes en sablier ou à énergie nulle.
À l’inverse, une quadrature excessive peut seulement augmenter le coût sans résoudre le verrouillage.

### Intégration réduite et intégration sélective

L’intégration réduite peut atténuer le verrouillage, mais comporte un risque de modes parasites.
Vérifiez que la stabilisation ne contamine pas l’énergie physique.

### Matériaux non linéaires et points de quadrature

Les variables d’état internes sont généralement mises à jour aux points de quadrature.
L’utilisation d’une tangente cohérente peut fortement améliorer la convergence de Newton.
La cohérence entre mise à jour de l’état, restauration et nouvelle tentative du pas de charge est importante.

## 8. L’assemblage est une convention de conservation du local vers le global

Ajoutez chaque matrice élémentaire (mathbf K^e) et chaque vecteur (mathbf F^e) au système global au moyen de la correspondance des degrés de liberté.

```mermaid
flowchart LR
  A[élément de référence] --> B[transformation géométrique]
  B --> C[évaluation aux points de quadrature]
  C --> D[matrice/vecteur élémentaire]
  D --> E[assemblage local vers global]
  E --> F[contraintes et termes de frontière]
  F --> G[résolution linéaire/non linéaire]
  G --> H[contrôle des erreurs et bilans]
```

Les degrés de liberté d’un nœud partagé combinent les contributions des éléments adjacents.
Pour les éléments d’arête ou de face ayant des signes et orientations, alignez l’orientation locale sur la convention globale.

## 9. Conformité, stabilité et verrouillage

Augmenter simplement l’ordre polynomial ne résout pas tous les problèmes.

- **Conformité** : l’espace d’approximation satisfait-il la continuité requise ?
- **Coercivité/stabilité inf-sup** : le problème discret est-il stable ?
- **Verrouillage** : la formulation devient-elle excessivement rigide pour les structures minces ou les conditions presque incompressibles ?
- **Mode parasite** : existe-t-il un mode qui se déforme sans énergie physique ?

Dans les problèmes mixtes, la combinaison des espaces de déplacement et de pression doit satisfaire la condition inf-sup.
Utiliser sans discernement une interpolation de même ordre peut produire des oscillations de pression.

## 10. Raffinements h, p et hp

- Raffinement h : réduire la taille des éléments.
- Raffinement p : augmenter l’ordre de la base.
- Raffinement hp : combiner les deux selon la régularité.

Sous des hypothèses de régularité suffisantes, une erreur typique en norme d’énergie prend la forme

$$
\|u-u_h\|_{H^1}\le C h^p|u|_{H^{p+1}}
$$

Aux singularités de coin, aux coefficients discontinus ou au contact, une faible régularité peut empêcher l’ordre nominal d’apparaître.

## 11. Erreurs a priori et a posteriori

Une estimation a priori explique le taux de convergence à partir de la régularité de la solution et de la taille du maillage.
Un estimateur a posteriori utilise les résidus et sauts de la solution calculée pour décider où raffiner.

Un estimateur résiduel conceptuel combine le résidu élémentaire (R_e) et le saut de flux entre éléments (J_f), par exemple

$$
\eta^2=\sum_e h_e^2\|R_e\|^2
+\sum_f h_f\|J_f\|^2
$$

Utilisez des problèmes de référence pour vérifier que l’indice d’efficacité reste stable dans toute la famille de problèmes.

## 12. Problèmes non linéaires et méthode de Newton

Si le vecteur résidu est (mathbf R(\mathbf U)=0), le pas de Newton est

$$
\mathbf J(\mathbf U^k)\Delta\mathbf U
=-\mathbf R(\mathbf U^k),
$$

$$
\mathbf U^{k+1}=\mathbf U^k+\alpha\Delta\mathbf U
$$

Une jacobienne cohérente, une recherche linéaire, le contrôle de l’incrément de charge ou de temps et la restauration de l’état déterminent la robustesse.

## 13. Flux de travail recommandé

1. Préciser la forme forte, le domaine et le découpage de la frontière.
2. Multiplier par une fonction test et dériver à la main la forme faible par intégration par parties.
3. Définir les espaces d’essai et de test ainsi que les contraintes essentielles.
4. Vérifier l’élément de référence, la transformation et les fonctions de forme.
5. Adapter l’ordre de quadrature à l’intégrande et à la non-linéarité.
6. Effectuer au niveau de l’élément un test de patch et un test par solution fabriquée.
7. Vérifier le bilan global, les réactions et l’énergie.
8. Effectuer un raffinement systématique sur au moins trois niveaux.
9. Rapporter la convergence et les estimateurs d’erreur pour chaque quantité d’intérêt.

## 14. Liste de vérification

- [ ] Le signe du terme de frontière de la forme faible a été redérivé.
- [ ] Les conditions aux limites essentielles et naturelles ont été distinguées.
- [ ] Le noyau et la compatibilité du problème de Neumann pur ont été traités.
- [ ] La direction de la jacobienne entre référence et espace physique est cohérente.
- [ ] Le déterminant de chaque élément est positif et suffisamment grand.
- [ ] Les modes de corps rigide et le noyau attendu ont été vérifiés.
- [ ] Le test de patch et le test d’état constant ont réussi.
- [ ] La sensibilité à l’ordre de quadrature a été évaluée.
- [ ] La somme des réactions et des forces externes est équilibrée.
- [ ] L’énergie de déformation et le travail sont cohérents.
- [ ] L’ordre observé a été calculé lors du raffinement h ou p.
- [ ] Une valeur ponctuelle singulière n’est pas rapportée comme une quantité d’intérêt convergée.

## 15. Schémas d’échec courants et limites

### Se contenter d’affiner le maillage

Ajouter des éléments déformés ou n’appliquer qu’un raffinement uniforme autour d’une singularité apporte peu au regard du coût.

### Supposer qu’un contour lisse est exact

Le post-traitement par moyennage nodal peut donner un aspect lisse à une contrainte discontinue.
Vérifiez les valeurs originales aux points de quadrature et l’équilibre.

### Utiliser l’intégration réduite comme remède universel

Elle peut réduire le verrouillage, mais introduire des modes en sablier.
Examinez simultanément l’énergie de stabilisation et la sensibilité au maillage.

### Confondre tolérance du solveur et erreur de discrétisation

L’erreur de maillage peut rester grande même lorsque le résidu linéaire est faible.
Inversement, comparer des raffinements alors que l’erreur algébrique est grande contamine l’ordre observé.

### Comparer uniquement la contrainte maximale en un point donné

La contrainte ponctuelle peut diverger à un coin rentrant ou sous une charge concentrée.
Choisissez une quantité d’intérêt bien définie, telle qu’une intégrale, une moyenne ou un paramètre de rupture.

## 16. Références officielles et primaires

- Galerkin, B. G., “Series Solution of Some Problems of Elastic Equilibrium,” 1915.
- Courant, R., “Variational Methods for the Solution of Problems of Equilibrium and Vibrations,” 1943.
- Ciarlet, P. G., *The Finite Element Method for Elliptic Problems*.
- NIST, [documentation sur l’analyse par éléments finis OOF](https://www.ctcms.nist.gov/oof/oof2/).
- PETSc, [interfaces d’éléments finis et de discrétisation](https://petsc.org/release/manual/dmplex/).
- The FEniCS Project, [documentation officielle](https://docs.fenicsproject.org/).

Le cœur de la MEF n’est pas la forme de ses éléments, mais **la cohérence avec laquelle forme faible, espaces fonctionnels, quadrature, assemblage et estimation d’erreur constituent un même problème d’approximation**.
