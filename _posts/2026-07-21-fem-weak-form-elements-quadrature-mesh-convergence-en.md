---
title: "The Backbone of the Finite Element Method: Weak Forms, Elements, Quadrature, and Mesh Convergence"
date: 2026-07-21 12:43:00 +0900
categories: [Scientific Computing, Finite Element Method]
tags: [fem, weak-form, galerkin, finite-element, quadrature, mesh-convergence]
description: "Connect the core structure of FEM, from deriving the weak form from the strong form through function spaces, boundary conditions, element interpolation, quadrature, assembly, linear solvers, and mesh convergence."
math: true
mermaid: true
lang: en
translation_key: fem-weak-form-elements-quadrature-mesh-convergence
hidden: true
---

{% include language-switcher.html %}

The finite element method (FEM) is more than a technique for dividing a geometry into small pieces.
It transforms a differential equation into an integrable weak form and projects a problem in an infinite-dimensional function space onto a finite-dimensional subspace.
Once this perspective is clear, element types and solver options connect through a single mathematical structure.

## 1. Start from the strong form

Consider the Poisson problem.

$$
-\nabla\cdot(k\nabla u)=f \quad \text{in }\Omega,
$$

$$
u=g_D \quad \text{on }\Gamma_D,
\qquad
-k\nabla u\cdot n=g_N \quad \text{on }\Gamma_N.
$$

The strong form requires (u) to be sufficiently differentiable point by point and to satisfy the equation and boundary conditions point by point.
For complex coefficients, discontinuous materials, and nonsmooth domains, this requirement can be too strong.

## 2. Test functions and integration by parts

Multiply by a test function (v) that is zero on the Dirichlet boundary and integrate.

$$
\int_\Omega -v\nabla\cdot(k\nabla u)\,d\Omega
=\int_\Omega vf\,d\Omega.
$$

Applying integration by parts, or Green's identity, gives

$$
\int_\Omega k\nabla v\cdot\nabla u\,d\Omega
-\int_{\partial\Omega}v k\nabla u\cdot n\,d\Gamma
=\int_\Omega vf\,d\Omega.
$$

Substituting the Neumann condition yields the weak form

$$
a(u,v)=\ell(v)
$$

with

$$
a(u,v)=\int_\Omega k\nabla v\cdot\nabla u\,d\Omega,
$$

$$
\ell(v)=\int_\Omega vf\,d\Omega+\int_{\Gamma_N}vg_N\,d\Gamma
$$

The derivative order of (u) has fallen from second to first, and the natural boundary condition has entered as a boundary integral.

## 3. Essential and natural boundary conditions

- A Dirichlet condition restricts the trial space itself, so it is called an essential condition.
- A Neumann condition appears naturally on the right-hand side of the weak form, so it is called a natural condition.

This distinction matters in implementation as well.
When eliminating Dirichlet degrees of freedom from the matrix or handling them as constraints, preserve symmetry and the calculation of reactions.

A pure Neumann problem has a null space because every solution shifted by a constant is also possible.
It requires the compatibility condition

$$
\int_\Omega f\,d\Omega+\int_{\Gamma_N}g_N\,d\Gamma=0
$$

and a mean-value constraint or reference.

## 4. The meaning of function spaces

The natural space for the Poisson problem is the Sobolev space (H^1(\Omega)).

$$
H^1(\Omega)=
\{v\in L^2(\Omega):\nabla v\in[L^2(\Omega)]^d\}.
$$

In other words, the function and its first weak derivative need only be square-integrable.
The central requirement is an integrable energy norm, not pointwise smoothness.

Galerkin FEM uses the same finite-dimensional subspace for the trial and test spaces.

$$
V_h=\mathrm{span}\{N_1,\ldots,N_n\}.
$$

## 5. Element interpolation and degrees of freedom

Represent the approximate solution as

$$
u_h(\mathbf x)=\sum_{j=1}^{n}N_j(\mathbf x)U_j
$$

Each (N_j) is a shape function, and each (U_j) is a nodal value or generalized degree of freedom.

Using each basis function (N_i) as a test function gives

$$
K_{ij}=\int_\Omega k\nabla N_i\cdot\nabla N_j\,d\Omega,
\qquad
F_i=\ell(N_i)
$$

and the global system becomes

$$
\mathbf K\mathbf U=\mathbf F
$$

## 6. The reference element and mapping

Map the physical element (Omega_e) from the reference element (hat\Omega).

$$
\mathbf x(\boldsymbol\xi)=
\sum_a N_a(\boldsymbol\xi)\mathbf x_a.
$$

The Jacobian is

$$
J=\frac{\partial\mathbf x}{\partial\boldsymbol\xi}
$$

and transforms both the gradient and the volume element.

$$
\nabla_x N=J^{-T}\nabla_\xi N,
\qquad
d\Omega=|\det J|d\hat\Omega.
$$

An element with (det J\le0) is inverted or degenerate.
A small determinant and a large condition number degrade gradient calculations and stiffness conditioning.

## 7. Quadrature is part of the model

Approximate the element integral by quadrature.

$$
\int_{\hat\Omega}g(\xi)d\xi
\approx
\sum_{q=1}^{n_q}w_q g(\xi_q).
$$

If the integration order is too low, stiffness and internal forces may not be constructed accurately, producing hourglass or zero-energy modes.
Conversely, excessive quadrature may only increase cost without resolving locking.

### Reduced integration and selective integration

Reduced integration can mitigate locking, but it carries the risk of spurious modes.
Check that stabilization does not contaminate physical energy.

