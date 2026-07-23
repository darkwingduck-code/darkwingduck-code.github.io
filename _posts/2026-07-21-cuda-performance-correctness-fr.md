---
title: "Performances et exactitude avec CUDA : principes pratiques d’APOD, de hiérarchie mémoire et de profilage"
date: 2026-07-21 12:29:00 +0900
categories: [GPU, Performance]
tags: [cuda, gpu-programming, profiling, memory-coalescing, numerical-correctness]
description: Améliorer les kernels CUDA à l’aide d’une référence CPU exacte, du cycle APOD, de l’analyse du trafic mémoire, de l’occupation et des preuves du profileur, plutôt que par des optimisations à l’aveugle.
lang: fr-FR
hidden: true
translation_key: cuda-performance-correctness
math: true
mermaid: true
---

{% include language-switcher.html %}

L’optimisation CUDA n’est pas une astuce consistant à augmenter le nombre de threads ou à ajouter de la mémoire partagée.
C’est un processus itératif qui consiste à trouver les goulots d’étranglement significatifs dans l’ensemble de l’application et à améliorer les mouvements de données ainsi que l’efficacité de l’exécution tout en préservant l’exactitude.

## 1. Le problème : un kernel rapide ne garantit pas une application rapide

Le code GPU comprend les coûts suivants.

- Prétraitement sur l’hôte
- Transfert de l’hôte vers le périphérique
- Lancement du kernel
- Calcul sur le périphérique
- Synchronisation du périphérique
- Transfert du périphérique vers l’hôte
- Post-traitement

Même si un kernel devient des dizaines de fois plus rapide, son effet reste limité s’il ne représente qu’une petite partie du temps total.
La loi d’Amdahl s’écrit comme suit.

$$
S=\frac{1}{(1-p)+p/s}
$$

- (p) : proportion occupée par la cible de l’amélioration
- (s) : accélération de cette partie

Commencez par mesurer (p) à l’aide d’un profil.

## 2. Modèle mental : le cycle APOD

```mermaid
flowchart LR
    A[Évaluer] --> B[Paralléliser]
    B --> C[Optimiser]
    C --> D[Déployer]
    D --> E[Observer les charges réelles]
    E --> A
```

L’approche APOD de NVIDIA met l’accent sur le cycle suivant.

- Évaluer : mesurer les points chauds et les objectifs.
- Paralléliser : sélectionner les parties qui peuvent l’être en toute sécurité.
- Optimiser : améliorer la mémoire, l’exécution et les instructions.
- Déployer : valider les régressions et la portabilité dans l’environnement réel.

Conservez les tests d’exactitude et les preuves du profileur pour chaque optimisation.

## 3. Référence CPU et contrat numérique

Avant l’implémentation sur GPU, conservez une référence pour les petites entrées.

```cpp
for (int i = 0; i < n; ++i) {
    reference[i] = transform(input[i]);
}
```

Éléments de validation :

- Tolérance absolue et relative
- NaN et Inf
- Longueur nulle et tailles limites
- Tailles qui ne sont pas des multiples de la taille de bloc
- Valeurs extrêmement grandes ou petites
- Exigences de déterminisme
- Différences dans l’ordre de réduction

L’addition en virgule flottante ne satisfait pas exactement l’associativité.
Une réduction parallèle peut ne pas être identique bit à bit à une somme CPU séquentielle.

Exemple de critère d’erreur :

$$
|y_{gpu}-y_{ref}| \le a_{tol}+r_{tol}|y_{ref}|
$$

Une tolérance doit reposer sur le dtype, le conditionnement et le nombre d’opérations accumulées, et non être fixée à une valeur arbitrairement grande.

## 4. Mise en correspondance des threads, blocs et grilles

Correspondance de base pour un tableau unidimensionnel :

```cpp
__global__ void scale(float* y, const float* x, float a, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        y[i] = a * x[i];
    }
}
```

Questions de conception :

- De quelle sortie chaque thread est-il propriétaire ?
- Existe-t-il un chevauchement des écritures entre threads ?
- Une synchronisation entre blocs est-elle nécessaire ?
- La taille de l’entrée dépasse-t-elle la limite de la grille ?
- Une boucle avec pas est-elle nécessaire ?

Boucle à pas de grille :

```cpp
for (int i = blockIdx.x * blockDim.x + threadIdx.x;
     i < n;
     i += blockDim.x * gridDim.x) {
    y[i] = a * x[i];
}
```

Elle gère des tailles variables et facilite l’expérimentation avec les configurations de lancement.

## 5. Hiérarchie mémoire et regroupement des accès

Les performances sont souvent limitées par le nombre d’octets déplacés plutôt que par le nombre d’opérations.

