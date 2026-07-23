---
title: "Using Least Squares Correctly: Projection, Conditioning, QR, and SVD"
date: 2026-07-21 09:10:00 +0900
categories: [Mathematics, Numerical Linear Algebra]
tags: [least-squares, projection, conditioning, qr, svd, pseudoinverse, regularization]
description: "Interpret least squares as an orthogonal projection problem and connect condition numbers, QR, SVD, pseudoinverses, and regularization from the perspective of numerical stability."
math: true
lang: en
translation_key: least-squares-projection-conditioning-svd
hidden: true
---

{% include language-switcher.html %}

When the observation equation \(Ax=b\) cannot be solved exactly, we are often taught to “multiply both sides by \(A^\mathsf T\).” But the essence of least squares is not memorizing a formula; it lies in three questions.

1. What are we minimizing?
2. Why is the solution connected to orthogonal projection onto the column space?
3. Which algorithm will compute the same mathematical solution stably?

This article organizes the geometry of least squares, the danger of normal equations, the roles of QR and SVD, rank deficiency, and regularization into one coherent progression.

## 1. Defining the least-squares problem

For \(A\in\mathbb R^{m\times n}\) and \(b\in\mathbb R^m\), the overdetermined system \(Ax=b\) generally has no exact solution. Least squares minimizes the Euclidean norm of the residual

$$
r(x)=b-Ax
$$

as follows.

$$
x_\star
=
\arg\min_x \|Ax-b\|_2^2.
$$

\(Ax\) always lies in \(\mathcal C(A)\), the column space of \(A\). The problem is therefore to find the column-space element \(\hat b=Ax_\star\) closest to \(b\).

## 2. Orthogonal projection and the normal equations

At the closest point, the residual \(r_\star=b-Ax_\star\) is orthogonal to every direction in the column space.

$$
A^\mathsf T r_\star=0.
$$

Expanding this expression gives the normal equations.

$$
A^\mathsf T A x_\star=A^\mathsf T b.
$$

If \(A\) has full column rank, \(A^\mathsf T A\) is positive definite and the solution is unique.

$$
x_\star=(A^\mathsf T A)^{-1}A^\mathsf T b.
$$

This equation, however, is a **mathematical expression**, not a recommended computational procedure. In real code, it is generally best to avoid both explicitly constructing an inverse and unconditionally solving the normal equations when accuracy matters.

The projection matrix is

$$
P=A(A^\mathsf T A)^{-1}A^\mathsf T
$$

and \(\hat b=Pb\). With full column rank, \(P\) satisfies

$$
P^\mathsf T=P,\qquad P^2=P
$$

Symmetry means the projection is orthogonal, while idempotence means that projecting an already projected value leaves it unchanged.

## 3. A simple regression example

Suppose we fit a linear model \(y\approx\beta_0+\beta_1t\) to several points. The design matrix is

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

The least-squares solution does not minimize the **perpendicular distance** between the data points and the line. It minimizes the sum of squared residuals in the specified \(y\) direction. If both axes contain errors, orthogonal distance regression or an errors-in-variables model may be more appropriate.

Moreover, if the absolute values of \(t\) are very large or its range is concentrated on one side, distinguishing the intercept column from the slope column numerically can become difficult. Centering and appropriately scaling \(t\) improves both the condition number and coefficient interpretation.

## 4. Condition numbers: How much input error is amplified in the solution

The 2-norm condition number of an invertible square matrix is

$$
\kappa_2(A)
=
\|A\|_2\|A^{-1}\|_2
=
\frac{\sigma_{\max}}{\sigma_{\min}}
$$

For a rectangular full-column-rank matrix, the ratio of the largest singular value to the smallest nonzero singular value has the same meaning.

A large condition number causes the following phenomena.

- Small errors in the input \(b\) are greatly amplified in \(x\).
- Nearly identical columns make coefficients fluctuate sharply.
- Parameter estimates may be unstable even when the residual is small.
- Floating-point rounding errors have a greater effect.

The normal equations have a decisive problem.

$$
\kappa_2(A^\mathsf T A)=\kappa_2(A)^2.
$$

