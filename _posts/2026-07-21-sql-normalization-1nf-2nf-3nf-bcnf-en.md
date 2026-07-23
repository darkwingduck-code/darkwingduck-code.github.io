---
title: "SQL Normalization Principles and Practical Tradeoffs: 1NF, 2NF, 3NF, and BCNF"
date: 2026-07-21 09:50:00 +0900
categories: [Data Engineering, Database Design]
tags: [sql, normalization, 1nf, 2nf, 3nf, bcnf, functional-dependency, data-modeling]
description: "Starting from functional dependencies and candidate keys, this guide explains how to assess 1NF, 2NF, 3NF, and BCNF, along with practical criteria for lossless decomposition, dependency preservation, and denormalization."
math: true
lang: en
hidden: true
translation_key: sql-normalization-1nf-2nf-3nf-bcnf
---

{% include language-switcher.html %}

Normalization is not a rule that says to split a table into many pieces. Its essence is to **manage each fact in exactly one place and thereby reduce update anomalies**. To apply it properly, first write down the functional dependencies—the business rules—rather than looking at column names.

This article assesses normal forms in the following sequence.

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

## 1. The Three Anomalies That Normalization Prevents

Storing different facts redundantly in one relation causes the following problems.

- **Update anomaly**: The same fact appears in multiple rows, but only some of them are updated.
- **Insert anomaly**: An independent fact cannot be recorded unless another fact is also present.
- **Delete anomaly**: Deleting one row also removes the only instance of a separate fact.

For example, if every order row repeats the customer's display name, a name change requires updating every historical row. If the requirement is to preserve the “display name at the time of the order,” however, the repetition may be an intentional snapshot rather than redundancy. Whether normalization is appropriate depends not on the shape of a column, but on **whether its value represents a current fact or a historical fact**.

## 2. Functional Dependencies: Rules, Not Data

For attribute sets \(X,Y\) in relation \(R\),

$$
X\to Y
$$

means that any two tuples with the same \(X\) value must always have the same \(Y\) value. \(X\) functionally determines \(Y\).

An important caveat is that a functional dependency does not arise merely because the current sample happens to contain no duplicates. A dependency must be a business rule that applies to all valid data that may be entered in the future.

### Trivial Dependency

If \(Y\subseteq X\), then \(X\to Y\) is trivial. For example,

$$
\{A,B\}\to A
$$

always holds regardless of what the values mean.

### Closure

The closure \(X^+\) of an attribute set \(X\) is the set of all attributes that \(X\) can determine under the given functional dependencies. Candidate keys are identified using closure.

1. Start with \(X^+=X\).
2. For each \(Y\to Z\), if \(Y\subseteq X^+\), add \(Z\) to \(X^+\).
3. Repeat until the set no longer changes.
4. If \(X^+=R\), then \(X\) is a superkey.
5. If no proper subset of \(X\) is a superkey, then \(X\) is a candidate key.

## 3. Distinguish Key Terms Precisely

- **Superkey**: An attribute set that uniquely identifies a row. It may include unnecessary attributes.
- **Candidate key**: A minimal superkey that cannot be reduced further.
- **Primary key**: The candidate key chosen as the representative key in an implementation.
- **Alternate key**: Any candidate key not selected as the primary key.
- **Prime attribute**: An attribute included in at least one candidate key.
- **Foreign key**: An attribute that references a candidate or unique key in another relation.

Adding an auto-incrementing ID as the primary key does not erase the original business candidate keys or functional dependencies. A natural key that must not be duplicated still needs a separate `UNIQUE` constraint.

## 4. 1NF: One Value per Attribute Position in a Relation

First Normal Form is the relational principle that every tuple–attribute intersection contains a single value from the relevant domain. Repeating columns and variable-length lists inside one cell are generally separated into their own relations.

Incorrect form:

| item_id | labels |
|---|---|
| one identifier | multiple comma-separated labels |

Normalized form:

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

### “Atomic” Refers to Query Semantics, Not Data-Type Size

A date does not need to be split into year, month, and day columns to satisfy 1NF. If a date domain is treated as one value, a date column is atomic. Conversely, storing an entire address as one string may not violate 1NF, but a separate structure is more appropriate if searching and validation by city are required.

Rather than declaring that the use of a JSON or array type automatically violates 1NF, ask:

- Must the elements inside it participate in relational constraints and joins?
- Are individual elements updated independently?
- Must the database enforce cardinality and duplication rules?
- Is it an external payload that requires schema evolution?

## 5. 2NF: Remove Facts That Depend on Only Part of a Composite Candidate Key

Second Normal Form requires that a relation:

1. be in 1NF; and
2. have no non-prime attribute functionally dependent on a proper subset of any candidate key.

In other words, it removes partial dependencies. If every candidate key consists of a single attribute, a 2NF violation cannot occur.

Consider this relation.

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

If a product can appear only once in an order, the candidate key is \((order\_id, product\_id)\). Suppose the business rules are:

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

`order_time` and `customer_id` depend only on `order_id`, part of the key, while `product_name` depends only on `product_id`; these dependencies violate 2NF.

Decompose the relation into:

- order_header(order_id, order_time, customer_id)
- product(product_id, product_name)
- order_line(order_id, product_id, quantity, agreed_unit_price)

Here, the agreed unit price is the price agreed for that order line, not the product's current price, so it depends on the entire composite key. Moving it to the product relation merely because the names sound related would destroy the historical fact.

## 6. 3NF: Remove Indirect Dependencies Through Non-Key Attributes

The intuition behind Third Normal Form is that a non-key attribute should not be determined indirectly through another non-key attribute.

In the preceding example, if

$$
order\_id\to customer\_id
$$

and

$$
customer\_id\to customer\_name
$$

then the transitive dependency

$$
order\_id\to customer\_name
$$

arises. Storing the customer's current name in every order creates an update anomaly, so decompose it into:

- customer(customer_id, current_name)
- order_header(order_id, order_time, customer_id)

### The Exact 3NF Criterion

A relation is in 3NF if, for every nontrivial functional dependency \(X\to A\), at least one of the following is true:

1. \(X\) is a superkey.
2. \(A\) is a prime attribute.

This definition is more accurate for relations with multiple candidate keys than the mnemonic “if a non-key determines a non-key, it is always a violation.”

## 7. BCNF: Every Determinant Is a Superkey

Boyce–Codd Normal Form requires \(X\) to be a superkey for every nontrivial functional dependency \(X\to Y\).

$$
X\to Y\text{ nontrivial}
\quad\Longrightarrow\quad
X\text{ is a superkey}.
$$

BCNF is stronger than 3NF.

$$
\mathrm{BCNF}\subseteq\mathrm{3NF}.
$$

Every BCNF relation is in 3NF, but not every 3NF relation is in BCNF.

### An Example in 3NF but Not BCNF

Consider the relation

~~~text
assignment(student, course, instructor)
~~~

with the following rules.

1. A student is assigned to one instructor for a given course.
2. Each instructor teaches exactly one course.

The functional dependencies are:

$$
(student,course)\to instructor
$$

$$
instructor\to course
$$

The candidate keys are \((student,course)\) and \((student,instructor)\). Every attribute is therefore prime, so the 3NF conditions are satisfied.

However, `instructor` alone is not a superkey yet determines `course`, so the relation violates BCNF.

A BCNF decomposition can be:

- instructor_course(instructor, course)
- student_instructor(student, instructor)

This reduces duplication, but the original \((student,course)\to instructor\) constraint may become difficult to check using only local constraints on the individual tables. This is where the tradeoff between BCNF and dependency preservation appears.

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
