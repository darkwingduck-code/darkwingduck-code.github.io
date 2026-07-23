---
title: "Principes de normalisation SQL et compromis pratiques : 1FN, 2FN, 3FN et FNBC"
date: 2026-07-21 09:50:00 +0900
categories: [Data Engineering, Database Design]
tags: [sql, normalization, 1nf, 2nf, 3nf, bcnf, functional-dependency, data-modeling]
description: "À partir des dépendances fonctionnelles et des clés candidates, ce guide explique comment évaluer les 1FN, 2FN, 3FN et FNBC, ainsi que les critères pratiques de décomposition sans perte, de préservation des dépendances et de dénormalisation."
math: true
lang: fr-FR
hidden: true
translation_key: sql-normalization-1nf-2nf-3nf-bcnf
---

{% include language-switcher.html %}

La normalisation n'est pas une règle imposant de découper une table en de nombreux morceaux. Son essence est de **gérer chaque fait à un seul endroit et de réduire ainsi les anomalies de mise à jour**. Pour l'appliquer correctement, commencez par consigner les dépendances fonctionnelles — les règles métier — plutôt que d'examiner les noms de colonnes.

Cet article évalue les formes normales dans l'ordre suivant.

$$
\text{Business rules}
\rightarrow
\text{Functional dependencies}
\rightarrow
\text{Candidate keys}
\rightarrow
\text{Normal forms}
\rightarrow
\text{Lossless, dependency-preserving decomposition}
$$

## 1. Les trois anomalies que la normalisation évite

Stocker de façon redondante des faits différents dans une même relation provoque les problèmes suivants.

- **Anomalie de mise à jour** : le même fait apparaît sur plusieurs lignes, mais seules certaines sont mises à jour.
- **Anomalie d'insertion** : un fait indépendant ne peut être enregistré que si un autre fait est également présent.
- **Anomalie de suppression** : supprimer une ligne supprime aussi l'unique occurrence d'un fait distinct.

Par exemple, si chaque ligne de commande répète le nom d'affichage du client, tout changement de nom impose de mettre à jour toutes les lignes historiques. Toutefois, si l'exigence consiste à conserver le « nom d'affichage au moment de la commande », cette répétition peut être un instantané intentionnel plutôt qu'une redondance. La pertinence de la normalisation ne dépend pas de la forme d'une colonne, mais de **la nature actuelle ou historique du fait représenté par sa valeur**.

## 2. Dépendances fonctionnelles : des règles, pas des données

Pour les ensembles d'attributs \(X,Y\) d'une relation \(R\),

$$
X\to Y
$$

signifie que deux tuples ayant la même valeur de \(X\) doivent toujours avoir la même valeur de \(Y\). \(X\) détermine fonctionnellement \(Y\).

Une précision importante : une dépendance fonctionnelle ne découle pas du simple fait que l'échantillon actuel ne contient aucun doublon. Elle doit être une règle métier applicable à toutes les données valides susceptibles d'être saisies à l'avenir.

### Dépendance triviale

Si \(Y\subseteq X\), alors \(X\to Y\) est triviale. Par exemple,

$$
\{A,B\}\to A
$$

est toujours vraie, quelle que soit la signification des valeurs.

### Fermeture

La fermeture \(X^+\) d'un ensemble d'attributs \(X\) est l'ensemble des attributs que \(X\) peut déterminer selon les dépendances fonctionnelles données. La fermeture permet d'identifier les clés candidates.

1. Commencer par \(X^+=X\).
2. Pour chaque \(Y\to Z\), si \(Y\subseteq X^+\), ajouter \(Z\) à \(X^+\).
3. Répéter jusqu'à ce que l'ensemble ne change plus.
4. Si \(X^+=R\), alors \(X\) est une superclé.
5. Si aucun sous-ensemble propre de \(X\) n'est une superclé, alors \(X\) est une clé candidate.

## 3. Distinguer précisément les termes relatifs aux clés

