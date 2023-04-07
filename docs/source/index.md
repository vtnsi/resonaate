---
orphan: true
---

% This file isn't included in TOC, so set it as "orphan"

(main-index-intro)=

# RESONAATE Documentation

Welcome to the RESONAATE (Responsive Space Observation Analysis & Autonomous Tasking Engine) documentation!

(index-main-fig-catalog)=

```{figure} _static/catalog.png
---
align: right
scale: 50 %
alt: Satellite Catalog Growth
---
Plot of satellite catalog growth over time.
```

With the expected resident space object (RSO) population growth and improvements of satellite propulsion capabilities, it has become increasingly apparent that maintaining space domain awareness (SDA) in future decades will require using human-on-the-loop autonomy as opposed to the current human-in-the-loop methods.

RESONAATE provides a stable, configurable API for advance algorithms related to SDA research, especially big-data oriented problems.
The main library API is written in Python to make it easy to use, distribute, extend, and to reduce the amount of programming knowledge required to perform SDA research.

Alongside the library, a command line interface (CLI) tool ({command}`resonaate`) is provided to easily start & configure large-scale SDA simulations.
This interface combines many settings and algorithm to perform truth simulation of sensor and target dynamics, incorporating dynamic state estimation of targets, and autonomously tasking sensors to track the estimated targets.
More specific details on how the CLI works can be seen in {mod}`.cli` and details on the JSON configuration format can be seen in {ref}`ref-cfg-top`.

Here are some of the features that RESONAATE has to offer:

- {class}`.EstimateAgent`, {class}`.SensingAgent`, and {class}`.TargetAgent` classes for agent-based simulation
- High-fidelity, configurable orbit propagation using Cowell's method
- {class}`.UnscentedKalmanFilter` for tracking RSOs
- Multiple {class}`.Sensor` types to take measurements of targets
- Corresponding database model for long-term-storage of simulated data
- Configurable and extendible {class}`.ScenarioConfig` class for changing simulation options
- Parallelization across multiple cores and machines
- Dynamic event system that can perform various spacecraft maneuvers and more
- Several {class}`.ManeuverDetection` techniques
- Adaptive estimation after detected maneuvers either in the form of initial orbit determination (IOD) or multiple model adaptive estimation (MMAE)

An overview of the motivation, design, framework, and terminology is provided below in {ref}`main-index-abstract`.
The sidebar on the left has more pages organized into targeted sets of information.
See {ref}`main-index-site` for a description of these sections.

