---
title: "Un modèle mental pratique des structures de données et des algorithmes : le raisonnement avant la complexité"
date: 2026-07-21 10:10:00 +0900
categories: [Computer Science, Algorithms]
tags: [data-structures, algorithms, big-o, amortized-analysis, graph-algorithms, invariants, benchmarking]
description: "Comment interpréter Big O et l'analyse amortie comme de véritables modèles de coût, puis choisir tableaux, tables de hachage, tas, arbres et algorithmes de graphe selon les exigences, la correction et les mesures."
math: true
lang: fr-FR
hidden: true
translation_key: data-structures-algorithms-practical-mental-model
---

{% include language-switcher.html %}

Mémoriser les structures de données et les algorithmes comme un tableau d'examen ne laisse que des phrases telles que « une table de hachage est en \(O(1)\), tandis qu'un arbre est en \(O(\log n)\) ». Dans une conception réelle, posez d'abord les questions suivantes.

- Les données tiennent-elles en mémoire ?
- Quelle opération est la plus fréquente : recherche, insertion, extraction du minimum ou requête sur une plage ?
- Faut-il préserver l'ordre et les doublons ?
- La latence dans le pire cas est-elle importante, ou le débit moyen compte-t-il davantage ?
- Quelle est la distribution des données et existe-t-il un risque d'entrée hostile ?
- Quels sont les coûts liés à la localité du cache, aux allocations et à la concurrence ?

Choisir un algorithme n'est pas un exercice de nomenclature. C'est **le travail qui consiste à traduire les exigences en modèle de coût et en invariants de correction**.

## 1. Définir les variables de taille avant l'analyse

Big O n'a aucun sens si l'on ignore ce que représente \(n\) dans l'expression de complexité.

- Nombre d'éléments d'un tableau \(n\)
- Nombre de sommets \(V\) et d'arêtes \(E\) d'un graphe
- Longueur d'une chaîne \(L\)
- Nombre de requêtes \(Q\)
- Dimension de l'état \(d\)
- Nombre de bits \(b\) d'une valeur entière

Par exemple, décrire sans condition un algorithme de graphe comme étant en \(O(n^2)\) efface la différence entre graphes creux et denses. Un parcours en largeur fondé sur une liste d'adjacence est en

$$
\Theta(V+E)
$$

tandis que le balayage d'une matrice d'adjacence entière est en

$$
\Theta(V^2)
$$

La représentation, et pas seulement le nom de l'algorithme, modifie la complexité.

## 2. Big O, grand thêta et grand oméga

### Borne supérieure : \(O(g(n))\)

S'il existe une constante \(c\) telle que, pour \(n\) suffisamment grand,

$$
0\le f(n)\le c\,g(n)
$$

alors \(f(n)=O(g(n))\). Comme il s'agit d'une borne supérieure, une fonction dans \(\Theta(n)\) peut aussi être décrite comme étant en \(O(n^2)\). Lorsque c'est possible, la borne serrée \(\Theta\) apporte davantage d'information.

### Même ordre asymptotique : \(\Theta(g(n))\)

Si

$$
c_1g(n)\le f(n)\le c_2g(n)
$$

alors \(f(n)=\Theta(g(n))\).

### Borne inférieure : \(\Omega(g(n))\)

Si \(f(n)\ge c\,g(n)\) pour \(n\) suffisamment grand, il s'agit d'une borne inférieure.

### Préciser le pire cas, le cas moyen et l'espérance

« Une recherche par hachage est en \(O(1)\) » est généralement une affirmation en espérance ou amortie, qui suppose un hachage et un facteur de charge convenables. Le pire cas diffère lorsque les collisions se concentrent. Distinguez les notions suivantes.

- Pire cas par opération
- Coût espéré lié à l'aléa
- Cas moyen selon une distribution d'entrée précisée
- Coût amorti sur une suite d'opérations

Moyenne et amortissement ne signifient pas la même chose.

## 3. Analyse amortie : répartir les rares opérations coûteuses sur toute la séquence

Lorsqu'un tableau dynamique atteint sa capacité, la création d'un tampon plus grand et la copie de tous les éléments peuvent faire coûter une insertion finale \(\Theta(n)\). Mais si la capacité croît selon un facteur constant, le nombre total de copies sur \(m\) insertions est borné par une série géométrique.

$$
1+2+4+\cdots < 2m.
$$

Le coût total de \(m\) ajouts est donc \(\Theta(m)\), et le coût amorti de chaque ajout est \(\Theta(1)\).