- **Superclé** : ensemble d'attributs qui identifie une ligne de manière unique. Il peut contenir des attributs superflus.
- **Clé candidate** : superclé minimale qui ne peut plus être réduite.
- **Clé primaire** : clé candidate choisie comme clé représentative dans une implémentation.
- **Clé alternative** : toute clé candidate non choisie comme clé primaire.
- **Attribut premier** : attribut appartenant à au moins une clé candidate.
- **Clé étrangère** : attribut qui référence une clé candidate ou unique d'une autre relation.

Ajouter un identifiant auto-incrémenté comme clé primaire n'efface ni les clés candidates métier d'origine ni les dépendances fonctionnelles. Une clé naturelle qui ne doit pas être dupliquée exige toujours une contrainte `UNIQUE` distincte.

## 4. 1FN : une valeur par position d'attribut dans une relation

La première forme normale est le principe relationnel selon lequel chaque intersection tuple-attribut contient une seule valeur du domaine concerné. Les colonnes répétées et les listes de longueur variable dans une cellule sont généralement séparées dans leurs propres relations.

Forme incorrecte :

| item_id | étiquettes |
|---|---|
| un identifiant | plusieurs étiquettes séparées par des virgules |

Forme normalisée :

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

### « Atomique » renvoie à la sémantique des requêtes, pas à la taille du type

Une date n'a pas besoin d'être décomposée en colonnes année, mois et jour pour satisfaire la 1FN. Si un domaine de dates est traité comme une seule valeur, une colonne de date est atomique. À l'inverse, stocker une adresse entière dans une chaîne peut ne pas violer la 1FN, mais une structure distincte convient mieux si une recherche et une validation par ville sont requises.

Au lieu d'affirmer que l'utilisation d'un type JSON ou tableau viole automatiquement la 1FN, demandez-vous :

- Les éléments qu'il contient doivent-ils participer à des contraintes relationnelles et à des jointures ?
- Les éléments individuels sont-ils mis à jour indépendamment ?
- La base de données doit-elle faire respecter les règles de cardinalité et de duplication ?
- S'agit-il d'une charge utile externe exigeant une évolution du schéma ?

## 5. 2FN : supprimer les faits qui ne dépendent que d'une partie d'une clé candidate composite

La deuxième forme normale exige qu'une relation :

1. soit en 1FN ; et
2. n'ait aucun attribut non premier fonctionnellement dépendant d'un sous-ensemble propre d'une clé candidate.

Autrement dit, elle supprime les dépendances partielles. Si chaque clé candidate se compose d'un seul attribut, aucune violation de la 2FN ne peut survenir.

Considérons cette relation.

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

Si un produit ne peut apparaître qu'une fois dans une commande, la clé candidate est \((order\_id, product\_id)\). Supposons les règles métier suivantes :

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

`order_time` et `customer_id` ne dépendent que de `order_id`, une partie de la clé, tandis que `product_name` ne dépend que de `product_id` ; ces dépendances violent la 2FN.

Décomposez la relation en :

- order_header(order_id, order_time, customer_id)
- product(product_id, product_name)
- order_line(order_id, product_id, quantity, agreed_unit_price)

Ici, le prix unitaire convenu est le prix fixé pour cette ligne de commande, et non le prix actuel du produit ; il dépend donc de toute la clé composite. Le déplacer vers la relation produit au seul motif que les noms semblent liés détruirait le fait historique.

## 6. 3FN : supprimer les dépendances indirectes passant par des attributs non-clés

L'intuition de la troisième forme normale est qu'un attribut non-clé ne doit pas être déterminé indirectement par un autre attribut non-clé.

Dans l'exemple précédent, si

$$
order\_id\to customer\_id
$$

and

$$
customer\_id\to customer\_name
$$

alors la dépendance transitive

$$
order\_id\to customer\_name
$$

apparaît. Stocker le nom actuel du client dans chaque commande crée une anomalie de mise à jour ; décomposez donc en :

- customer(customer_id, current_name)
- order_header(order_id, order_time, customer_id)

### Le critère exact de la 3FN

