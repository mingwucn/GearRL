# Top-Journal Research Plan for GearRL

> **Status note (2026-07-11):** This document preserves the original plan and historical implementation narrative. Several original strength and robustness conclusions were invalidated by the final AEI review council and must not be cited. The authoritative current scope, evidence, and remaining gates are recorded in `AEI_REMEDIATION_STATUS.md`, `paper/manuscript-v3`, and `paper/submission-readiness-v3`.

## Objective

Transform GearRL from a prototype into a reproducible, manufacturing-aware design-synthesis system for compound spur gear trains in constrained enclosures.

The publication target is *Advanced Engineering Informatics* (AEI). This is a fully digital engineering-informatics study with certified synthesis, in-house CAE screening, and reproducible evidence; it does not claim physical manufacturing validation.

The AEI submission is therefore the primary path. RCIM-style manufacturing claims and physical-validation gates are outside the submitted contribution and remain future work.

The primary research claim is:

> An object-oriented executable engineering-knowledge model centralizes gear-domain semantics and supports requirements-first synthesis of bounded compound spur-gear layouts with independently checkable positive certificates and replayable bounded negative proofs.

Learning is excluded from the primary claim. The existing policy experiments rank paths in constructed reference graphs and do not establish a requirements-first speed or valid-within-budget advantage. Learning may return only after a separately frozen 30-seed requirements-first gate passes; otherwise it remains future work.

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
| Certified synthesis graph | Weeks 22-34 | Deterministic solver complete; learned branch ordering separately gated |
| Evaluation and submission | Weeks 34-48 | Preregistered results, artifact release, and venue decision completed |

## Submission Acceptance Criteria

Submit only when all of the following are true:

1. All reported outputs pass the independent verifier under the declared model.
2. The benchmark, source code, configurations, checkpoints, and result bundles reproduce the paper tables from a clean environment.
3. The proposed method has a statistically supported benefit over predeclared baselines, or the deterministic solver itself provides the paper's contribution.
4. CAE evidence is reported with model limits and convergence results.
5. The manuscript claims only the declared digital kinematic, geometric, and static-strength model; physical validation is future work.

## Implemented sourced load envelope

The frozen `load-envelope-v1` study replaces the illustrative generic-steel load case with a traceable 2 x 2 x 2 x 2 factorial sensitivity experiment. It evaluates two material grades, input torques of 1 and 3 Nm, face widths of 8 and 12 mm, and per-mesh efficiencies of 0.95 and 0.98 on the same 24 family-stratified layouts. The implementation is object-oriented: `TraceableMaterial`, `LoadEnvelopeCase`, `AEIStaticEnvelopeCatalog`, `LoadEnvelopeStudy`, and the evidence store separate source data, experiment construction, analysis, and persistence.

The material inputs are manufacturer data rather than inferred gear allowables:

- ArcelorMittal S355 plate uses the published 355 MPa minimum yield strength for the declared 5-16 mm thickness scope.
- SSAB Toolox 44 plate uses the published 1150 MPa minimum 0.2% proof strength for the declared 6-130 mm thickness scope.
- Both static screening allowables are explicitly derived as minimum yield strength divided by 1.5. This factor is an experiment declaration, not a manufacturer fatigue or gear-rating value.

The frozen result contains 16 envelope cases, 384 layout-case observations, and all underlying tooth reports. Twelve cases pass every sampled layout. At 3 Nm, S355 passes 62.5-83.3% of layouts depending on width and efficiency, whereas all declared Toolox 44 cases pass. The minimum observed static screening safety factor is 0.362. These results demonstrate sensitivity to engineering inputs and identify rejected digital designs; they do not establish fatigue life, contact durability, manufacturing fitness, or physical safety.

Evidence is stored under `data/results/load-envelope-v1`. Its manifest binds the dataset hash, model version, sources, configuration, summary hash, and every case-record hash. `LoadEnvelopeEvidenceStore` rejects modified summaries or records.

### Implemented operating-uncertainty analysis

The frozen `load-uncertainty-v1` study propagates explicitly declared independent uniform operating ranges: 1-3 Nm input torque, 8-12 mm face width, and 0.95-0.98 per-mesh efficiency. Material yield data are not assigned invented probability distributions; S355 and Toolox 44 are analyzed as separate conditions using their sourced minimum strengths.