L'analyse amortie n'est pas une moyenne empirique affirmant que « c'était rapide la plupart du temps ». Elle prouve que **le coût total ne dépasse pas la borne, quelle que soit la suite d'entrées**.

Les méthodes de preuve courantes sont :

- Méthode globale : sommer directement le coût de toute la séquence
- Méthode comptable : facturer à l'avance un crédit aux opérations peu coûteuses
- Méthode du potentiel : inclure dans le coût les variations du potentiel de la structure de données

Dans un système soumis à une échéance de latence, un \(O(1)\) amorti peut ne pas suffire. Déterminez si une pause en \(O(n)\) lors d'un redimensionnement est acceptable, et si un rehachage progressif ou une réservation de capacité est nécessaire.

## 4. La complexité est un coût multidimensionnel

Choisir uniquement selon la complexité temporelle néglige :

- la mémoire auxiliaire ;
- le nombre d'allocations ;
- les défauts de cache et le suivi de pointeurs ;
- la prédiction de branchement ;
- la taille de sérialisation ;
- la contention en parallèle ;
- le temps de prétraitement ;
- le rapport entre mises à jour et requêtes.

Même avec le même \(O(n)\), parcourir un tableau contigu peut être bien plus rapide que parcourir une structure chaînée. À l'inverse, une liste chaînée peut être avantageuse pour détacher un élément lorsque l'on possède déjà un pointeur vers le nœud central. Le coût nécessaire pour trouver ce nœud ne doit pas être omis.

## 5. Carte de sélection des structures de données

### Tableau ou tableau dynamique

**Points forts**

- Accès par indice en \(\Theta(1)\)
- Mémoire contiguë et bonne localité du cache
- Ajout en fin amorti en \(\Theta(1)\)
- Adapté au tri, à la recherche dichotomique et au traitement vectorisé

**Points faibles**

- L'insertion ou la suppression au milieu est en \(\Theta(n)\), car les éléments doivent être déplacés
- Pics dus au redimensionnement et capacité inutilisée
- Les pointeurs stables peuvent être invalidés

C'est un excellent choix par défaut. Vérifiez si la « liste » d'un langage est réellement un tableau dynamique ou une liste chaînée.

### Liste chaînée

**Points forts**

- Insertion et suppression en \(\Theta(1)\) lorsque la position du nœud est déjà connue
- Structures nécessitant des raccordements et des références de nœuds stables

**Points faibles**

- Accès par indice et recherche en \(\Theta(n)\)
- Allocation par nœud et surcoût des pointeurs
- Mauvaise localité du cache

Ne la choisissez pas simplement parce qu'« il y a beaucoup d'insertions ». Si trouver le point d'insertion coûte \(\Theta(n)\), l'avantage global peut disparaître.

### Table de hachage

**Points forts**

- Recherche, insertion et suppression par clé en \(\Theta(1)\) en espérance
- Appartenance, comptage de fréquences et déduplication

**Points faibles**

- Inadaptée à l'ordre des clés et aux requêtes sur des plages
- Dépend de la qualité du hachage et du facteur de charge
- Coût du rehachage
- Risques liés aux collisions hostiles et aux clés mutables

L'égalité et le hachage doivent être cohérents.

$$
a=b\quad\Longrightarrow\quad hash(a)=hash(b).
$$

Modifier un champ participant à l'égalité après avoir utilisé un objet comme clé peut rendre l'entrée introuvable.

### Arbre de recherche équilibré

**Points forts**

- Recherche, insertion et suppression dans le pire cas en \(\Theta(\log n)\)
- Parcours trié
- Prédécesseur et successeur
- Requêtes sur des plages

**Points faibles**

- Constantes et surcoût des pointeurs supérieurs à ceux d'une table de hachage
- Complexité de l'implémentation de l'équilibrage

Il convient lorsqu'il faut une table associative ou un ensemble ordonné, des requêtes d'intervalle ou un comportement prévisible dans le pire cas.

### Tas ou file de priorité

Pour un tas binaire :

- Consulter le minimum ou le maximum : \(\Theta(1)\)
- Insérer : \(\Theta(\log n)\)
- Extraire le minimum ou le maximum : \(\Theta(\log n)\)
- Rechercher une clé quelconque parmi tous les éléments non ordonnés : \(\Theta(n)\)
- Construction en bloc du tas : \(\Theta(n)\)

