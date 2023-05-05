(tech-noise-top)=

# Process Noise Models

Note that most of the equations and language in this section is derived from {cite:t}`bar-shalom_2001_estimation, crassidis_2012_optest`.

______________________________________________________________________

<!-- TOC formatted for sphinx -->

```{contents} Table of Contents
---
depth: 2
backlinks: none
local:
---
```

______________________________________________________________________

## Kinematic Process Noise Models

We typically define process noise for a Kalman filter as additive, zero-mean white noise such that our process (dynamics) model is

```{math}
x(k+1) &= f\left[k, x(k), u(k)\right] + v(k) \\
x&\in\mathbb{R}^n \\
```

where $f[\cdot]$ defines a possibly nonlinear function, $k$ is the discrete time step, $x(k)\in \mathcal{R}^n$ is the state vector, $u(k)$ is the **known** (typically  zero in our usage) control input, and $v(k)$ is the process noise.
The additive, zero-mean, and white noise properties are defined as follows:

```{math}
E\left[ v(k) \right] = 0
```

```{math}
E\left[ v(k)v(j)^T \right] = Q(k)\delta_{kj}
```

where $Q(k)$ is covariance of the discrete time process noise.
In general, the process noise covariance is time-varying (such that the noise is a non-stationary sequence), but we typically choose

```{math}
Q(k) = Q, \,\, \forall k
```

This means that we design a constant process noise covariance up front.

Difficulty arises in how to design $Q$ for a particular dynamics (process) model.
If the system is kinematic, as is the case in astrodynamics, we can define the process noise itself as a kinematic system.
This allows $Q$ to be defined via quantities derived from physics.
Process noise can be modeled as an $n\mathrm{th}$ order kinematic model where the $n\mathrm{th}$ derivative of position is equal to white noise.
This can be done in two primary ways:

- discretize a continuous time model
- direct definition of the process noise in discrete time

(tech-noise-cont)=

### Continuous Time Process Noise

The process noise can be modeled as a continuous white noise acceleration such that

```{math}
\ddot{x}(t) = \tilde{v}(t), \quad x\in\mathbb{R}
```

where

```{math}
E\left[\tilde{v}(t) \right] = 0
```

```{math}
E\left[ \tilde{v}(t)\tilde{v}(\tau) \right] = \tilde{q}(t)\delta(t-\tau)
```

When time-invariant $\tilde{q}$ is the power spectral density of the continuous time process noise.
Using this model, we can discretize the model, assuming $\tilde{q}$ is constant, resulting in

```{math}
Q(k) = Q = \begin{bmatrix}
    \frac{1}{3}T^3 & \frac{1}{2}T^2 \\[6pt]
    \frac{1}{2}T^2 & T \\
\end{bmatrix} \tilde{q}, \quad \forall k
```

where $T$ is the discrete time step and $Q(k)=Q$ is the discrete time process noise covariance.

When the intensity, $\tilde{q}$, is small this process model becomes a *nearly constant velocity* model.
Also, the following relation can be used as a tuning guideline for $\tilde{q}$

```{math}
\sqrt{Q_{22}} = \sqrt{\tilde{q}\,T}
```

where $\sqrt{Q_{22}}$ is the order of changes in velocity over a time step.
This results in $\tilde{q}$ being defined in terms of the approximate *un-modeled* acceleration

```{math}
\tilde{q} \simeq \tilde{a}^2 T
```

where $\tilde{a}$ is the approximate *un-modeled* accelerations in the process model.
Note that $\tilde{q}$ has units of $[\mathrm{km}]^2/[\mathrm{s}]^3$ and $T$ has units of $[\mathrm{s}]$.
Finally, this model is defined only for a single kinematic coordinate, so the multidimensional process noise covariance is block diagonal with the above defined $Q$ as the independent blocks.

(tech-noise-disc)=

### Discrete Time Process Noise

We can also directly define a kinematic model in discrete time in which the process noise $v(k)$ is a scalar-valued zero-mean white sequence

```{math}
E\left[ v(k) \right] = 0
```

```{math}
E\left[ v(k)v(j) \right] = \sigma^2\delta_{kj}
```

and enters the dynamics equation via

```{math}
x(k+1) = f\left[k, x(k), u(k)\right] + \Gamma v(k)
```

where $\Gamma$ is the noise gain vector and $v(k)$ is a zero-mean white sequence.
This model assumes that the object undergoes a constant acceleration during each time step (of length $T$)

```{math}
\tilde{v}(t) = v(k), \quad t\in\left[k T, (k+1) T\right]
```

which are uncorrelated in time.
This defines a discrete piecewise constant acceleration process noise model

The second order case gives the following noise gain vector

```{math}
\Gamma = \begin{bmatrix}
    \frac{1}{2}T^2 \\[6pt]
    T \\
\end{bmatrix}
```

Then, one can directly determine the process noise covariance

```{math}
Q(k) = \Gamma \sigma^2\Gamma^T = \begin{bmatrix}
        \frac{1}{4}T^4 & \frac{1}{2}T^3 \\[6pt]
        \frac{1}{2}T^3 & T^2 \\
    \end{bmatrix} \sigma^2
```

where $\sigma^2$ is the discrete time process noise variance.

When the intensity, $q \simeq \sigma T$, is small this process model becomes a *nearly constant velocity* model.
Also, the following relation can be used as a tuning guideline for $\sigma$

```{math}
\frac{1}{2} \tilde{a} \leq \sigma \leq \tilde{a}
```

where $\tilde{a}$ is the maximum *un-modeled* acceleration magnitude over a time step.
Note that $\sigma$ has units of $[\mathrm{km}]/[\mathrm{s}]^2$.
Finally, this model is defined only for a single kinematic coordinate, so the multidimensional process noise covariance is block diagonal with the above defined $Q$ as the independent blocks.

(tech-noise-simple)=

### Simplified Process Noise

Finally, one can define a simplified form of the process noise covariance

```{math}
Q(k) = \begin{bmatrix}
    0 & 0 \\[6pt]
    0 & q \\
\end{bmatrix}
```

using the fact the the off diagonal terms and first order variances are small.
However, one needs to be careful that this doesn't lead to their filter becoming "smug".

(tech-noise-est)=

## Initial Estimate Noise

The initial estimated state vector, $\hat{x}$, is sampled according to the
following random variable

```{math}
\begin{split}
    \hat{x} &\sim \mathcal{N}\left(\vec{x}; [\mathbb{I}_{3}\sigma_p, \mathbb{I}_{3}\sigma_v]\right) \\
    \hat{x} &\in\mathbb{R}^6 \\
\end{split}
```

where $\sigma_{p}$ and $\sigma_{v}$ are the position and velocity standard deviations, respectively,
and $\vec{x}$ is the true state vector. The initial error covariance is then simply a block
diagonal of $\mathbb{I}_{3}\sigma_{p}$ and $\mathbb{I}_{3}\sigma_{v}$.
