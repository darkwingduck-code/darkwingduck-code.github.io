---
title: "V&V for Trustworthy Numerical Results: Convergence, Mesh and Time-Step Independence, and Conservation"
date: 2026-07-21 09:20:00 +0900
categories: [Scientific Computing, Verification and Validation]
tags: [verification, validation, convergence, mesh-independence, time-step, conservation, numerical-error]
description: A practical procedure for distinguishing code verification, solution verification, and experimental validation, then assessing the reliability of numerical results through convergence, mesh and time-step independence, and conservation.
math: true
lang: en
translation_key: numerical-verification-validation-convergence
hidden: true
---

{% include language-switcher.html %}

A plausible contour and a smooth curve are not evidence of accuracy. For a numerical simulation to be trustworthy, at least the following questions must be considered separately.

- Is the code solving the equations correctly?
- Are the discretization and iterative errors in this calculation sufficiently small?
- Do the chosen equations and inputs adequately explain the quantities of interest in reality?
- Is this conclusion valid within the intended use and allowable error?

If these questions are bundled together under the single word “verification,” it becomes impossible to know what has been checked and what remains. This is why verification and validation are distinguished.

## 1. The Boundary Between Verification and Validation

| Level | Core question | Typical evidence |
|---|---|---|
| code verification | Were the equations implemented as intended? | exact solution, manufactured solution, benchmark, unit test |
| solution verification | How large is the numerical error in the current calculation? | iterative convergence, mesh/time-step refinement, error estimate |
| validation | Does the model reproduce real-world quantities of interest adequately for its purpose? | comparison with independent measurements, validation uncertainty, applicability |
| calibration | Were unknown parameters estimated from data? | objective/likelihood, posterior, identifiability |

In brief, verification is close to asking “are we solving the equations right?” while validation asks “are we solving the right equations?” Validation, however, does not prove that a model is absolutely true. It accumulates **evidence for a specific intended use, range of conditions, and quantity of interest**.

Using the same data for calibration and validation amounts to asking the model to fit data it has already seen. Separate them where possible; if limited data requires reuse, explicitly state that the result is not an independent validation.

## 2. Decompose the Error First

The difference between a computational result and reality combines several causes.

$$
\text{total discrepancy}
=
\text{model-form error}
+\text{parameter/input uncertainty}
+\text{discretization error}
+\text{iterative error}
+\text{implementation error}
+\text{measurement error}.
$$

This equation is not a rigorous probabilistic model in which each term is simply additive and independent; it is a conceptual decomposition intended to prevent causes from being overlooked. The causes may interact with one another and may not be completely separable from observations alone.

A good V&V plan defines the quantity of interest (QoI) first. Rather than referring to the entire field, state which average, maximum, integral, arrival time, or boundary flux will be used in decision-making. Mesh convergence and validation results can differ by QoI.

## 3. Code Verification: The Stage for Finding Implementation Errors

### Exact Solutions and Benchmarks

When an analytic solution exists for simplified boundary conditions or geometry, computational error can be compared directly. Even if it differs from a complex production case, it is valuable for isolating and testing the implementation of operators, boundary conditions, and source terms.

### Method of Manufactured Solutions

First choose a desired smooth function \(u_m(x,t)\), then substitute it into the governing equation's operator \(\mathcal L\) to construct the source

$$
f_m=\mathcal L(u_m)
$$

If the code is configured to solve

$$
\mathcal L(u)=f_m
$$

the known answer \(u_m\) can be used to test the interior operator, boundary conditions, time integration, and observed order together.

A manufactured solution need not represent a real phenomenon. It should instead satisfy the following conditions.

- It activates all major terms in the code path.
- It does not mask bugs through excessive symmetry.
- It has the required differentiability.
- Its boundary conditions and source are derived consistently.

### Independent Implementations and Limiting Cases

Different codes producing the same answer is useful evidence, but they may share common assumptions or common bugs. Combine this result with other types of evidence, such as limits in which a term approaches zero, symmetry, dimensional analysis, and conservation laws.

## 4. Solution Verification: Numerical Error in the Current Calculation

### Separate Iterative Error from Discretization Error