Un tas n'est pas un « conteneur trié ». Il ne garantit que la priorité de la racine. Utilisez-le lorsque vous extrayez sans cesse l'élément de plus haute priorité suivant, comme dans un top-\(k\), un ordonnanceur ou la frontière de Dijkstra.

### File à double extrémité

Utilisez-la lorsqu'une file exige des insertions et extractions en \(\Theta(1)\) aux deux extrémités. Dans un parcours en largeur, évitez de supprimer répétitivement le premier élément d'un tableau et de provoquer des décalages en \(\Theta(n)\).

### Structure d'ensembles disjoints

Lorsqu'on fusionne sans cesse des ensembles et qu'on interroge leur connexité, la compression des chemins combinée à l'union par rang ou par taille donne un coût amorti par opération pratiquement constant :

$$
O(\alpha(n))
$$

Cette structure ne convient pas si une suppression dynamique ou le chemin lui-même est nécessaire.

## 6. Remonter de l'objectif vers la structure de données

| Exigence centrale | Premier candidat | Conditions à vérifier |
|---|---|---|
| Accès par indice et parcours séquentiel | tableau dynamique | Fréquence des modifications au milieu, capacité |
| Appartenance d'une clé | ensemble/table de hachage | Besoin d'ordre ou de garanties dans le pire cas |
| Clés triées et requêtes sur des plages | arbre équilibré | Rapport entre mises à jour et requêtes |
| Extraction répétée du minimum | tas | Prise en charge de la suppression arbitraire ou de la diminution de clé |
| FIFO | file à double extrémité | File bornée, concurrence |
| LIFO | pile ou tableau dynamique | Profondeur maximale |
| Fusion et requête de connexité | ensembles disjoints | Absence garantie de suppression d'arêtes |
| Parcours d'un graphe creux | liste d'adjacence | Arêtes multiples, orientation |
| Graphe dense ou test rapide d'une arête | matrice d'adjacence ou ensemble de bits | Acceptabilité d'une mémoire en \(V^2\) |

Un service peut séparer sa source de vérité de ses index de consultation. Par exemple, les enregistrements peuvent être conservés dans un tableau, avec un index de hachage pour la recherche par identifiant et un tas pour la priorité. Dans ce cas, **l'invariant de synchronisation entre les représentations** devient un nouveau coût.

## 7. La représentation du graphe détermine l'algorithme

### Liste d'adjacence

La mémoire est en \(\Theta(V+E)\), et le parcours des voisins d'un sommet est proportionnel à son degré. C'est le choix par défaut pour les graphes creux.

### Matrice d'adjacence

La mémoire est en \(\Theta(V^2)\), mais vérifier l'existence d'une arête prend \(\Theta(1)\). Elle peut convenir aux graphes denses, aux petits graphes et aux opérations parallèles au niveau des bits.

### Liste d'arêtes

Elle est simple pour les algorithmes qui parcourent ou trient toutes les arêtes une seule fois. La recherche des voisins d'un sommet quelconque est lente sans index séparé.

Lors du choix d'une représentation, décidez également si le graphe est orienté ou non, pondéré ou non, s'il autorise les boucles et les arêtes parallèles, s'il est mutable, et à quel point les identifiants de sommets sont denses.

## 8. Préconditions des parcours en largeur, en profondeur et de Dijkstra

### Parcours en largeur

Le parcours en largeur trouve la plus courte distance en nombre d'arêtes depuis une source dans un graphe non pondéré, ou dans un graphe dont toutes les arêtes ont le même coût.

~~~python
from collections import deque

def bfs(graph, source):
    distance = {source: 0}
    parent = {source: None}
    queue = deque([source])

    while queue:
        u = queue.popleft()
        for v in graph[u]:
            if v in distance:
                continue
            distance[v] = distance[u] + 1
            parent[v] = u
            queue.append(v)

    return distance, parent
~~~

Marquez un sommet comme visité lorsqu'il est **ajouté à la file**, et non lorsqu'il en est retiré, afin d'éviter que le même sommet soit ajouté plusieurs fois.

Cet exemple suppose que tout sommet terminal apparaissant comme voisin est également une clé de `graph`. Une véritable API doit valider cet invariant de représentation ou gérer explicitement une adjacence vide avec une expression telle que `graph.get(u, ())`.

### Parcours en profondeur

Le parcours en profondeur est une brique de base pour l'accessibilité, les composantes connexes, la détection de cycles et le tri topologique. Mais « utiliser un parcours en profondeur » ne suffit pas à déterminer les cycles.