An already poor condition number is squared. Forming \(A^\mathsf T A\) can also lose significant digits.

> A small residual and accurate parameters are not the same thing. Even if \(b\) is close to the column space, nearly dependent columns can allow very different coefficients to produce similar predictions.

## 5. Solving least squares with QR

Suppose \(A\) has full column rank and

$$
A=QR,
$$

where the columns of \(Q\in\mathbb R^{m\times n}\) are orthonormal and \(R\in\mathbb R^{n\times n}\) is upper triangular. Then

$$
\|Ax-b\|_2^2
=
\|Rx-Q^\mathsf Tb\|_2^2
+\|(I-QQ^\mathsf T)b\|_2^2.
$$

Because the second term is independent of \(x\), we can solve

$$
Rx=Q^\mathsf T b
$$

by back substitution.

In practice, Householder QR is generally more stable than classical Gram–Schmidt. If rank is in doubt, use column-pivoted QR

$$
AP=QR
$$

to bring important columns forward and diagnose effective rank.

## 6. SVD and the pseudoinverse

SVD decomposes a matrix as

$$
A=U\Sigma V^\mathsf T
$$

The columns of \(U\) and \(V\) are orthonormal, and the diagonal entries \(\sigma_i\) of \(\Sigma\) are the singular values.

The Moore–Penrose pseudoinverse is

$$
A^+=V\Sigma^+U^\mathsf T
$$

and the minimum-norm solution among all least-squares solutions is

$$
x_\star=A^+b
=
\sum_{\sigma_i>0}
\frac{u_i^\mathsf Tb}{\sigma_i}v_i
$$

This equation directly reveals the source of ill-conditioning. In directions with small \(\sigma_i\), even small noise in \(u_i^\mathsf Tb\) is amplified by \(1/\sigma_i\).

### When SVD is especially useful

- When rank deficiency exists or is suspected
- When you want to inspect the null space and identifiable directions
- When you need a minimum-norm solution
- When diagnosing conditioning from the singular spectrum
- When applying regularization such as truncated SVD

SVD offers the greatest diagnostic power, but it can cost more computation and memory than QR. Choose according to problem size, sparsity, and required accuracy.

## 7. Rank deficiency and non-unique solutions

If \(\operatorname{rank}(A)<n\), distinct values of \(x\) can produce the same \(Ax\). For \(z\in\mathcal N(A)\),

$$
A(x+z)=Ax
$$

so if \(x\) is a least-squares solution, \(x+z\) has the same residual. The pseudoinverse solution selects the one with the smallest \(\|x\|_2\).

Rank is not binary in numerical data. Given a singular-value cutoff \(\tau\), one may discard directions satisfying

$$
\sigma_i\le\tau
$$

but \(\tau\) is not a mere implementation detail. It is a modeling choice about which directions to regard as unidentifiable and should reflect scale, noise level, and purpose.

## 8. Weighted least squares and covariance

If residual components have different variances or are correlated, ordinary least squares' equal-weight assumption is inappropriate. If the error covariance is \(\Sigma_b\), then

$$
x_\star
=
\arg\min_x
(Ax-b)^\mathsf T\Sigma_b^{-1}(Ax-b).
$$

Using a whitening matrix satisfying \(W^\mathsf TW=\Sigma_b^{-1}\) transforms the problem into

$$
\min_x\|W(Ax-b)\|_2^2
$$

Here, weights should not be arbitrary scores chosen for convenience; they should be connected to the probability structure of the residuals.

## 9. Regularization is an additional assumption, not a numerical trick

Tikhonov regularization can be written as

$$
x_\lambda
=
\arg\min_x
\left(
\|Ax-b\|_2^2
+\lambda^2\|L(x-x_0)\|_2^2
\right)
$$

- \(x_0\): Prior or reference solution
- \(L\): Structure to penalize
- \(\lambda\): Balance between data fit and prior

With \(L=I\) and \(x_0=0\), this becomes the ridge form. Regularization reduces variance at the cost of introducing bias. It should therefore be treated as a modeling step that states which solutions are more plausible, not as “adding an arbitrary small value because the condition number is bad.”