Une relation est en 3FN si, pour chaque dépendance fonctionnelle non triviale \(X\to A\), au moins l'une des conditions suivantes est vraie :

1. \(X\) est une superclé.
2. \(A\) est un attribut premier.

Cette définition est plus exacte pour les relations possédant plusieurs clés candidates que le moyen mnémotechnique « si une non-clé détermine une non-clé, il y a toujours violation ».

## 7. FNBC : tout déterminant est une superclé

La forme normale de Boyce-Codd exige que \(X\) soit une superclé pour chaque dépendance fonctionnelle non triviale \(X\to Y\).

$$
X\to Y\text{ nontrivial}
\quad\Longrightarrow\quad
X\text{ is a superkey}.
$$

La FNBC est plus stricte que la 3FN.

$$
\mathrm{BCNF}\subseteq\mathrm{3NF}.
$$

Toute relation en FNBC est en 3FN, mais toute relation en 3FN n'est pas nécessairement en FNBC.

### Un exemple en 3FN mais pas en FNBC

Considérons la relation

~~~text
assignment(student, course, instructor)
~~~

avec les règles suivantes.

1. Un étudiant est affecté à un enseignant pour un cours donné.
2. Chaque enseignant dispense exactement un cours.

Les dépendances fonctionnelles sont :

$$
(student,course)\to instructor
$$

$$
instructor\to course
$$

Les clés candidates sont \((student,course)\) et \((student,instructor)\). Tous les attributs sont donc premiers ; les conditions de la 3FN sont satisfaites.

Cependant, `instructor` seul n'est pas une superclé mais détermine `course` ; la relation viole donc la FNBC.

Une décomposition en FNBC peut être :

- instructor_course(instructor, course)
- student_instructor(student, instructor)

Cela réduit les duplications, mais la contrainte d'origine \((student,course)\to instructor\) peut devenir difficile à vérifier uniquement au moyen de contraintes locales aux tables. C'est ici qu'apparaît le compromis entre FNBC et préservation des dépendances.

## 8. Two Conditions for a Good Decomposition

### Lossless Join

Natural-joining the decomposed relations must reconstruct the original relation without introducing spurious tuples.

For a decomposition into two relations \(R_1,R_2\), it is lossless if either of the following holds in the functional-dependency closure:

$$
(R_1\cap R_2)\to R_1
$$

or

$$
(R_1\cap R_2)\to R_2.
$$

The intuition is that the shared attributes must act as a key for at least one of the relations.

### Dependency Preservation

A decomposition is dependency-preserving if the original functional dependencies can be enforced through local constraints on each relation, without a join.

3NF synthesis is well suited to achieving both lossless join and dependency preservation. A BCNF decomposition can be made lossless, but it does not always preserve every dependency. Thus, “a higher normal form always produces a better schema” is false.

## 9. A Practical Normalization Workflow

### Step 1: Write Facts as Sentences

Before drawing an ERD, state the business rules in forms such as:

- One A can have multiple Bs.
- Each B belongs to exactly one C.
- Is a price a current attribute or a snapshot at transaction time?
- Is an identifier never reused over its entire lifetime?

### Step 2: List Candidate Keys and Functional Dependencies

Do not consider only the primary key; identify every candidate key. Include unique constraints, nullable columns, and temporal validity.

### Step 3: Derive a Minimal Cover

- Split each right-hand side into a single attribute.
- Remove extraneous attributes from each left-hand side.
- Remove redundant dependencies implied by the others.

### Step 4: Assess the Normal Form

Start with 1NF and progress through 2NF, 3NF, and BCNF. Connect each violation to one concrete update, insert, or delete anomaly.

### Step 5: Check Decomposition Quality

Verify lossless join and dependency preservation. If a constraint spans multiple tables, document the transaction, trigger, assertion alternative, or application invariant that enforces it.

### Step 6: Design the Physical Schema

Add PK, UNIQUE, FK, NOT NULL, CHECK, and indexes. Do not assume the database automatically creates an index on foreign-key columns; verify the behavior of the DBMS in use.

