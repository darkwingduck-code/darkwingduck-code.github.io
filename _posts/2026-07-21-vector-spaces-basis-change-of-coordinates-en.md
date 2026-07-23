---
title: "From Vector Spaces to Change of Basis: Understanding the Structure of Linear Algebra"
date: 2026-07-21 09:00:00 +0900
categories: [Mathematics, Linear Algebra]
tags: [vector-space, subspace, span, linear-independence, basis, dimension, change-of-basis]
description: "Connect subspaces, spans, linear independence, bases, dimensions, and coordinate transformations through definitions, worked examples, and practical validation procedures."
math: true
lang: en
translation_key: vector-spaces-basis-change-of-coordinates
hidden: true
---

{% include language-switcher.html %}

Much of the confusion in linear algebra begins not with calculation methods but with **mixing concepts at different levels**. A vector space is the setting in which operations are valid, while a subspace is a smaller setting closed under those operations. A span is the range that can be made from given vectors, linear independence means there is no redundancy in a representation, and a basis is a coordinate system that satisfies both properties.

The goal of this article is not to memorize terms separately, but to answer the following questions consistently.

- Is a given set really a subspace?
- What space do a set of vectors span?
- How do we remove redundancy from a spanning set?
- When can a vector form a basis?
- When the basis changes, how do the vector itself and its coordinates change?

## 1. Vector spaces: Sets in which linear combinations remain safely contained

A vector space \(V\) over a field \(\mathbb F\) is a set equipped with vector addition and scalar multiplication. In practice, the scalars are usually drawn from \(\mathbb R\) or \(\mathbb C\). We do not check every axiom, such as associativity, commutativity, and distributivity, each time, but their essence can be condensed into the following statement.

> For \(u,v\in V\) and \(a,b\in\mathbb F\), every linear combination \(au+bv\) must also belong to \(V\).

Vectors are not limited to sequences of numbers. Polynomials, matrices, functions, and signals are also vectors when their addition and scalar multiplication satisfy the axioms. The essence of linear algebra is therefore not the geometry of arrows but a **structure that preserves linear combinations**.

## 2. Subspaces: A one-line test stronger than three separate conditions

For \(W\subseteq V\) to be a subspace, it must satisfy the following conditions.

1. The zero vector belongs to \(W\).
2. It is closed under addition.
3. It is closed under scalar multiplication.

Combining these into a single test gives the following.

$$
u,v\in W,\quad a,b\in\mathbb F
\quad\Longrightarrow\quad
au+bv\in W.
$$

Also verify \(W\neq\varnothing\) so that the empty set does not pass incorrectly.

### Homogeneous constraints create subspaces; nonhomogeneous constraints generally do not

For a matrix \(A\),

$$
W=\{x\mid Ax=0\}
$$

is always a subspace. If \(Au=0\) and \(Av=0\), then

$$
A(au+bv)=aAu+bAv=0
$$

because of linearity. This is why a null space is a subspace.

In contrast,

$$
S=\{x\mid Ax=c\},\qquad c\neq 0
$$

generally does not contain the zero vector and is therefore not a subspace. If solutions exist, \(S\) is an **affine set** obtained by translating the null space. A line or plane that does not pass through the origin is a representative example.

## 3. Span: Everything that can be made from the given materials

The span of vectors \(v_1,\dots,v_k\) is the set of all their linear combinations.

$$
\operatorname{span}(v_1,\dots,v_k)
=
\left\{
\sum_{i=1}^{k}a_i v_i
\;\middle|\;
a_i\in\mathbb F
\right\}.
$$

The span is the **smallest subspace** containing every one of \(v_1,\dots,v_k\). Adding more spanning vectors does not necessarily increase the dimension. If a new vector is already in the existing span, only the representation becomes redundant; the space remains unchanged.

Constructing the matrix

$$
A=[v_1\;v_2\;\cdots\;v_k]
$$

makes \(\operatorname{span}(v_1,\dots,v_k)\) the column space of \(A\). Whether a vector \(y\) belongs to this span can be determined by whether \(Ac=y\) has a solution.