\(\lambda\) can be selected with cross-validation, the discrepancy principle, an L-curve, generalized cross-validation, and other methods. Whichever method you use, record the selection criterion and the independence of the evaluation data.

## 10. Algorithm selection guide

| Situation | First choice to consider | Reason |
|---|---|---|
| Dense, full rank, ordinary conditioning | Householder QR | Balances stability and cost |
| Rank unclear, diagnosis important | SVD | Reveals the singular spectrum and null space |
| Need to determine column rank | Pivoted QR or SVD | Estimates effective rank |
| Very large sparse problem | Iterative least-squares solver | Avoids matrix-factorization cost |
| Covariance structure present | Whitened/weighted least squares | Reflects the error model |
| Ill-posed inverse problem | Regularized solver | Suppresses unstable directions |
| Speed is paramount and conditioning is good | Carefully consider Cholesky on the normal equations | Fast, but risks squaring the condition number |

The default should be a function that solves the linear system directly rather than “compute the inverse and multiply.” Library functions such as `solve`, `lstsq`, and sparse solvers take advantage of internal factorizations and exception handling.

## 11. Practical workflow

1. **Define the objective**: Is prediction important, or is parameter interpretation important?
2. **Check dimensions and units**: Write down the shapes and physical units of \(A\), \(x\), and \(b\).
3. **Scale**: Inspect column norms, variable ranges, and units; center and standardize if needed.
4. **Diagnose rank**: Inspect QR pivots or the singular spectrum.
5. **Choose a solver**: Use QR by default; consider SVD for rank and ill-conditioning diagnostics.
6. **Analyze residuals**: Examine structure, bias, heteroscedasticity, and correlation, not just one norm.
7. **Verify orthogonality**: Check whether \(A^\mathsf Tr\) is zero within tolerance.
8. **Check sensitivity**: Perturb the input within its admissible range and observe how much coefficients and predictions change.
9. **Report uncertainty**: Compute parameter uncertainty when the noise model and covariance assumptions are valid.
10. **Record reproducibility details**: Preserve the solver, tolerance, scaling, rank cutoff, and regularization-selection method.

## 12. Verification checklist

- [ ] Are the minimized norm and weights specified?
- [ ] Does \(Ax_\star\) lie in the column space, and is \(A^\mathsf Tr\approx0\)?
- [ ] If full rank was assumed, was it actually verified?
- [ ] Was an inverse of \(A^\mathsf TA\) avoided?
- [ ] Were condition numbers before and after column scaling compared?
- [ ] Were singular values and the cutoff recorded together?
- [ ] Were residual magnitude and parameter stability evaluated separately?
- [ ] Was overfitting the regularization parameter to evaluation data avoided?
- [ ] Do the weights in weighted least squares match the error model?
- [ ] Were prediction intervals kept distinct from parameter confidence intervals?

## 13. Pitfalls and limitations

### Mistaking a high \(R^2\) for a well-solved problem

High explanatory power does not guarantee residual independence, model adequacy, or parameter identifiability. It is especially dangerous in extrapolation.

### Changing input units and directly comparing coefficient magnitudes

Coefficient magnitude depends on variable scale. Align units and scaling before comparing importance.

### Believing that the pseudoinverse recovers the “true solution”

The pseudoinverse merely selects a representative solution according to a clear optimization criterion; it cannot restore null-space information lost from the data.

### Hiding model-structure errors with regularization

Regularization mitigates ill-posedness, but it does not fix omitted variables, an incorrect observation operator, or systematic bias.

### Limits of linearized least squares

A nonlinear model \(f(x)\) requires local linearization and iterative optimization. Initial values, local minima, and Jacobian conditioning become additional concerns.

## Conclusion

Least squares is not merely a “formula that reduces the sum of squared errors”; it is a **projection problem onto a subspace**. QR is the fundamental tool for computing that projection stably, while SVD is the diagnostic tool that exposes rank and unstable directions. The condition number asks whether the computation is trustworthy, and regularization explicitly states what assumptions were added in place of missing information.

Least squares becomes a reproducible analysis when you preserve residual orthogonality, the singular spectrum, scaling, solver, and tolerance alongside the final numbers.
