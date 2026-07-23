---
title: "From DOE to UQ and Calibration: A Complete Map for Simulation Study Design"
date: 2026-07-21 09:30:00 +0900
categories: [Scientific Computing, Research Methods]
tags: [doe, sensitivity-analysis, uncertainty-quantification, calibration, identifiability, surrogate-model]
description: "Distinguish design of experiments, local and global sensitivity, uncertainty propagation, and parameter calibration, then connect them in one reproducible simulation-study workflow."
math: true
lang: en
translation_key: doe-sensitivity-uq-calibration
hidden: true
---

{% include language-switcher.html %}

Changing a few simulation inputs and comparing output curves is not enough to support strong conclusions. Variable effects, interactions, input uncertainty, parameter estimation, and model error become entangled.

To separate them, first distinguish the roles of four tools.

- **Design of Experiments (DOE)**: decides which input combinations to compute or measure.
- **Sensitivity analysis (SA)**: asks how much of the output variation is explained by each input.
- **Uncertainty Quantification (UQ)**: asks how uncertainty in inputs and models propagates into output uncertainty.
- **Calibration**: uses observations to estimate unknown parameters.

They complement one another, but they are not substitutes. Good DOE does not automatically quantify uncertainty, and a good calibration fit does not mean validation is complete.

## 1. The first table to build: classifying inputs and uncertainty

Do not treat every input \(x=(x_1,\dots,x_d)\) as the same kind.

| Class | Meaning | Typical treatment |
|---|---|---|
| controllable factor | The designer selects its levels | factorial, optimal design |
| scenario/context variable | Has a range of interest but is not controlled directly | blocking, stratification |
| aleatory variable | Modeled as inherent variation | probability distribution and forward propagation |
| epistemic parameter | Uncertain because of insufficient knowledge | calibration, interval/prior update |
| nuisance parameter | Not itself of interest but affects results | marginalization, profiling |
| model discrepancy | Where the equation structure differs from reality | separate discrepancy model or bias budget |

Even the same physical quantity can be classified differently depending on the objective. More important than its name is deciding in advance **which information will be used to update it and how**.

Every input needs at least the following metadata:

- definition and units
- allowed range and its justification
- distribution or design levels
- correlations and constraints among inputs
- whether it is fixed or estimated
- whether it is measurable
- where it enters the model

## 2. DOE: turning an execution budget into information

### Limitations of one-factor-at-a-time

OFAT, which changes one variable at a time, is easy to understand but misses interactions. For example,

$$
y=\beta_0+\beta_1x_1+\beta_2x_2+\beta_{12}x_1x_2
$$

when \(\beta_{12}\) is large, the effect of \(x_1\) changes with the level of \(x_2\). OFAT around a single reference point makes this structure difficult to identify.

### Design types and objectives

| Design | Advantage | Caution |
|---|---|---|
| full factorial | Systematically estimates main effects and interactions | Run count explodes as dimension grows |
| fractional factorial | Screens with fewer runs | The alias structure must be interpreted |
| central composite / Box–Behnken | Efficient for a quadratic response surface | Vulnerable to extrapolation outside the specified region |
| Latin hypercube | Evenly stratifies each axis | Check projection quality and correlation |
| low-discrepancy sequence | Well suited to integration and global SA | Distinguish it from independent random replicates |
| D-/I-optimal design | Optimized for the objective of a particular regression model | Efficiency falls if the assumed model is wrong |
| adaptive/sequential design | Concentrates the budget in uncertain or important regions | Manage the stopping rule and selection bias |

DOE does not mean only “filling the space evenly.” A good design depends on whether the objective is screening, surrogate training, optimization, parameter identification, or validation.

### Randomization, replication, and blocking

- **Randomization** reduces the chance that time drift or order effects are confounded with a particular factor.
- **Replication** estimates variation under identical conditions. For a fully deterministic simulator, simple repetition with the same binary and environment provides no new information, but replication is needed for a stochastic solver or nondeterministic execution.
- **Blocking** separates nuisance variation that is difficult to eliminate, such as equipment, batch, date, or mesh family.

Even in a simulation campaign, run order, compute environment, and solver version can be block or provenance variables.

## 3. Sensitivity analysis: choose the definition of influence first

The “most important variable” changes with the metric.

### Local sensitivity

The derivative around a reference point \(x_0\),

$$
S_i^{\mathrm{local}}
=
\left.
\frac{\partial f}{\partial x_i}
\right|_{x=x_0}
$$

describes the effect of a small perturbation. When units differ, consider a dimensionless index such as

$$
S_i^{\mathrm{scaled}}
=
\frac{x_i}{f}
\frac{\partial f}{\partial x_i}
$$

Local derivatives are efficient for gradient-based optimization and linearized uncertainty, but they can miss nonlinearity, thresholds, interactions, and dependence on the reference point.