## 4. Linear independence: Uniqueness of the representation of the zero vector

The vector set \(\{v_1,\dots,v_k\}\) is linearly independent when

$$
a_1v_1+\cdots+a_kv_k=0
$$

has only the solution \(a_1=\cdots=a_k=0\). If nonzero coefficients can produce the zero vector, the set is linearly dependent.

From the matrix perspective, all of the following statements are equivalent.

- \(v_1,\dots,v_k\) are linearly independent.
- The only solution of \(Ac=0\) is \(c=0\).
- The number of pivot columns in \(A\) is \(k\).
- \(\operatorname{rank}(A)=k\).
- The nullity is 0.

### A frequently incorrect statement: “A basis vector only needs to be nonzero”

For a single vector \(v\), if \(v\neq0\), then \(\{v\}\) is a basis of the one-dimensional subspace \(\operatorname{span}(v)\) that it creates. It is not, however, a basis of an arbitrary larger subspace. To be a basis, vectors must not only be **linearly independent** but also **span** the entire target space.

## 5. Basis and dimension: A minimal spanning set and a maximal independent set

A basis \(B=(b_1,\dots,b_n)\) of a subspace \(W\) satisfies both of the following conditions.

1. \(\operatorname{span}(b_1,\dots,b_n)=W\)
2. \(b_1,\dots,b_n\) are linearly independent.

This allows a basis to be understood in two ways.

- A **minimal spanning set** that no longer spans the entire space if any vector is removed
- A **maximal independent set** that becomes dependent if one more vector is added

Every basis of a finite-dimensional space has the same number of vectors. That number is the dimension \(\dim W\). For a matrix \(A\in\mathbb F^{m\times n}\),

$$
\operatorname{rank}(A)+\operatorname{nullity}(A)=n
$$

holds. This means the \(n\) input degrees of freedom decompose into observable column-space directions and null-space directions that \(A\) erases.

## 6. Worked example: Finding a plane's basis in two ways

Consider the following homogeneous plane.

$$
W=\{(x,y,z)^\mathsf T\in\mathbb R^3\mid x+y+z=0\}.
$$

Because the constraint gives \(x=-y-z\),

$$
\begin{bmatrix}x\\y\\z\end{bmatrix}
=
y\begin{bmatrix}-1\\1\\0\end{bmatrix}
+
z\begin{bmatrix}-1\\0\\1\end{bmatrix}.
$$

A candidate basis is therefore

$$
B=
\left(
\begin{bmatrix}-1\\1\\0\end{bmatrix},
\begin{bmatrix}-1\\0\\1\end{bmatrix}
\right)
$$

The two vectors are not scalar multiples of each other, so they are independent, and they span every solution. Therefore \(\dim W=2\).

We can reach the same conclusion through rank-nullity. The constraint matrix \(A=[1\;1\;1]\) has rank 1, so its nullity is \(3-1=2\). Checking that different approaches give the same dimension is a useful verification technique.

## 7. Distinguish coordinates from the vector itself

If the coordinates of a vector \(v\) in the basis \(B=(b_1,\dots,b_n)\) are written as

$$
[v]_B=
\begin{bmatrix}c_1\\\vdots\\c_n\end{bmatrix}
$$

then

$$
v=c_1b_1+\cdots+c_nb_n
$$

Here, \(v\) is an abstract object, while \([v]_B\) is a numerical representation that depends on the chosen basis.

Below, assume that two bases of an \(n\)-dimensional space are expressed in a single fixed \(n\)-dimensional reference coordinate system, so their basis matrices are square and invertible. If the matrix whose columns are the basis vectors is also denoted by \(B\), then

$$
v=B[v]_B,\qquad [v]_B=B^{-1}v
$$

holds. If \(B\) and \(C\) are two bases of the same space, then

$$
[v]_C=C^{-1}B[v]_B.
$$

Thus, the matrix that converts \(B\)-coordinates to \(C\)-coordinates is