- Graphe non orienté : un voisin déjà visité autre que l'arête vers le parent signale un cycle
- Graphe orienté : il faut une arête de retour vers la pile de récursion actuelle ou un état de couleur
- Ordre topologique : valable uniquement pour un graphe orienté acyclique

L'ordre de parcours d'un arbre de recherche en profondeur peut varier selon l'ordre d'itération des adjacences. Fixez l'ordre des voisins lorsqu'une sortie déterministe est requise.

### Dijkstra

Dijkstra trouve les plus courts chemins depuis une source lorsque **tous les poids des arêtes sont positifs ou nuls**.

~~~python
from heapq import heappop, heappush
from math import inf, isfinite

def dijkstra(graph, source):
    distance = {v: inf for v in graph}
    distance[source] = 0.0
    heap = [(0.0, source)]

    while heap:
        best, u = heappop(heap)
        if best != distance[u]:
            continue

        for v, weight in graph[u]:
            if not isfinite(weight) or weight < 0:
                raise ValueError("Dijkstra requires finite nonnegative weights")
            candidate = best + weight
            if candidate < distance[v]:
                distance[v] = candidate
                heappush(heap, (candidate, v))

    return distance
~~~

Comme des entrées périmées correspondant au même sommet peuvent rester dans la file de priorité, il faut les détecter. Une implémentation employant un tas qui permet directement de diminuer une clé est différente.

Avec une liste d'adjacence et un tas binaire, la complexité temporelle habituelle est \(O((V+E)\log V)\), souvent écrite \(O(E\log V)\) pour un graphe connexe. Pour l'implémentation ci-dessus, qui autorise les entrées dupliquées, tenez également compte de la mémoire du tas et des coûts constants.

### Sélection selon la structure des poids

| Poids des arêtes | Algorithme candidat |
|---|---|
| Tous égaux | Parcours en largeur |
| 0 ou 1 | Parcours en largeur 0–1 |
| Tous positifs ou nuls | Dijkstra |
| Arêtes négatives possibles | Famille Bellman–Ford |
| Graphe orienté acyclique | Relâchement dans l'ordre topologique |
| Toutes les paires, graphe dense ou petit | Envisager Floyd–Warshall et d'autres |

Lorsqu'un cycle négatif est accessible, un plus court chemin fini peut ne pas être défini. C'est un problème de définition, et non une défaillance de l'algorithme.

## 9. Récursion et itération

La récursion exprime les définitions des arbres et des méthodes diviser pour régner de façon proche de la structure du code. Elle a aussi les coûts suivants.

- Limites de profondeur de la pile d'appels
- Allocation des cadres et surcoût des appels de fonctions
- Débordement de pile dans les arbres profonds ou déséquilibrés
- État implicite et reprise sur erreur

L'itération gère directement l'état du parcours avec une pile ou une file explicite.

~~~python
def iterative_dfs(graph, source):
    visited = set()
    stack = [source]

    while stack:
        u = stack.pop()
        if u in visited:
            continue
        visited.add(u)
        for v in reversed(graph[u]):
            if v not in visited:
                stack.append(v)

    return visited
~~~

Cet exemple suppose que l'adjacence est une séquence déterministe prise en charge par `reversed`. Pour reproduire l'ordre de visite d'un parcours récursif, le comportement LIFO de la pile peut exiger d'y pousser les voisins dans l'ordre inverse. Même lorsque l'ordre de visite n'affecte pas la correction, vérifiez que les tests n'en dépendent pas accidentellement.

Les critères de choix comprennent :

- Profondeur faible et clairement bornée : la récursion peut être plus lisible
- Entrée hostile ou profondeur en \(O(n)\) : préférer l'itération
- Interruption, reprise ou sérialisation du parcours : l'état explicite est avantageux
- Traitement en ordre postfixe : conserver l'état d'entrée ou de sortie dans le cadre de pile

Vérifiez si le langage et l'environnement d'exécution garantissent l'optimisation des appels terminaux.

## 10. Relier les preuves au code avec des invariants de correction

Pour montrer qu'un algorithme est correct pour toute entrée valide, et pas seulement qu'il « fonctionne sur l'exemple », utilisez un invariant de boucle.

### Trois étapes

1. **Initialisation** : l'invariant est vrai avant le début de la boucle.
2. **Conservation** : il reste vrai après une itération.
3. **Terminaison** : à la fin de la boucle, l'invariant produit la conclusion recherchée.