`ToothResponseSurface` uses the exact force-controlled linear-elastic scaling with torque, face width, and directed mesh-efficiency depth. `DirectCornerValidator` checks this response against all 16 directly solved CAE envelope corners before uncertainty results are admitted. The maximum relative disagreement is below `5e-13`. A scrambled six-dimensional Sobol design provides 8,192 A/B samples per material, and the study reports within-layout first-order and total-order indices. Failure-probability intervals resample the 24 layouts with 5,000 seeded bootstrap replicates; they therefore quantify variation across sampled geometries rather than treating individual Sobol draws as independent physical experiments.

For the declared range, S355 has a pooled modeled-failure probability of 0.110 and a layout-bootstrap 95% interval of `[0.016, 0.223]`; Toolox 44 has no modeled failures in the evaluated sample. Mean total-order indices are 0.888 for torque, 0.123 for face width, and below 0.001 for efficiency. The artifact retains per-layout failure probabilities and safety-factor quantiles under `data/results/load-uncertainty-v1` and cryptographically binds its results to the direct-CAE envelope manifest.

These are conditional digital sensitivity results. The uniform ranges are declared study assumptions, not field-measured duty distributions, and the results do not cover fatigue, contact stress, thermal effects, material variability, or physical qualification.

### Implemented strength-coupled synthesis ablation

The frozen `strength-coupled-v1` study demonstrates that CAE-derived static strength is an admission constraint inside requirements-first synthesis rather than a post-processing label. Ten case IDs are fixed in `StrengthCoupledStudyConfig` and loaded from hash-checked blind solver inputs. Each case is solved first under its original geometric and kinematic requirements, then under the same bounded design space with the S355 plate load case, 1 Nm input torque, 8 mm face width, 0.98 per-mesh efficiency, and a required static screening factor of 2.3.

Seven baseline designs are retained. `valid-down-34` is redesigned from tooth sequence `[18]-[18,20]-[25]`, whose minimum screening factor is 2.259, to `[26]-[25,20]-[26]`, whose factor is 2.336. `valid-low-31` and `valid-three-four-33` become infeasible under the declared coupled model after the complete enumerator eliminates all 6,561 bounded parameter tuples in each case. Thus the strength constraint changes both design selection and modeled feasibility.

`StrengthCouplingRequirements`, `StrengthCoupledSynthesisStudy`, `PredeclaredSolverViewRepository`, and `StrengthCoupledEvidenceStore` separate requirement injection, paired evaluation, frozen-input selection, and persistence. Evidence under `data/results/strength-coupled-v1` contains the baseline-under-strength certificate, accepted strength certificate where present, search accounting, selected trains, source-index hash, and per-record hashes. Rejection is reported only when the bounded search is complete.

This ablation establishes coupling only for the declared static tooth-root model and bounded three-shaft compound family. It does not convert the CAE screen into fatigue, contact, reliability, or physical-validation evidence.

### Implemented publication artifact registry

`PublicationArtifactRegistry` generates six deterministic evidence-only Markdown tables and six vector figures for solver comparison, solver scaling, CAE verification, load uncertainty, strength-coupled synthesis, and confirmatory assembly robustness. Every registry entry records the output hash and the path and hash of every frozen source payload used by its renderer. The figures use an object-oriented `SVGCanvas` backed by `xml.etree.ElementTree`, avoiding nondeterministic or host-specific raster-font behavior. `PublicationReproducer` rebuilds all outputs in a clean temporary directory and requires byte identity with `paper/generated-v1`; modified tables, figures, or source evidence fail verification.

The class-based `AEIPublicationTableFactory` and `AEIPublicationFigureFactory` declare the submitted reporting set. `make paper-verify` provides a one-command reporting reproduction target, and CI runs the same target after the regression and certified-workflow tests. This closes table/figure-to-bundle traceability for the currently implemented results. It does not yet constitute a DOI release or clean container-build attestation; those remain Gate F work.

### Implemented claim-guarded AEI manuscript

The object-oriented `AEIManuscriptAssembler`, `ManuscriptClaimGuard`, and `ManuscriptArtifactStore` assemble `paper/manuscript-v1/GearRL_AEI_MANUSCRIPT.md` exclusively from the declared manuscript source, the frozen closest-method audit, and registered publication artifacts. The guard requires the modeled-validity scope and rejects unsupported production, fatigue, physical-validation, learning-improvement, universal-priority, and state-of-the-art phrases. The manuscript explicitly excludes the legacy reference-graph path-ranking experiment from its primary claim.