- Registres : locaux au thread et rapides, mais en nombre limité
- Mémoire partagée : locale au bloc ; exige une gestion et une synchronisation explicites
- Cache L1/L2 : géré par le matériel
- Mémoire globale : grande, mais limitée par la latence et la bande passante
- Mémoire constante : avantageuse pour certains motifs de diffusion

Concevez la disposition du tableau de sorte que des threads adjacents dans un warp accèdent à des adresses adjacentes.

Exemple de mauvais pas :

```cpp
float value = matrix[threadIdx.x * leading_dimension + column];
```

Demandez-vous si l’indice peut être réorganisé afin que les threads lisent des colonnes contiguës.

Ne devinez pas si les accès sont regroupés ; confirmez-le avec les métriques de transactions mémoire et de débit.

## 6. Intensité arithmétique et raisonnement Roofline

Intensité arithmétique :

$$
I=\frac{\text{operations}}{\text{bytes transferred}}
$$

Une faible intensité suggère une charge limitée par la mémoire, tandis qu’une forte intensité suggère une charge limitée par le calcul.
Une borne supérieure simple du modèle Roofline est :

$$
P\le \min(P_{peak}, I\times B_{memory})
$$

Il s’agit d’un modèle mental pour choisir une direction d’optimisation, et non d’un prédicteur exact des performances.

- Limité par la mémoire : réutilisation des données, regroupement des accès et réduction des transferts
- Limité par le calcul : combinaison d’instructions, débit mathématique et adéquation aux tensor cores
- Limité par la latence : analyse du parallélisme et des dépendances

## 7. Quand utiliser la mémoire partagée

La mémoire partagée est avantageuse lorsque les données globales sont réutilisées.

Workflow typique par tuiles :

1. Chaque thread lit une partie d’une tuile depuis la mémoire globale.
2. La stocker dans la mémoire partagée.
3. Utiliser `__syncthreads()` pour synchroniser la fin du chargement.
4. Réutiliser la tuile dans plusieurs opérations.
5. Passer à la tuile suivante.

Précautions :

- Chaque thread participant doit atteindre la barrière.
- Des conflits de banques peuvent se produire.
- Davantage de mémoire partagée par bloc réduit le nombre de blocs résidents.
- Pour des données lues une seule fois, la copie peut coûter plus qu’elle ne rapporte.

Comparez les chargements globaux et le temps du kernel avant et après l’utilisation de la mémoire partagée.

## 8. Traiter l’occupation comme une contrainte, pas comme un objectif

L’occupation est la proportion de warps actifs sur un SM par rapport au maximum théorique.
Elle compte pour masquer la latence, mais 100 % n’est pas toujours optimal.

Facteurs qui limitent l’occupation :

- Threads par bloc
- Utilisation des registres
- Utilisation de la mémoire partagée
- Limites de l’architecture

Forcer la baisse de l’utilisation des registres peut provoquer un débordement et augmenter le trafic de mémoire locale.
Une faible occupation peut rester rapide lorsque le parallélisme au niveau des instructions et la réutilisation du cache sont bons.

Commencez avec des tailles de bloc multiples de 32 et mesurez plusieurs candidats.
Utilisez l’API d’occupation officielle et un profileur, mais prenez la décision finale selon le temps de bout en bout.

## 9. Divergence, opérations atomiques et réductions

Lorsque les threads d’un warp exécutent des branches différentes, leurs chemins peuvent être sérialisés.
Cependant, ajouter des calculs complexes pour éliminer une branche courte peut être plus lent.

Les opérations atomiques sont utiles pour l’exactitude, mais la contention peut devenir un goulot d’étranglement.

Hiérarchie de réduction :

1. Résultat partiel local au thread
2. Réduction au niveau du warp
3. Réduction au niveau du bloc
4. Une opération atomique globale uniquement pour les résultats de bloc, ou un second kernel

Testez chaque réduction personnalisée avec diverses tailles et politiques relatives aux NaN.
Utilisez d’abord une primitive de bibliothèque lorsqu’elle suffit.

## 10. Asynchronisme et mesure du temps

Le lancement d’un kernel peut être asynchrone par rapport à l’hôte.
Une mesure immédiate avec une horloge générale peut ne saisir que le temps de lancement.

Utilisez des événements CUDA.

```cpp
cudaEventRecord(start, stream);
kernel<<<grid, block, 0, stream>>>(...);
cudaEventRecord(stop, stream);
cudaEventSynchronize(stop);
cudaEventElapsedTime(&milliseconds, start, stop);
```

Principes de mesure des performances :