### Screening: the Morris family

When elementary effects obtained by moving each input once at several locations are collected, their mean absolute value indicates overall influence, while their variance indicates possible nonlinearity or interactions. This is useful for filtering out unimportant variables in high dimensions, but it is not an exact variance decomposition.

### Global variance-based sensitivity

Assuming independent inputs, output variance can be decomposed in ANOVA form.

$$
\operatorname{Var}(Y)
=
\sum_i V_i
+\sum_{i<j}V_{ij}
+\cdots
$$

The first-order Sobol index and total-effect index can be written as

$$
S_i=\frac{V_i}{\operatorname{Var}(Y)},
\qquad
S_{T_i}
=
1-
\frac{
\operatorname{Var}_{X_{\sim i}}
\left(
\mathbb E[Y\mid X_{\sim i}]
\right)
}{
\operatorname{Var}(Y)
}
$$

\(S_i\) is the effect of \(X_i\) alone, while \(S_{T_i}\) includes every interaction involving \(X_i\). A large \(S_{T_i}-S_i\) signals that interactions are important.

### The trap of correlated inputs

The standard Sobol decomposition assumes independent inputs. If physically feasible input combinations have correlations or constraints, independent sampling can create impossible states. In this case, consider methods that respect the dependency structure, such as conditional sampling, grouped indices, and Shapley effects, and state the joint distribution used.

## 4. UQ: propagating uncertainty into an output distribution

The basic forward-UQ problem is to estimate the distribution, mean, variance, quantiles, and failure probability of \(Y\) in

$$
X\sim p_X(x),\qquad Y=f(X)
$$

### Monte Carlo

Generate independent samples \(x^{(j)}\) and compute \(y^{(j)}=f(x^{(j)})\). This approach is relatively insensitive to dimension and simple to implement, but costly for rare events or expensive simulations. Report the Monte Carlo standard error or confidence interval along with the sample count.

### Surrogate-based UQ

When the original model is expensive, use a response surface, Gaussian process, polynomial chaos, neural surrogate, or similar model. The total error then separates into at least the following terms.

$$
\text{UQ error}
=
\text{sampling error}
+\text{surrogate error}
+\text{input-model error}
+\text{simulation numerical error}.
$$

A small surrogate test error alone does not guarantee accurate tail probabilities or sensitivity indices. Separately examine error in regions important to the UQ objective, especially near boundaries, tails, and constraints.

### Rare events

When the failure probability is small, crude Monte Carlo produces almost no failure samples. Methods such as importance sampling, subset simulation, splitting, or adaptive surrogates may be needed. If the proposal was adjusted arbitrarily after observing outcomes, inspect estimator bias and weight calculations.

## 5. Calibration: estimating parameters as an inverse problem

Given observations \(d\), simulator \(f(\theta,z)\), parameter \(\theta\), and observation conditions \(z\), write

$$
d=f(\theta,z)+\delta(z)+\varepsilon
$$

- \(\delta(z)\): model discrepancy
- \(\varepsilon\): measurement noise

### Optimization perspective

Weighted least squares is expressed as

$$
\hat\theta
=
\arg\min_\theta
(d-f(\theta))^\mathsf T
\Sigma^{-1}
(d-f(\theta))
$$

Bounds, regularization, or a prior penalty may be added.

### Bayesian perspective

$$
p(\theta\mid d)
\propto
p(d\mid\theta)p(\theta)
$$

Here the likelihood represents the measurement and model residual structure, while the prior represents information available before observation. The result is a posterior distribution, not a single point estimate.

Bayesian methods do not automatically provide correct uncertainty when the likelihood or discrepancy model is wrong. A narrow posterior means that information is concentrated under the model assumptions; it does not mean that every error in reality is small.

## 6. Identifiability: optimization success differs from parameter learning

### Structural identifiability

If different parameters produce the same output even under the assumption of zero noise and continuous observations, the parameters are structurally unidentifiable.

### Practical identifiability

Even theoretically identifiable parameters are difficult to distinguish from actual data when observation locations, ranges, noise, or input excitation are inadequate.

The following diagnostics are helpful:

- singular spectrum of the Jacobian or Fisher information
- parameter profile likelihood
- posterior correlation
- optimization from multiple initial values
- synthetic recovery test
- expected information under new observation conditions

When parameters are strongly correlated, individual values may be unstable even though a particular combination or prediction is stable. Distinguish whether the objective is the parameters themselves or prediction.

## 7. Confounding between model discrepancy and parameters

If model-structure error \(\delta(z)\) is ignored, parameters may absorb that error instead. These “effective parameters” fit the calibration conditions well but can lose their physical meaning or predictive power under new conditions.