$$
P_{C\leftarrow B}=C^{-1}B
$$

Reading the subscript arrow as “from the input basis to the output basis” helps prevent errors in multiplication order.

When a subspace basis is written directly in the coordinates of a larger ambient space, the basis matrix may be rectangular and \(B^{-1}\) does not exist. In this case, solve \(B[v]_B=v\) with QR or a similar method, or first choose a fixed reference basis inside the subspace and express it as a square coordinate matrix.

### The matrix of a linear transformation also depends on the basis

If \(A\) is the standard-basis matrix of a linear transformation \(T:V\to V\), and \(B\) is the new basis matrix, then

$$
[T]_B=B^{-1}AB.
$$

The sequence sends a vector from the new coordinates to standard coordinates, applies \(A\), and returns it to the new coordinates. Because \(A\) and \(B^{-1}AB\) express the same linear transformation in different coordinate systems, they share similarity invariants such as trace, determinant, and eigenvalues.

## 8. Practical problem-solving workflow

### When a set is given

1. Specify the ambient space and scalar field.
2. Check first whether it contains the zero vector.
3. For arbitrary \(u,v\) and scalars \(a,b\), verify that \(au+bv\) preserves the defining condition.
4. If there is a nonhomogeneous constant term, an inequality, or a fixed-norm condition, first investigate the likelihood that it is not a subspace.

### When spanning vectors are given

1. Construct a matrix with the vectors as columns.
2. Find the pivot columns by row reduction.
3. Select the pivot columns of the **original matrix** as a basis of the column space.
4. Compare the rank with the number of basis vectors.

The columns of a row-reduced matrix may have a different column space from the original. Row operations preserve the row space, but generally do not preserve the column space itself.

### When a coordinate transformation is given

1. Specify the coordinate system in which each basis vector is written.
2. Match the column order of the basis matrix with the order of coordinate components.
3. Calculate \(P_{C\leftarrow B}=C^{-1}B\).
4. Verify that \(CP_{C\leftarrow B}=B\).
5. For an arbitrary test vector, check that \(B[v]_B=C[v]_C\).

## 9. Validation checklist

- [ ] Did you call a set that does not contain the zero vector a subspace?
- [ ] Did you distinguish a span from the set itself?
- [ ] Did you check “spans” and “is independent” separately?
- [ ] Does the number of basis vectors equal the known dimension?
- [ ] Does the sum of rank and nullity equal the number of columns?
- [ ] Did you select pivot columns from the original matrix?
- [ ] Did you label the input and output basis direction of the coordinate transformation?
- [ ] Is the actual vector reconstructed unchanged after the transformation?
- [ ] Did you record the rank-detection tolerance for numerical calculations?

## 10. Pitfalls and limitations

### Trying to decide everything with one determinant

The determinant is defined only for square matrices. For independence, span, and rank questions involving rectangular matrices, row reduction, QR, and SVD are more general.

### Numerical rank is not an exact integer

With floating-point data, you decide whether a singular value is “sufficiently small” rather than whether it is exactly zero. Because changing the threshold can change the estimated rank, report the scale and tolerance together.

### Assuming that a basis is unique

Dimension is fixed, but there are infinitely many bases. A good basis depends on the purpose. An orthonormal basis stabilizes calculations, an eigenbasis simplifies operations, and a sparse basis can make interpretation and storage easier.

### Overextending finite-dimensional intuition

In infinite-dimensional spaces such as function spaces, an algebraic basis is distinguished from an analytic basis involving convergence. Once infinite sums, norms, and completeness appear, finite-matrix intuition alone is insufficient.

## Conclusion

The essential flow is simple.

$$
\text{Subspace}
\longrightarrow
\text{span}
\longrightarrow
\text{linear independence}
\longrightarrow
\text{basis}
\longrightarrow
\text{dimension and coordinates}
$$

A basis is not simply a “list of direction vectors.” It is an **interface that represents every element of a space without redundancy**. Once you adopt this viewpoint, projection, least squares, SVD, and dimensionality reduction connect through the same language.