### Step 7: Evaluate Against Real Queries and Write Paths

Measure query plans, cardinality, locking, write amplification, and storage. Intentionally denormalize only where a performance problem has been demonstrated.

## 10. When Denormalization Is Reasonable

Normalization is the default for designing the logical source of truth. Derived representations may be appropriate in the following cases.

### Read Performance

If frequent aggregates or multiple joins are an actual bottleneck, consider a materialized view, indexed view, or summary table. Specify the source relations and refresh policy.

### Analytical Models

An OLAP star schema prioritizes query simplicity and scan efficiency around facts and dimensions. It is safer to view it as a transformed serving model than as a direct replacement for the OLTP source schema.

### Events and Snapshots

An immutable event payload may duplicate some values to preserve the state at that time. Distinguish current master data from historical event truth.

### Preserving External Documents

If an external API payload must be preserved in its original form, raw JSON and normalized query tables can coexist. Using the raw payload as the only query model can make constraints and migrations difficult.

Every denormalization should also define:

- the authoritative source;
- the party responsible for updates;
- the synchronous or asynchronous refresh method;
- acceptable staleness;
- the rebuild procedure; and
- a query that detects inconsistency.

## 11. Time and History Are Separate Dimensions

“A customer's name” may not be one current value.

- current canonical name
- display name at the time of the order
- legal name during a particular validity period
- raw name received in the original event

When temporal requirements exist, distinguish `valid_from`, `valid_to`, system time, and event time. If the current table is normalized but values are simply overwritten when history is needed, reproducibility is lost.

## 12. Validation Checklist

- [ ] Are the functional dependencies business rules rather than coincidences in a sample?
- [ ] Have all candidate keys besides the primary key been identified?
- [ ] Does a surrogate key conceal duplicates in a natural key?
- [ ] Was 1NF atomicity assessed according to usage and domain semantics?
- [ ] Were partial dependencies on a composite key checked?
- [ ] Were transitive dependencies through non-key attributes checked?
- [ ] Was the prime-attribute exception in 3NF applied correctly?
- [ ] Was the BCNF decomposition checked for loss of dependency preservation?
- [ ] Was the decomposition verified to have a lossless join?
- [ ] Are the rules actually enforced with PK, UNIQUE, FK, and CHECK constraints?
- [ ] Are current facts distinguished from historical snapshots?
- [ ] Does every denormalized value have a source and refresh policy?
- [ ] Were performance conclusions verified with real query plans?

## 13. Common Pitfalls

### The Misconception That Adding One ID to Every Table Guarantees 2NF

The fact that a surrogate primary key is a single column does not eliminate partial dependencies on the original business candidate keys. The anomalies remain.

### The Misconception That NULL Simplifies Functional Dependencies

The semantics of SQL NULL, three-valued logic, and a UNIQUE constraint's treatment of NULL vary by DBMS and must be checked. Making a required business identifier nullable obscures candidate-key reasoning.

### Designing Solely to Reduce Joins

Joins are a fundamental relational-database operation. Merging tables based on one read query while ignoring redundant-update cost and consistency risk can increase total system cost.

### The Misconception That Normalization Solves All Integrity Problems

Normal forms address functional dependencies and redundancy. Rules involving range constraints, cross-row aggregates, temporal overlaps, or state transitions require additional constraints and transaction design.

### Mechanically Prioritizing BCNF Above Everything

A decomposition may lose dependency preservation and make a rule impossible to check without joins or complex triggers. Remaining in 3NF can sometimes be operationally safer.

## Conclusion

1NF, 2NF, 3NF, and BCNF are not a sequence to memorize; they are a framework for identifying and removing different causes of redundancy.

- 1NF: relationally one value at each attribute position
- 2NF: removal of non-prime facts that depend on only part of a composite candidate key
- 3NF: control of indirect dependencies through non-key attributes
- BCNF: restriction of every determinant to a superkey

The practical goal is not the highest number. It is a **schema in which the database consistently enforces business rules, decomposition is lossless, and required dependencies are preserved in an operationally viable way**.