### Exemple d'invariant de recherche dichotomique

Avec l'intervalle semi-ouvert \([lo,hi)\) :

- Si une réponse existe, elle se trouve toujours dans \([lo,hi)\).
- \([0,lo)\) ne satisfait pas la condition.
- \([hi,n)\) satisfait la condition.

Conservez la même convention de bornes dans les mises à jour et le retour pour éviter les décalages d'une unité.

### Invariant du parcours en largeur

Les distances des sommets retirés de la file pour traitement ne décroissent pas, et le premier chemin découvert contient le nombre minimal d'arêtes. Cela dépend de la précondition selon laquelle toutes les arêtes ont le même coût.

### Invariant de Dijkstra

La distance d'un sommet finalisé par le minimum valide du tas est sa plus courte distance. Des arêtes positives ou nulles sont nécessaires pour prouver qu'un chemin non encore visité ne pourra pas réduire cette valeur par la suite.

### Invariant du tas

Dans un tas minimum, la clé de chaque nœud est inférieure ou égale à celles de ses enfants. Un tri total n'est pas nécessaire. Vérifiez que la réparation locale après une insertion ou une extraction restaure cet invariant.

## 11. Les cas limites sont des données de conception, pas des exceptions tardives

### Collections

- Vide
- Un seul élément
- Tous les éléments égaux
- Déjà triée ou triée en ordre inverse
- Nombreux doublons
- Juste avant et juste après une limite de capacité
- Clé absente et suppression répétée

### Valeurs numériques

- Zéro et zéro négatif
- Valeurs représentables minimale et maximale
- Débordement d'entier
- Autorisation ou non de NaN et de l'infini
- Égalité et tolérance des nombres à virgule flottante
- Ordres de grandeur très différents

### Graphes

- Sommet isolé
- Composante déconnectée
- Boucle
- Arête parallèle
- Confusion entre graphe orienté et non orienté
- Cycle et cycle négatif accessible
- Source absente du graphe
- Plusieurs plus courts chemins

### Ressources

- Entrée qui ne tient pas en mémoire
- Profondeur maximale de récursion
- Annulation et expiration
- Lectures et écritures partielles
- Modification concurrente

Ne laissez pas les cas limites uniquement dans une liste de tests. Décidez dans le contrat de l'API s'il faut rejeter, normaliser ou prendre en charge chacun d'eux.

## 12. Profilage : trouver où se situe le coût au lieu de le deviner

Même un algorithme de bonne complexité peut ne pas être le véritable goulot d'étranglement. Suivez cette séquence avant d'optimiser.

1. Définissez des objectifs de latence de bout en bout ou de débit.
2. Profilez avec une charge semblable à celle de la production.
3. Séparez le processeur, les allocations, l'attente des E/S et la contention des verrous.
4. Examinez la fréquence des appels et le coût par appel sur le chemin critique.
5. Après avoir modifié l'algorithme ou la représentation, mesurez à nouveau dans les mêmes conditions.

Supprimer une boucle en \(O(n^2)\), une sérialisation inutile, des requêtes répétées à la base de données ou un mauvais schéma d'allocation produit souvent un effet bien supérieur à une micro-optimisation.

## 13. Conditions de confiance dans un banc d'essai

### Charge de travail

- Mesurer plusieurs points de la véritable plage de tailles
- Inclure des distributions triées, riches en doublons, déséquilibrées et hostiles, et pas seulement des entrées aléatoires
- Reproduire les rapports lecture/écriture et succès/échec du cache
- Distinguer les caches chauds des caches froids

### Mesure

- Contrôler les effets de préchauffage, de compilation à la volée et du ramasse-miettes
- Séparer la préparation de la zone chronométrée
- Mesurer la médiane et les centiles de queue sur plusieurs répétitions
- Consigner la variation de fréquence du processeur et la charge d'arrière-plan
- Consommer les résultats pour empêcher l'élimination du code mort
- Mesurer également le pic de mémoire et les allocations

### Interprétation

Un graphique à axes logarithmiques ou le nombre d'opérations selon la taille d'entrée peut révéler le point de bascule. Un algorithme simple peut être plus rapide pour un petit \(n\), tandis qu'un autre, meilleur asymptotiquement, le dépasse pour un grand \(n\).

Un banc d'essai ne prouve pas une vérité universelle. Il apporte des indices sur le matériel, l'environnement d'exécution et la distribution d'entrée mesurés.

## 14. Processus pratique de sélection