The manuscript manifest hashes every directly read registry and source plus the assembled output. `make paper-verify` regenerates it in a clean temporary directory and requires byte identity. This completes the reproducible digital draft package; editorial polishing, journal-template conversion, DOI release, and independent clean-environment attestation remain pre-submission work.

### Implemented submission-readiness audit

`SubmissionReadinessAuditor` evaluates fourteen declared AEI gates using replaceable object-oriented evidence-check strategies. `BenchmarkIntegrityCheck` verifies every member of the frozen 400-instance regression set, while `CuratedIntegrityCheck` verifies hashes and physical solver/evaluator separation for the 50 requirements-first cases. Other checks bind CAE verification and sample size, stochastic seed count, scaling observations, strength coupling, uncertainty, closest-method coverage, registered publication assets, manuscript scope, and reproducibility inputs.

The frozen `paper/submission-readiness-v1` report records eleven passed local gates, one partial legacy-benchmark gate, zero failed gates, and two external pending gates. Its verdict remains `ready_to_submit: false` until independent container execution and archival release/DOI evidence exist. `SubmissionReadinessArtifactStore` hashes and byte-reproduces this verdict through `make paper-verify`, preventing a locally complete scientific bundle from being misreported as externally released or independently reproduced.

### Implemented editable AEI submission package

The official AEI author guide was checked on 2026-07-11 and its numeric submission constraints were frozen in `paper/aei_submission_source.json`: the abstract may contain at most 250 words, the manuscript requires 1-7 keywords, and the separate highlights file requires 3-5 bullets of at most 85 characters each. The manuscript now uses stable semantic literature IDs that `ManuscriptCitationResolver` converts to numbered in-text citations, and coverage validation requires every registered closest method to be cited. Data availability and generative-AI preparation declarations appear before the references.

`AEILatexRenderer`, `AEISubmissionValidator`, and `AEISubmissionPackageStore` generate and byte-reproduce `paper/aei-submission-v1`, including editable `elsarticle` LaTeX, separate highlights, captions, and three numbered evidence-derived SVG figures. The source compiles locally to a ten-page PDF with `pdflatex -shell-escape`. The package remains deliberately provisional: no author identities, corresponding-author details, funding statement, competing-interest statement, or archival dataset identifier are invented. These five author/external fields are explicit blockers in `validation.json` and feed the frozen submission-readiness verdict.

### Implemented clean-environment attestation

`CleanEnvironmentAttestor` creates a new prefix from the platform-specific explicit Conda lock, installs the separately hash-pinned pip layer, checks out a detached local clone at the recorded commit, and constructs a prefix-isolated process environment. It then runs the full regression suite, the publication, literature, manuscript, and AEI-package verifiers, and direct integrity checks for the pilot and confirmatory robustness draws. The downstream readiness artifact is intentionally excluded because it hashes the clean attestation; including it would create a provenance cycle. `GitCommitCheckout`, `SourceTreeHasher`, replaceable `CommandRunner`, and `CleanEnvironmentEvidenceStore` separate source isolation, hashing, execution, and persistence.

The frozen `data/results/clean-environment-v1` evidence attests commit `bb7414ab1feed254b065274b48e998a4a55edef6`. All seven acyclic scientific verification targets passed, including direct integrity checks for both robustness draw bundles. The explicit installed Conda inventory hash equals the committed lockfile hash `9e336f12028ae556612a03c33f742a488e71c54bcc34e83d489f5aabe579696f`; the pip freeze, source tree, stdout, stderr, and command runtimes are separately recorded. This satisfies independent locked-prefix reproduction on Linux. It is not a container-engine attestation because Docker and Podman are unavailable on the host.

### Implemented joint assembly-robustness pilot

`AssemblyRobustnessStudy` evaluates joint shaft-location error, conservative housing-clearance erosion, and transverse-backlash allowance through the independent reference verifier. The input shaft is a fixed datum; the remaining shaft centers receive independent uniform two-axis perturbations. `AssemblyScenarioFactory`, `AssemblyPerturbationSampler`, `AssemblyRobustnessEvaluator`, `LayoutBootstrapInterval`, and `AssemblyRobustnessEvidenceStore` separate factor declaration, seeded sampling, adjudication, layout-level inference, and deterministic compressed persistence.