Changing the mesh before a nonlinear or linear solver has converged sufficiently mixes iterative error with discretization error. On each mesh, make the residual tolerance sufficiently smaller than the discretization difference, and check the stability of the QoI as well as the residual.

A decrease in algebraic residual does not necessarily guarantee a decrease in solution error. In a badly conditioned system, a small residual and a large solution error can coexist.

### The Asymptotic Convergence Range

If the mesh spacing is \(h\) and the theoretical order is \(p\), then in a sufficiently fine range one expects

$$
\phi(h)=\phi_0+Ch^p+\mathcal O(h^{p+1})
$$

where \(\phi\) is one QoI. When the refinement ratio is constant and

$$
h_3=rh_2=r^2h_1,\qquad r>1
$$

with \(h_1\) the finest spacing, the observed order can be estimated as

$$
p_{\mathrm{obs}}
=
\frac{
\ln\left|
(\phi_3-\phi_2)/(\phi_2-\phi_1)
\right|
}{
\ln r
}
$$

If the sequence is in the asymptotic range and converges monotonically, Richardson extrapolation gives

$$
\phi_{\mathrm{ext}}
=
\phi_1+
\frac{\phi_1-\phi_2}{r^{p_{\mathrm{obs}}}-1}
$$

This formula becomes unstable if the three values converge oscillationally or if their differences are at the noise level. Rather than unconditionally reporting a single apparent order, first report the convergence pattern and whether the assumptions are satisfied.

## 5. Why the Phrase “Mesh Independent” Requires Caution

Discretization error is rarely exactly zero on a finite mesh. It is therefore better to report the following specifics instead of merely claiming “independence.”

- The refinement family and characteristic \(h\) used
- Refinement ratio
- Cell/DOF scale of each mesh
- Mesh quality and boundary-layer resolution
- Values and relative changes for each QoI
- Observed order or error estimate
- Acceptance criterion used to select the final mesh

The mere fact that values from two meshes are similar is insufficient. There may be accidental error cancellation, non-monotonic convergence, or the same resolution bottleneck. Where possible, use at least three levels and verify that the meshes form a systematic refinement family sharing a topology and stretching rule.

### Local and Integral Quantities Converge Differently

A domain average or integral flux may be stable while a point maximum, gradient, or discontinuity location converges slowly. Conduct the mesh study separately for every QoI to be reported. If the “maximum location” moves between meshes, do not directly compare the values at the same cell index.

## 6. Time-Step Independence and the Coupling of Spatial and Temporal Errors

A refinement study can also be performed for time step \(\Delta t\) in the form

$$
\phi(\Delta t)=\phi_0+C_t(\Delta t)^q+\cdots
$$

However, if the spatial error is large, reducing the time step may produce no visible change, and the converse is also true.

A practical sequence is as follows.

1. Evaluate spatial refinement using a sufficiently small \(\Delta t\).
2. Evaluate \(\Delta t\) refinement on the selected fine mesh.
3. Around the final combination, vary the mesh and \(\Delta t\) together to check their interaction.
4. With adaptive time stepping, record tolerances, accepted-step history, and rejected steps rather than a single nominal step.

Satisfying a stability condition is different from achieving sufficient accuracy. The fact that an implicit method does not diverge at a large time step does not mean that it has accurately resolved the transient phase and peak time.

## 7. Conservation: Strong Evidence Independent of a Convergence Plot

For a control volume \(\Omega\) in a conservative problem, a general balance is

$$
\frac{d}{dt}\int_{\Omega}U\,d\Omega
+
\int_{\partial\Omega}F\cdot n\,dS
=
\int_{\Omega}S\,d\Omega
$$

For a discrete calculation over a fixed time interval, compute

$$
\Delta \text{storage}
+\text{net outflow}
-\text{source}
=
\text{balance defect}
$$

Reporting only the absolute defect makes cases of different scales difficult to compare. Also examine a normalized balance error divided by a representative flux or storage change. If the denominator is near zero, however, relative error explodes, so present the absolute value and scale together.

Conservation is a necessary condition, not a sufficient one. Global conservation may still hold when the same total is distributed incorrectly among different locations. Therefore, distinguish the following levels.