1. **Répertorier les opérations** : estimer la fréquence des recherches, insertions, suppressions, minimums, plages et parcours.
2. **Définir le contrat** : décider de l'ordre, des doublons, de la mutabilité, de la concurrence et des limites de latence.
3. **Définir les tailles et distributions** : consigner \(n,V,E,Q\), la densité, l'asymétrie et la possibilité d'une entrée hostile.
4. **Comparer les structures candidates** : dresser un tableau du temps et de la mémoire moyens, dans le pire cas et amortis.
5. **Écrire les invariants de correction** : consigner les conditions que la structure et l'algorithme doivent préserver.
6. Construire **l'implémentation correcte la plus simple**.
7. Vérifier les invariants avec **des tests de limites et de propriétés**.
8. Utiliser **le profilage** pour trouver le véritable goulot d'étranglement.
9. Comparer les solutions avec un **banc d'essai représentatif**.
10. **Consigner le raisonnement** : conserver les hypothèses de charge et les seuils de réévaluation.

## 15. Liste de vérification

- [ ] Les variables de taille des expressions de complexité sont-elles définies ?
- [ ] Le pire cas, l'espérance, la moyenne et l'amortissement sont-ils distingués ?
- [ ] La mémoire, les allocations et la localité sont-elles évaluées en plus du temps ?
- [ ] Le coût d'insertion d'une liste chaînée inclut-il la recherche de la position ?
- [ ] Les conditions d'ordre, de collisions et de clés mutables du hachage ont-elles été vérifiées ?
- [ ] Le tas est-il bien compris comme autre chose qu'une structure entièrement triée ?
- [ ] La représentation du graphe convient-elle à sa densité et aux requêtes ?
- [ ] Les préconditions de poids et d'orientation des arêtes pour les parcours en largeur, en profondeur et Dijkstra ont-elles été vérifiées ?
- [ ] La profondeur de récursion n'est-elle pas non bornée par l'entrée ?
- [ ] Peut-on expliquer l'initialisation, la conservation et la terminaison de l'invariant de boucle ?
- [ ] Les cas vides, les doublons, les débordements et les déconnexions sont-ils testés ?
- [ ] Le goulot d'étranglement a-t-il été confirmé par profilage avant l'optimisation ?
- [ ] La charge et l'environnement du banc d'essai sont-ils consignés ?
- [ ] La latence de queue et le pic de mémoire ont-ils été examinés en plus des moyennes ?

## 16. Pièges et limites fréquents

### Une structure dont le Big O est plus petit est toujours plus rapide

Les constantes, la localité du cache, les allocations et la plage réelle de \(n\) déterminent le point de bascule. Il faut à la fois une analyse asymptotique et des bancs d'essai.

### Déduire la complexité du seul nom d'une bibliothèque

Des conteneurs portant le même nom peuvent avoir des implémentations différentes selon les langages. Consultez dans la documentation officielle les garanties des opérations et les règles d'invalidation.

### Supposer qu'une entrée triée est une entrée facile

Selon l'algorithme, une entrée triée ou triée en sens inverse peut constituer le pire cas. Examinez les hypothèses qui sous-tendent les pivots, le hachage et l'équilibrage des arbres.

### Donner des arêtes négatives à Dijkstra et ne vérifier que le résultat

Cela peut fonctionner par hasard sur un petit exemple, mais la précondition de la preuve de correction est rompue. Placez la validation des entrées à la frontière de l'algorithme.

### Supposer que convertir une récursion en boucle préserve toujours l'ordre

L'arbre de parcours change selon l'ordre dans lequel les voisins sont poussés sur la pile explicite et le moment où ils sont marqués comme visités.

### Figer définitivement un choix sur la base d'un seul banc d'essai

Lorsque la taille des données, le rapport lecture/écriture ou la version de l'environnement d'exécution change, le raisonnement peut changer lui aussi. Consignez les critères de réévaluation.

## Conclusion

Le modèle mental pratique des structures de données et des algorithmes peut se résumer ainsi.

> Commencez par écrire les opérations et garanties requises, choisissez la structure la plus simple qui les préserve, vérifiez son passage à l'échelle par une analyse asymptotique, puis mesurez-la sous la charge réelle.

Big O est une carte qui filtre les candidats, un invariant est un contrat qui préserve la correction, et le profilage comme les bancs d'essai forment le tableau de bord des coûts réels. Réunir les trois transforme le choix d'une structure de données en décision d'ingénierie plutôt qu'en exercice de mémorisation.