View the [source code](https://code.vt.edu/space-research/resonaate/resonaate) and [issue tracker](https://code.vt.edu/space-research/resonaate/resonaate/-/issues) hosted on GitLab.

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

(main-index-abstract)=

## Abstract

% Include initial bit of README

(index-main-fig-ssn)=

```{figure} _static/ssn.jpg
---
align: right
scale: 40 %
alt: Space Surveillance Network
---
The U.S. Space Surveillance Network (SSN)
```

The RESONAATE simulation creates a decision-making engine that can create a tasking strategy for a diversely populated space object surveillance and identification (SOSI) network.
The figure on the right ({numref}`index-main-fig-ssn`) shows a visual representation of the United States Space Surveillance Network (SSN).
RESONAATE often uses a version of this model, but also provides the flexibility to construct an arbitrary SSN with different sensors.
The RESONAATE simulation tracks multiple maneuvering and non-maneuvering RSO using the given SSN, and attempts to do so in a responsive, autonomous, and optimal way.

RESONAATE models the RSO tracking (or sensor management) problem as a sub-optimal partially observable Markov decision process (POMDP) which defines actions as which RSO to task various ground and space-based sensors to track at a given time.
A representation of the POMDP model is shown below ({numref}`index-main-fig-pomdp`).
The POMDP algorithm implements multiple types of metrics to measure the value of tasking opportunities.
Examples of these include sensor usage metrics, information theoretic metrics, stability metrics, and behavioral metrics.
The successful measurements from the tasked sensors are combined using an unscented Kalman filter (UKF) to maintain viable orbit estimates for all targets.
This process is repeated over sequential time steps for the entire simulation length.
The filter for each target RSO can include maneuver detection techniques for unplanned maneuvers.
If a maneuver is detected, the simulation has the ability to dynamically switch to an adaptive estimation technique which can include triggering IOD or initializing an MMAE filter until post-maneuver convergence.

The RESONAATE simulation stores both truth and estimated state information into a SQL database which allows for comparisons of various algorithms across different portions of the RSO tracking problem (e.g. tasking, estimation, or fusion) by directly measuring the global performance.
It is also easy to perform Monte Carlo studies to determine algorithm sensitivity, or parametric studies to determine trade-offs for tunable algorithm parameters.

(index-main-fig-pomdp)=

```{figure} _static/pomdp.jpg
---
align: center
scale: 60 %
alt: Partially Observable Markov Decision Process block diagram
---
Block diagram of RESONAATE's Partially Observable Markov Decision Process (POMDP) model
```

______________________________________________________________________

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% The TOC trees are hidden so they only appear on the sidebar

(main-index-site)=

## Site Contents

{ref}`main-index-started` goes over basic information on how to install, setup, and use the RESONAATE tool and library.
This section is the main jumping off point for new users or anyone trying to get a general understanding of the RESONAATE use cases.

{ref}`main-index-ref` details specific information on how RESONAATE works such as the JSON config format and the library API documentation.
This section targets users and developers alike for quickly and efficiently finding out more information on how to use various features of RESONAATE.

{ref}`main-index-tech` is meant for in-depth description of the mathematics, physics, and software engineering that RESONAATE is built upon.
The idea is that the bulk of equations, references, derivations, and assumptions can be kept here, so that code documentation strings can remain manageable.

{ref}`main-index-dev` provides detailed descriptions about key processes, RESONAATE distribution & integration, as well as design philosophies.
The material here is meant specifically for RESONAATE software developers to reference for how to better work with the RESONAATE team.

{ref}`main-index-meta` holds extra details about the RESONAATE software package that while being important, are not directly applicable to understanding RESONAATE itself.
These pages serve as a way to document software history, references, licensing, and other "metadata" about the tool/library.

% Getting Started Section

(main-index-started)=

```{toctree}
---
maxdepth: 1
caption: Getting Started
name: home_started_toc
includehidden:
---
intro/install
intro/quickstart
gen/examples/index

```

% User Guide TOC

(main-index-tech)=

```{toctree}
---
maxdepth: 1
caption: User Guide
name: home_background_toc
includehidden:
---
background/astro
background/estimation
background/noise
background/tasking
```

% Reference Material TOC

(main-index-ref)=

```{toctree}
---
maxdepth: 1
caption: Reference Material
name: home_ref_toc
includehidden:
hidden:
---
reference/config_format
reference/api

```

% Developer Info TOC

(main-index-dev)=

```{toctree}
---
maxdepth: 1
caption: For Developers
name: home_dev_toc
includehidden:
---
Getting Started <development/contrib>
Workflow <development/workflow>
Style Guide <development/style>
Testing <development/test>
Documentation <development/docs>
Labels <development/labels>
Releases <development/releases>
CI/CD <development/ci>
Docker <development/containers>
```

% Meta Information TOC

(main-index-meta)=

```{toctree}
---
maxdepth: 1
caption: Meta Information
name: home_meta_toc
includehidden:
---
Bibliography <meta/bibliography>
Changelog <meta/changelog>
License <meta/license>
```

______________________________________________________________________

(main-index-pub)=

## Publications

For additional information on the development of the RESONAATE Tool, see the following publications:

- "Dynamically Tracking Maneuvering Spacecraft with a Globally-Distributed, Heterogeneous Wireless Sensor Network"
  - {cite:t}`nastasi_2017_space_dst`
- "An Autonomous Sensor Management Strategy for Monitoring a Dynamic Space Domain with Diverse Sensors"
  - {cite:t}`nastasi_2018_scitech_dst`
- "Autonomous Multi-Phenomenology Space Domain Sensor Tasking and Adaptive Estimation"
  - {cite:t}`thomas_2018_ieee_fusion`
- "Adaptively Tracking Maneuvering Spacecraft with a Globally Distributed, Diversely Populated Surveillance Network"
  - {cite:t}`nastasi_2019_aiaa_jgcd`
- "Autonomous and Responsive Surveillance Network Management for Adaptive Space Situational Awareness"
  - {cite:t}`nastasi_2018_diss`
- "Parametric Analysis of an Autonomous Sensor Tasking Engine for Spacecraft Tracking"
  - {cite:t}`kadan_2021_scitech_parametric`

______________________________________________________________________

(main-index-auth)=

## Authors

- Project Principal Investigators
  - Dr. Jonathan Black: <jonathan.black@vt.edu>
  - Dr. Kevin Schroeder: <kschro1@vt.edu>
- Core Developers
  - Dylan Thomas: <dylan.thomas@vt.edu>
  - David Kusterer: <kdavid13@vt.edu>
  - Jon Kadan: <jkadan@vt.edu>
  - Cameron Harris: <camerondh@vt.edu>
- Contributors
  - Connor Segal: <csegal@vt.edu>
  - Amit Bala: <agbala@vt.edu>
  - Dylan Penn: <dylanrpenn@vt.edu>