- Effectuer un préchauffage.
- Consigner les variations de fréquence et les interférences d’autres processus.
- Répéter plusieurs fois et publier la distribution.
- N’ajouter que les synchronisations nécessaires.
- Distinguer les mesures qui incluent les transferts de celles qui les excluent.
- Indiquer les coûts de génération et de validation des entrées.

## 11. Workflow de profilage

### Chronologie au niveau du système

Utilisez Nsight Systems pour examiner l’activité du CPU, les transferts, les kernels, la synchronisation et les périodes d’inactivité.

Questions :

- À quels moments le GPU est-il inactif ?
- Y a-t-il trop de petits lancements de kernels ?
- Les transferts et les calculs se chevauchent-ils ?
- Existe-t-il des synchronisations inutiles ?

### Métriques au niveau du kernel

Utilisez Nsight Compute pour une vue détaillée des kernels sélectionnés.

- Bande passante mémoire atteinte
- Efficacité des transactions mémoire
- Raisons d’attente des warps
- Occupation et registres
- Efficacité des branches
- Débit d’instructions

Collecter toutes les métriques à la fois augmente le surcoût du profilage.
Ne sélectionnez que les sections nécessaires pour vérifier l’hypothèse.

## 12. Ordre pratique des optimisations

1. Trouver le point chaud avec un profil de bout en bout.
2. Figer la référence CPU et les tests du kernel.
3. Supprimer les transferts et synchronisations inutiles.
4. Améliorer les motifs d’accès à la mémoire.
5. S’il existe une réutilisation, envisager la mémoire partagée ou la fusion.
6. Explorer les configurations de lancement et de blocs.
7. N’envisager les optimisations d’instructions et de précision qu’en dernier.
8. Exécuter les tests de régression d’exactitude et de performances après chaque modification.

La fusion des kernels peut réduire le trafic intermédiaire en mémoire globale et les lancements.
Cependant, mesurez aussi la pression sur les registres, la complexité du code et la baisse de réutilisabilité.

## 13. Liste de contrôle de l’évaluation

- [ ] Existe-t-il une référence CPU indépendante pour les petites entrées ?
- [ ] La tolérance est-elle définie avec une justification numérique ?
- [ ] Les erreurs mémoire ont-elles été vérifiées avec Compute Sanitizer ou un outil équivalent ?
- [ ] Les points chauds de bout en bout ont-ils été identifiés en premier ?
- [ ] Le temps du kernel est-il distingué du temps incluant les transferts ?
- [ ] Un préchauffage et une synchronisation des événements ont-ils été appliqués ?
- [ ] Le regroupement des accès globaux a-t-il été confirmé par des métriques ?
- [ ] Les données sont-elles réellement réutilisées dans la mémoire partagée ?
- [ ] L’occupation et le débordement des registres sont-ils examinés ensemble ?
- [ ] Les tailles non multiples et les limites ont-elles été testées ?
- [ ] Les performances et l’exactitude ont-elles été vérifiées sur plusieurs architectures ?
- [ ] Les preuves du profileur et les commits sont-ils reliés avant et après l’optimisation ?

## 14. Échecs courants et limites

### Observer uniquement l’utilisation du GPU

Une utilisation élevée n’indique pas si le travail est un calcul utile ou une attente de la mémoire.
Examinez ensemble le débit de l’application et les métriques du kernel.

### Supposer que la mémoire partagée est toujours plus rapide

Une copie sans réutilisation ne fait qu’ajouter des instructions et des barrières.
Décidez d’après les profils avant et après la modification.

### Forcer une occupation de 100 %

Le débordement des registres et la dégradation de la réutilisation du cache peuvent ralentir l’exécution.
L’occupation est une cause des performances, pas la fonction objectif.

### Activer les calculs rapides sans valider l’exactitude

Les opérations approchées et la contraction peuvent modifier le résultat.
Évaluez les tolérances métier et la stabilité dans l’ensemble du pipeline.

La configuration CUDA optimale varie selon l’architecture du GPU et le toolkit.
Ne considérez pas un réglage codé en dur comme une règle permanente ; maintenez un benchmark reproductible.

## 15. Références officielles

- [Guide de programmation CUDA C++](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
- [Guide des bonnes pratiques CUDA C++](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- [Documentation officielle de Nsight Systems](https://docs.nvidia.com/nsight-systems/)
- [Documentation officielle de Nsight Compute](https://docs.nvidia.com/nsight-compute/)
- [Documentation officielle de Compute Sanitizer](https://docs.nvidia.com/compute-sanitizer/)

## 16. Conclusion

Les performances CUDA résultent du comportement de la mémoire, de l’exécution et de la structure de l’application.
Maintenir le cycle APOD avec les tests d’exactitude évite les illusions des microbenchmarks et ne conserve que les améliorations qui se reproduisent sur les charges réelles.