Conversely, if a highly flexible discrepancy model is allowed, \(\delta\) can explain any mismatch and prevent learning of the parameters. A problem that estimates parameters and discrepancy freely at the same time may be inherently confounded.

Mitigation strategies include:

- include diverse conditions and observation types
- design QoIs sensitive to each parameter
- use physically justified priors and bounds
- constrain the smoothness and structure of the discrepancy
- separate calibration and validation conditions
- report parameter uncertainty and predictive discrepancy separately

## 8. A recommended end-to-end workflow

### Step 1: Define the objective and outputs

Fix the decision, QoI, acceptable error, and input range of interest first. Instead of saying “fit the model well,” state which predictions will be supported and over what range.

### Step 2: Input audit

Build a table of input units, ranges, joint distributions, physical constraints, and information sources. Distinguish epistemic from aleatory uncertainty, but when the boundary is ambiguous, treat multiple interpretations as scenarios.

### Step 3: Screening DOE

When dimension is high, filter out low-impact variables with factorial/fractional designs, Morris methods, derivative screening, or similar tools. Record the screening threshold and any interactions that could be missed.

### Step 4: Space-filling or objective-directed DOE

Choose LHS, a low-discrepancy sequence, or an optimal design according to the objective: surrogate modeling, global SA, or calibration. Exclude physically impossible combinations through constraint-aware sampling.

### Step 5: Numerical quality control

Record each run's convergence, conservation, failure code, and mesh/time-step provenance. Simply deleting solver failures can distort the estimated feasible region, so manage failure itself as an outcome.

### Step 6: Surrogate validation

Use a test design independent of training. Check not only average error but also the worst region, tails, derivatives, and the region in which the calibration posterior will concentrate.

### Step 7: Global SA and forward UQ

State the joint input model and compute the Monte Carlo uncertainty of the sensitivity indices as well. Check whether input-importance rankings are stable with respect to sample size and surrogate choice.

### Step 8: Calibration

Record the likelihood, prior, bounds, discrepancy assumptions, and optimizer/sampler diagnostics. Check identifiability through synthetic recovery and multi-start runs.

### Step 9: Validation

Compare observations with the predictive distribution under conditions and QoIs that were not used. Evaluate out-of-sample prediction rather than calibration residuals.

### Step 10: Sequential update

Select the next run or measurement that will reduce current uncertainty the most. Define the acquisition rule and stopping criterion in advance to prevent endless exploration.

## 9. Verification checklist

- [ ] Are the objectives of DOE, sensitivity, UQ, and calibration kept distinct?
- [ ] Do input ranges and distributions have technical justification?
- [ ] Are correlations and physical constraints reflected in joint sampling?
- [ ] Was OFAT avoided as the sole basis for concluding that no interactions exist?
- [ ] Is replication designed appropriately for deterministic or stochastic behavior?
- [ ] Are the definition and assumptions of the sensitivity metric stated?
- [ ] Is the sampling uncertainty of the sensitivity index itself reported?
- [ ] Is surrogate error included in the UQ results or quantified separately?
- [ ] Has the identifiability of calibration parameters been diagnosed?
- [ ] Was the possibility that model discrepancy is absorbed into parameters examined?
- [ ] Are calibration and validation data separated?
- [ ] Are the random seed, design generator, execution order, and failed runs preserved?

## 10. Common pitfalls and limitations

### The misconception that wider ranges are always more conservative

An unjustifiably broad independent uniform distribution can create combinations that are impossible in reality and artificially change sensitivity rankings. A range should reflect joint feasibility as well as conservatism.

### The misconception that a correlation coefficient captures the entire dependency structure

Linear correlation may fail to describe tail dependence, nonlinear constraints, or multimodality.

### Trusting only the surrogate's average test score

A small global RMSE does not guarantee accuracy around a threshold, in the tails, or in gradients. Validation metrics must match the downstream task.

### Interpreting a parameter posterior as a physical constant

A calibration parameter obtained while ignoring model discrepancy may be a condition-dependent correction value.

### Removing every insensitive variable

A variable is insensitive only for the current output and range; that does not guarantee it is unimportant for another QoI, regime, or tail event.

### Excessive dimension under a small compute budget

Performing high-dimensional global SA and flexible calibration simultaneously with few runs makes the estimators unstable. Screening, structural dimension reduction, and informative measurements should come first.

## Conclusion

A strong simulation study comes not from a large number of runs but from **runs with separated information flows**. DOE determines where to look, sensitivity analysis explains what matters, UQ calculates the breadth of the conclusion, and calibration updates unknown parameters with observations.

Finally, validation asks whether predictions under all these assumptions remain fit for purpose when confronted with new information. Simply separating the questions and data for these four stages greatly reduces overfitting, false precision, and uninterpretable parameters.
