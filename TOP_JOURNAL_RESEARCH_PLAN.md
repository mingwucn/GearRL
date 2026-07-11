# Top-Journal Research Plan for GearRL

## Objective

Transform GearRL from a prototype into a reproducible, manufacturing-aware design-synthesis system for compound spur gear trains in constrained enclosures.

The publication target is *Advanced Engineering Informatics* (AEI). This is a fully digital engineering-informatics study with certified synthesis, in-house CAE screening, and reproducible evidence; it does not claim physical manufacturing validation.

The research claim is:

> A manufacturing-aware certified synthesis graph generates valid compound spur-gear layouts under explicit geometric, kinematic, component, and CAE-derived strength constraints, and learning-guided search reduces design time on unseen enclosure families without weakening validity.

## Scope and Claim Boundaries

The first research version is limited to:

- External involute spur gears on parallel shafts.
- Fixed 20-degree pressure angle and module selected from a declared standard series.
- Simple gears and two-stage compound gears only.
- Signed angular-velocity ratio as the primary functional target.
- Ideal torque ratio derived separately under an explicit efficiency assumption.
- Geometric validity: intended meshes, no unintended gear/shaft/housing intersections, minimum clearance, tooth-count and undercut rules, and valid axial stacking.
- Backlash robustness is limited to the standard small-displacement relation between declared transverse backlash and positive center-distance expansion; it is not a tooth-contact simulation.
- CAE validity: conservative static tooth-root stress safety factor under declared torque, material, face width, and load-distribution assumptions.

The system must use the phrase "valid under the declared kinematic, geometric, and static-strength model." It must not claim full manufacturability, operational reliability, or dynamic drivetrain validation without additional evidence.

## Work Packages

### 1. Literature and Venue Gate

Review recent work in AEI, gear-train synthesis, constrained optimization, learning-guided search, and gear-strength analysis. Build a comparison matrix covering topology class, kinematic model, engineering knowledge representation, solver, learning role, CAD/CAE validation, benchmark, and reproducibility artifacts.

Freeze the proposed contribution only after establishing a defensible gap against the closest methods. The AEI paper path requires explicit engineering knowledge representation, a certified digital workflow, a benchmark, independent validation, and CAE screening.

### 2. Canonical Design and Validation Model

Replace duplicated data models with one typed, unit-aware specification containing:

- `DesignProblem`: enclosure, obstacles, shafts, target signed speed ratio, component constraints, and load case.
- `GearTrain`: shafts, simple or compound gear stages, mesh graph, and axial stack.
- `ValidationCertificate`: geometric, kinematic, component, and CAE checks with margins.
- `MaterialLoadCase`: material, torque, face width, allowable stress, efficiency assumption, and safety factor target.
- `CAEReport`: mesh provenance, solver configuration, stress/displacement fields, convergence information, and safety factor.
- `ManufacturingArtifact`: CAD/DXF/STEP export, process parameters, and export-validation result.

Implement a directed mesh graph. Every mesh edge must identify driving and driven gear members, center-distance equation, direction reversal, and ratio contribution. Use a separate reference verifier instead of reusing in-loop validation code.

Build at least 50 hand-constructed known-valid and known-invalid cases before optimization work begins. Cover simple trains, compound trains, ratio parity, infeasible shaft placement, boundary contact, non-adjacent collisions, invalid axial stacking, and tooth-limit violations. The generator, in-loop validator, and reference verifier must agree on every case.

### Object-Oriented Architecture Requirement

Use object-oriented design for all production code. Do not add procedural pipelines or free-function business logic outside narrowly scoped numerical kernels.

- Model engineering concepts as cohesive domain objects: design problems, gear stages, mesh graphs, constraint sets, load cases, certificates, benchmarks, and manufacturing artifacts.
- Define interfaces or abstract base classes for validators, solvers, CAE analyses, exporters, benchmark generators, policies, and experiment stores; inject implementations through constructors.
- Keep each object responsible for one bounded concern and expose typed inputs/outputs. Separate domain rules from persistence, rendering, command-line entry points, and numerical back ends.
- Implement the deterministic solver, learned branch-ordering policy, in-loop validator, reference verifier, and CAE solver as replaceable strategy objects so that evaluations can compare them without changing domain code.
- Use factories only to create domain objects from validated specifications; retain immutable problem/configuration objects during an experiment run.
- Unit-test object contracts and use integration tests only to verify composed workflows.

### 3. Self-Developed CAE System

Develop the CAE module in `conda env ai`. The project owns the finite-element formulation, assembly, boundary conditions, sparse solve, post-processing, and safety-factor evaluation. Use `gmsh` only for mesh generation and `meshio` only for mesh interchange.

Required environment dependencies:

- NumPy and SciPy for numerical assembly and sparse solution.
- Gmsh and MeshIO for finite-element mesh generation and interchange.
- PyVista and VTK for inspection and report visualization.
- PyTorch for the learned search policy.
- Pydantic and test tooling for typed schemas and validation.

Implement a two-dimensional, linear-elastic, plane-stress triangular-element solver for the worst-loaded involute tooth. Generate involute gear geometry from module, tooth count, pressure angle, addendum, and dedendum. Convert declared input torque into tangential and radial tooth loads using the specified load convention and face width.