- Local cell balance
- Per-boundary flux balance
- Global domain balance
- Per-species or per-component balance
- Coupled balances such as energy, mass, and momentum

## 8. How to Design Validation Comparisons

### Define Validation Metrics in Advance

Do not look at a plot and judge that it is “similar”; define the QoI and metric first. Examples include:

- Bias and normalized error
- Profile norm
- Peak magnitude and location
- Integral quantity
- Temporal phase error
- Coverage or probabilistic score

### Combine Uncertainties

When interpreting the simulation–measurement difference

$$
E=S-D
$$

consider simulation numerical uncertainty, input uncertainty, and measurement uncertainty together. A small \(|E|\) alone does not prove that the model is correct; also determine whether a very wide uncertainty band is merely obscuring the difference.

### State the Validation Domain

Extrapolation outside the range of validated conditions weakens the evidence. Record the input space, boundary regime, dimensionless groups, and material/state ranges, and assess how far the prediction point lies from the validation domain.

## 9. Recommended V&V Workflow

1. **Define the intended use and allowable error**: State which QoIs will inform which decisions.
2. **Construct the model hierarchy**: Distinguish governing equations, closures, boundary and initial conditions, and parameter sources.
3. **Code verification**: Test the implementation with unit tests, exact solutions or MMS, limiting cases, and benchmarks.
4. **Iterative convergence**: Examine equation residuals and QoI histories together.
5. **Spatial refinement**: Compare at least three levels in a systematic mesh family.
6. **Temporal refinement**: Include temporal QoIs, phase, and peak timing.
7. **Conservation checks**: Automatically compute local, boundary, and global balances.
8. **Propagate input uncertainty**: Reflect input uncertainty in the validation comparison.
9. **Independent validation**: Compare against data not used for calibration with predefined metrics.
10. **Record the applicability range and limitations**: Identify unvalidated regimes and dominant uncertainties.

## 10. Verification Checklist

- [ ] Have verification, validation, and calibration been distinguished?
- [ ] Were the QoIs and tolerances used in decision-making defined first?
- [ ] Does the analytic/MMS test activate the production code's major terms?
- [ ] Is iterative error sufficiently smaller than the differences between meshes?
- [ ] Were at least three levels of systematic refinement used?
- [ ] Was observed order checked in addition to theoretical order?
- [ ] Were monotonic, oscillatory, and divergent convergence distinguished?
- [ ] Were spatial and temporal refinement performed separately?
- [ ] Were local and boundary conservation checked in addition to global conservation?
- [ ] Were calibration and validation data separated?
- [ ] Were measurement, input, and numerical uncertainty reported together?
- [ ] Was extrapolation outside the validation domain identified?

## 11. Common Pitfalls

### Concluding That a Small Residual Means the Answer Is Correct

A residual says only how well the discrete algebraic equations have been solved; it reveals neither discretization error nor model-form error.

### Comparing Only Two Meshes and Declaring Independence

Accidental agreement between two values does not establish a convergence order or an asymptotic range. At least three levels and the convergence pattern are needed.

### Evaluating Every Field with One Metric

Even if the mean agrees well, the peak, gradient, or phase may be wrong. Multiple QoIs suited to the intended purpose are necessary.

### Reporting Calibration Performance as Validation Performance

Fit to the data used to tune parameters is a calibration result. Independent information is needed to assess predictive adequacy.

### Assuming a Finer Mesh Is Always More Accurate

With incorrect boundary conditions, a loose iterative tolerance, poor mesh quality, or an unstable scheme, increasing the DOF alone does not guarantee accuracy.

## 12. Limitations and Reporting Principles

In complex nonlinear and multiscale problems, it may be impossible to reach a clean asymptotic range. Discontinuities, moving interfaces, chaotic dynamics, and adaptive meshes weaken the assumptions of simple Richardson analysis. In such cases, instead of forcing a single “exact error” estimate, report transparently how stable the conclusion is across multiple resolutions, which error source dominates, and what could not be verified.

The product of V&V is not a pass stamp. It is **a network of evidence supporting a conclusion**. This is why solver tolerances, refinement families, balance defects, uncertainties, and applicability ranges matter more than plots.