### Nonlinear materials and quadrature points

Internal state variables are usually updated at quadrature points.
Using a consistent tangent can greatly improve Newton convergence.
Consistency among state updates, rollbacks, and load-step retries is important.

## 8. Assembly is a local-to-global conservation convention

Add each element matrix (mathbf K^e) and vector (mathbf F^e) to the global system using the degree-of-freedom mapping.

```mermaid
flowchart LR
  A[reference element] --> B[geometry mapping]
  B --> C[quadrature point evaluation]
  C --> D[element matrix/vector]
  D --> E[local-to-global assembly]
  E --> F[constraints and boundary terms]
  F --> G[linear/nonlinear solve]
  G --> H[error and balance checks]
```

The degrees of freedom at a shared node combine contributions from adjacent elements.
For edge or face elements with signs and orientations, align the local orientation with the global convention.

## 9. Conformity, stability, and locking

Simply raising the polynomial order does not solve every problem.

- **Conformity**: Does the approximation space satisfy the required continuity?
- **Coercivity/inf-sup stability**: Is the discrete problem stable?
- **Locking**: Does the formulation become excessively stiff for thin structures or nearly incompressible conditions?
- **Spurious mode**: Is there a mode that deforms without physical energy?

In mixed problems, the combination of displacement and pressure spaces must satisfy the inf-sup condition.
Using equal-order interpolation unconditionally can produce pressure oscillations.

## 10. h-, p-, and hp-refinement

- h-refinement: Reduce element size.
- p-refinement: Increase the basis order.
- hp-refinement: Combine the two according to smoothness.

Under sufficient regularity, a typical energy-norm error has the form

$$
\|u-u_h\|_{H^1}\le C h^p|u|_{H^{p+1}}
$$

At corner singularities, discontinuous coefficients, or contact, low regularity may prevent the nominal order from appearing.

## 11. A priori and a posteriori error

An a priori estimate explains the convergence rate using solution regularity and mesh size.
An a posteriori estimator uses residuals and jumps from the computed solution to decide where to refine.

A conceptual residual estimator combines the element residual (R_e) and inter-element flux jump (J_f), as in

$$
\eta^2=\sum_e h_e^2\|R_e\|^2
+\sum_f h_f\|J_f\|^2
$$

Use benchmarks to verify that the effectivity index is stable over the problem family.

## 12. Nonlinear problems and Newton's method

If the residual vector is (mathbf R(\mathbf U)=0), the Newton step is

$$
\mathbf J(\mathbf U^k)\Delta\mathbf U
=-\mathbf R(\mathbf U^k),
$$

$$
\mathbf U^{k+1}=\mathbf U^k+\alpha\Delta\mathbf U
$$

A consistent Jacobian, line search, load or time increment control, and state rollback determine robustness.

## 13. Recommended workflow

1. Specify the strong form, domain, and boundary partition.
2. Multiply by a test function and derive the weak form by hand through integration by parts.
3. Define the trial and test spaces and essential constraints.
4. Verify the reference element, mapping, and shape functions.
5. Match quadrature order to the integrand and nonlinearity.
6. Perform an element-level patch test and a manufactured-solution test.
7. Check global balance, reactions, and energy.
8. Perform systematic refinement at three or more levels.
9. Report convergence and error estimators for each QoI.

## 14. Verification checklist

- [ ] The sign of the weak form's boundary term was re-derived.
- [ ] Essential and natural boundary conditions were distinguished.
- [ ] The pure Neumann null space and compatibility were handled.
- [ ] The direction of the reference-to-physical Jacobian is consistent.
- [ ] Every element determinant is positive and sufficiently large.
- [ ] Rigid-body modes and the expected null space were checked.
- [ ] The patch test and constant-state test passed.
- [ ] Sensitivity to quadrature order was evaluated.
- [ ] The sum of reactions and external forces balances.
- [ ] Strain energy and work are consistent.
- [ ] Observed order was calculated under h- or p-refinement.
- [ ] A point-singularity value is not reported as though it were a converged QoI.

## 15. Common failure patterns and limitations

### Only making the mesh finer

Adding distorted elements or applying only uniform refinement at a singularity provides little benefit for the cost.

### Assuming a smooth contour is accurate

Postprocessing with nodal averaging can make discontinuous stress look smooth.
Check the original quadrature-point values and equilibrium.

### Using reduced integration as a universal remedy

It can reduce locking but introduce hourglass modes.
Examine stabilization energy and mesh sensitivity together.

### Confusing solver tolerance with discretization error

Mesh error can remain large even when the linear residual is small.
Conversely, comparing mesh refinement while algebraic error is large contaminates the observed order.

### Comparing only the maximum stress at a particular point

Point stress can diverge at a re-entrant corner or concentrated load.
Choose a well-defined QoI such as an integral, average, or fracture parameter.

## 16. Official and primary references

- Galerkin, B. G., “Series Solution of Some Problems of Elastic Equilibrium,” 1915.
- Courant, R., “Variational Methods for the Solution of Problems of Equilibrium and Vibrations,” 1943.
- Ciarlet, P. G., *The Finite Element Method for Elliptic Problems*.
- NIST, [OOF finite-element analysis documentation](https://www.ctcms.nist.gov/oof/oof2/).
- PETSc, [Finite element and discretization interfaces](https://petsc.org/release/manual/dmplex/).
- The FEniCS Project, [Official documentation](https://docs.fenicsproject.org/).

The heart of FEM is not the shape of its elements, but **whether the weak form, function spaces, quadrature, assembly, and error estimation form one consistent approximation problem**.