CAE verification requirements:

- Element patch tests.
- Cantilever-beam analytical benchmark.
- Mesh-convergence study.
- Comparison with a separately implemented analytical gear-root stress estimate.
- Preregistered agreement check before CAE results are used as optimization constraints.

Treat CAE as conservative screening, not as complete contact or fatigue validation.

### 4. Benchmark and Baselines

Freeze a 400-instance benchmark:

- 250 procedural instances across four enclosure families and three difficulty strata.
- 50 verifier-backed tight-clearance feasible instances and 100 near-infeasible instances with explicit infeasibility certificates.
- An optional, separately labelled external extension partition when valid cases and provenance become available; never simulate or fabricate this evidence.

Every instance must include generator seed, canonical problem JSON, reference-verifier version, feasibility label, and a feasibility certificate or proof of infeasibility. Keep generator families disjoint across train, validation, and test partitions.

Implement and evaluate deterministic methods before learning:

- Exact or branch-and-bound search on bounded instances.
- CP-SAT or equivalent constrained search.
- Evolutionary optimization.
- The route-first heuristic from the original system.

Freeze hardware, wall-clock budget, tuning budget, random seeds, and stopping criteria before final testing.

### 5. Manufacturing-Aware Certified Synthesis Graph

Implement the central method as a manufacturing-aware certified synthesis graph:

- Nodes represent feasible partial shaft and gear states.
- Edges represent exact simple-mesh and compound-stage transitions.
- Edge admission is controlled by the independent geometric and kinematic predicate.
- Terminal admission requires the CAE safety-factor threshold and manufacturing-export feasibility.

Use complete deterministic branch-and-bound search as the baseline solver and as the fallback contribution. Add learning only as a graph-policy branch-ordering heuristic. Train from deterministic-solver traces, then refine with PPO. The learned policy may rank only feasible graph transitions and may never generate an unconstrained invalid action.

### 6. Evaluation Protocol

The primary endpoint is the independently verified valid-design rate within a fixed compute budget.

Secondary metrics are:

- Signed-ratio error.
- Minimum clearance margin.
- CAE safety factor.
- Gear count and envelope area.
- Standard-component compliance.
- Solver time.
- Manufacturing-export success.

Run stochastic methods for 30 independent seeds. Analyze paired per-instance outcomes using bootstrap confidence intervals, effect sizes, and corrected multiple comparisons.

Learning is retained only if it preserves 100% modeled validity and improves either:

- Median search time by at least 30%, or
- Valid-within-budget rate by at least 10 percentage points,

with a 95% confidence interval excluding no improvement.

Run CAE on a preregistered stratified sample of 120 successful layouts. Report every failure, safety margin, and model limitation. Evaluate robustness under shaft-position tolerance, housing tolerance, backlash allowance, and load variation.

## Digital Manufacturing Workflow

Export every accepted design as canonical JSON, SVG/DXF, and parametric CAD geometry. Generate STEP only after automated CAD interference checks pass. Include material, module, tooth count, face width, load case, CAE report, and validation certificate in the process-planning record.

Do not use placeholder metrics, demonstrations, or untraceable legacy outputs as scientific evidence.

## Reproducibility Requirements

Create an `environment-ai.yml`, lockfile, container recipe, and one-command clean-environment reproduction target. Store every experiment as an immutable bundle with:

- UUID, Git commit, and dirty-state hash.
- Dependency and container hash.
- Hardware details, random seed, full configuration, and dataset hash.
- Model checkpoint, raw trajectory, per-instance result, and reference-verifier/CAE certificate.

Generate paper figures and tables only from immutable experiment bundles. Quarantine existing demo and placeholder experiment artifacts. Require CI coverage for schema compatibility, unit/property tests, reference-verifier agreement, CAE patch/convergence tests, benchmark generation, baseline smoke runs, training/evaluation smoke runs, and paper-figure regeneration.

## Milestones

| Phase | Target | Exit Criterion |
| --- | --- | --- |
| Literature and venue | Weeks 1-4 | AEI contribution gap and digital evidence path documented |
| Correctness | Weeks 5-12 | Generator, validator, and reference verifier agree on 50 curated cases |
| CAE | Weeks 8-20 | Patch, analytical, and convergence verification complete |
| Benchmark and baselines | Weeks 13-24 | Frozen 400-instance benchmark and deterministic comparison suite |
| Certified synthesis graph | Weeks 22-34 | Deterministic solver and constrained learned branch ordering complete |
| Evaluation and submission | Weeks 34-48 | Preregistered results, artifact release, and venue decision completed |

## Submission Acceptance Criteria

Submit only when all of the following are true:

1. All reported outputs pass the independent verifier under the declared model.
2. The benchmark, source code, configurations, checkpoints, and result bundles reproduce the paper tables from a clean environment.
3. The proposed method has a statistically supported benefit over predeclared baselines, or the deterministic solver itself provides the paper's contribution.
4. CAE evidence is reported with model limits and convergence results.
5. The manuscript claims only the declared digital kinematic, geometric, and static-strength model; physical validation is future work.