The frozen `assembly-robustness-v1` pilot contains 120 feasible layouts, 27 scenarios, 512 draws per layout, and 1,658,880 draw-level outcomes. With zero backlash, no continuously perturbed layout remains valid under the exact center-distance rule. Both 0.02 and 0.05 mm backlash declarations yield the same pooled modeled-valid probability of 0.0319, and housing erosion from 0 to 0.1 mm has no effect because nominal sampled boundary margins range from 20 to 102 mm. The pilot therefore establishes brittleness and factor saturation, not a calibrated manufacturing-yield estimate. Its diagnostic outcome motivates a separately predeclared finer confirmatory backlash grid; the grid must be frozen before that computation.

The confirmatory protocol is frozen before execution at `data/protocols/assembly-robustness-confirmatory-v2.json`. It retains 120 layouts, 512 draws, 5,000 layout-bootstrap samples, and seed 2026; crosses four shaft-location tolerances from 0.0025 to 0.025 mm, the zero and 0.1 mm housing-erosion extremes, and seven backlash allowances from 0 to 0.02 mm. The 56-scenario grid targets the pilot saturation transition without changing the inference unit or inspecting confirmatory outcomes.

The frozen confirmatory result contains 3,440,640 draw-level outcomes. At 0.02 mm backlash, pooled modeled-valid probability saturates near 0.0319 for all four shaft-location tolerances. Below saturation, the declared factors interact strongly: at 0.005 mm backlash, modeled validity falls from 0.03197 under +/-0.0025 mm shaft error to 0.00036 under +/-0.025 mm. Housing-clearance erosion remains inactive across 0-0.1 mm because the sampled nominal boundary margins are 20-102 mm. The result is a conditional rigid-center model probability and exposes a tolerance-aware synthesis gap; it is not a measured manufacturing-yield estimate.

### Implemented literature and contribution gate

The machine-readable `literature/aei_closest_methods.json` records a search cutoff, the AEI venue requirement, ten DOI-backed closest methods, their engineering-knowledge representations, synthesis and validation scopes, closest overlap, and the remaining difference to GearRL. The set deliberately includes strong counterexamples: graph-based product architecture generation with simulation, graph-based robot topology-to-CAD design, planetary-transmission topology synthesis, automated gearbox component sizing, constrained simulation-based optimization, constrained DRL architecture design, and gear-specific strength optimization.

The review rules out novelty claims for graph-based design, gear optimization, knowledge formalization, constrained learning, or simulation coupling in isolation. The defensible candidate contribution is their evidence-oriented integration: an executable requirements and mesh-graph schema, blind bounded synthesis, independent positive certificates and complete negative proofs, strength-coupled design admission, and hash-bound reporting. Any novelty statement must say `within the audited closest-method set`; the matrix does not establish a universal first.

`LiteratureEvidenceLoader`, `LiteratureMatrixRenderer`, and `LiteratureArtifactStore` validate, render, hash, and reproduce the matrix and its claim register. The frozen artifact is `paper/literature-v1`, and `make paper-verify` requires byte identity. The claim register explicitly prohibits manufacturing-ready, fatigue-qualified, physically validated, generally superior, and learning-speedup claims on current evidence.

### Implemented scaling and anytime study

The frozen `scaling-v1` protocol evaluates exact enumeration, process-isolated CP-SAT, and differential evolution across tooth-domain sizes of 5, 9, 13, and 17 values per decision (`625` to `83,521` full tuples). Each size contains two constructive feasible families and two independently exhaustive infeasible families. Shared candidate budgets are 250, 1,000, 7,000, and 100,000; differential evolution uses 30 fixed seeds, while deterministic methods use one run. Solver inputs exclude oracle truth.

At the largest domain, CP-SAT recovers both feasible cases and proves both negative cases at every budget. Exact enumeration recovers both feasible cases at every budget but completes both negative proofs only at 100,000 candidates. Differential evolution has median feasible recovery 0.5 and worst-seed recovery 0 at budget 250, reaches 1.0 by budget 1,000, and never proves negative cases. Therefore, correct negative prediction and proof status are reported separately. Runtime is descriptive on the recorded machine and one-thread configuration; this small structured family does not establish general asymptotic superiority.

The artifact contains 16 oracle-adjudicated cases, 2,048 raw observations, 48 method-size-budget summaries, and source, environment, hardware, and thread provenance. Its scientific source tree is clean at commit `e29e57c`; the manifest separately records the unrelated `opencode.json` and generated output directory as dirty paths. The publication registry derives a largest-domain table and median anytime figure directly from the frozen manifest and summary.
