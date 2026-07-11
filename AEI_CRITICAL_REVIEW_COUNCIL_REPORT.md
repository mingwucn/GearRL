# GearRL AEI Critical Review Council Report

Date: 2026-07-11

## 1. Scope and evidence

This review evaluates whether the current GearRL repository supports a submission to *Advanced Engineering Informatics* (AEI). The intended contribution is a purely digital, object-oriented, certificate-producing workflow for constrained compound-gear design. No physical validation is claimed or required for the selected paper scope.

Six independent reviewers inspected the repository with distinct remits: novelty and framing; architecture and correctness; gear-domain and CAE validity; experiments and statistics; reproducibility; and engineering impact and AEI fit. A separate council of three reviewers adjudicated the consolidated findings.

Primary evidence included the research plan, canonical domain models, benchmark generator and frozen data loader, synthesis implementations, verifier, CAE implementation and verification, manufacturing exporters, experimental runners, reporting code, tests, environment definitions, CI, and provenance machinery. The test suite passed with 110 tests and 15 subtests.

Material evidence missing at review time includes a related-work matrix and manuscript, independently authored design problems, globally proven negative instances, an independent evaluation oracle, strong optimization baselines, real gear-tooth CAD/STEP artifacts, and a released content-addressed package of final experimental results.

## 2. Critical-review ledger

### F1. The benchmark tests path selection rather than inverse synthesis

**Severity:** Critical. **Confidence:** High.

`benchmark/generator.py` constructs the intended stages, tooth counts, shaft positions, solution edges, and decoys, then derives the target ratio and enclosure from that construction. `evaluation/comparison.py` supplies the reference stages and mesh graph to each solver. The current task therefore selects a valid path through an exposed, preconstructed graph; it does not synthesize topology, geometry, tooth counts, or placement from independent requirements.

**Resolution:** Define requirements-first problems independently of solutions. Hide reference solutions from all solver-facing data and make topology, tooth counts, module, axial stack, and placement actual decision variables.

### F2. Negative labels do not prove global infeasibility

**Severity:** Critical. **Confidence:** High.

Near-infeasible records are produced by invalidating the intended reference path. Failure of that path does not prove that no alternative design exists in the declared design space.

**Resolution:** Establish every negative label using an independently checkable exhaustive bounded search, a complete CP-SAT/MILP formulation, or a mathematical infeasibility proof.

### F3. Dataset partitions do not test unseen families

**Severity:** High. **Confidence:** High.

Training, validation, and test data reuse the same stage count, topology, edge ordering, procedural generator, and four boundary variants. Seed changes provide numerical variation but not structural distribution shift.

**Resolution:** Freeze disjoint topology, enclosure, obstacle, ratio, stage-count, module, and infeasibility-mechanism families. Reserve independently authored cases for external testing.

### F4. Ground truth and evaluation share the same verifier

**Severity:** Critical. **Confidence:** High.

`ReferenceVerifier` contributes generator labels, terminal admission, and final scoring. A verifier defect can therefore agree with itself and appear as perfect accuracy.

**Resolution:** Introduce an independently implemented evaluation oracle and establish agreement on curated analytical cases, adversarial cases, and the complete frozen benchmark.

### F5. The AEI novelty gap is undocumented

**Severity:** Critical. **Confidence:** High.

The research plan requires a related-work matrix, but the repository contains no current systematic comparison against gear synthesis, constrained optimization, knowledge-based engineering, certified search, CAD/CAE integration, or learning-guided design.

**Resolution:** Complete a traceable literature review and closest-method matrix before freezing contributions. Each novelty statement must identify a specific difference and supporting experiment.

### F6. Solver terminology and comparison are not credible yet

**Severity:** High. **Confidence:** High.

The named branch-and-bound implementation performs shallow exhaustive path enumeration without a bound or incumbent pruning. Comparisons omit the planned CP-SAT/MILP and evolutionary methods and do not enforce common tuning and runtime budgets.

**Resolution:** Rename the existing method accurately or implement real bounding and pruning. Add complete and evolutionary baselines through the common OOP solver interface, with frozen hardware, tuning, stopping, and objective rules.

### F7. Learning is not currently a positive contribution

**Severity:** High. **Confidence:** High.

The learned policy is slower than deterministic enumeration on the current benchmark. The protocol does not establish multi-seed, held-out-family, scaling, feature, imitation, PPO, or data-size effects.

**Resolution:** Treat learning as a negative result unless a preregistered multi-seed OOD/scaling study demonstrates a stable benefit in time, node expansions, or design quality.

### F8. Fundamental certificate predicates are incomplete

**Severity:** Critical. **Confidence:** High.

Intended meshes do not enforce common module and tooth-system compatibility, contact ratio, undercut, or tooth interference. Non-finite numerical values can bypass comparison-based checks and receive a valid certificate.

**Resolution:** Reject all non-finite inputs and derived quantities. Add module, pressure-angle/system, base/addendum/root geometry, contact-ratio, undercut, and interference rules with analytical and adversarial tests.

### F9. The CAE model is not yet an involute tooth-root model

**Severity:** Critical. **Confidence:** High.

The production FE geometry is a generic trapezoidal cantilever whose shape is effectively independent of tooth count, involute flank, and root fillet. Existing patch and beam tests validate the finite-element kernel more strongly than the gear-specific stress abstraction.

**Resolution:** Build parameterized involute and root-fillet geometry, perform gear-specific stress mesh convergence, and compare against an independently formulated standard calculation and a trusted numerical reference. Otherwise label the current model as a low-fidelity surrogate.

### F10. Loads, materials, and power transmission lack a defensible basis

**Severity:** High. **Confidence:** High.

Current safety factors use a lightly loaded illustrative case and an unsupported allowable stress. Contact fatigue, bending life, reliability, and common gear factors are absent; the declared efficiency value is unused in torque propagation.

**Resolution:** Define sourced application envelopes, material grades, duty cycles, life and reliability targets, and load factors. Propagate per-mesh efficiency consistently and keep static bending, contact, and fatigue conclusions separate.

### F11. “Manufacturing-aware” exceeds the demonstrated workflow

**Severity:** Critical. **Confidence:** High.

Axial feasibility is represented by layer labels, and SVG/DXF outputs contain pitch and outer circles. The system has no true tooth solids, shafts, bores, bearings, hubs, STEP assembly, or automated assembly-interference check.

**Resolution:** For the minimum paper, use “packaging-aware conceptual geometry export.” Retain “manufacturing-aware” only after implementing fabrication-relevant parametric geometry, STEP output, and machine-checkable assembly constraints.

### F12. CAE and robustness do not yet influence design meaningfully

**Severity:** High. **Confidence:** High.

The benchmark lacks strength-critical decision cases, and current safety margins are too large to discriminate designs. Tolerance studies use narrow common-mode perturbations and limited uncertainty dimensions.

**Resolution:** Create calibrated near-boundary design cases and integrate structural limits into search. Use declared independent and correlated uncertainty distributions and report sensitivity indices and failure modes.

### F13. Statistical analysis is incomplete

**Severity:** High. **Confidence:** High.

Current reports emphasize aggregate accuracy and median time. They lack paired method contrasts, effect sizes, runtime intervals, family stratification, multiplicity handling, failure-aware time-to-solution analysis, and adequate learned-policy seeds.

**Resolution:** Preregister primary estimands and use paired instance-level inference, robust effect sizes and intervals, seed-level dispersion, family-stratified reporting, and corrected secondary comparisons.

### F14. Final evidence is not artifact-reproducible

**Severity:** Critical. **Confidence:** High.

Final experiment bundles are ignored and untracked. The advertised full reproduction script regenerates a procedural benchmark instead of consuming the cited frozen dataset and omits several studies.

**Resolution:** Release a DOI-addressed, content-addressed evidence package and provide one OOP orchestrator that verifies inputs and regenerates every submitted table and figure.

### F15. Environment, provenance, CI, and legacy boundaries need strengthening

**Severity:** High. **Confidence:** High.

Official execution paths bypass the available lockfile. Manifests omit hardware, container, thread settings, and dirty-diff identity. CI exercises a smoke workflow rather than the scientific protocol, and legacy outputs are not clearly quarantined.

**Resolution:** Build CI and containers from one pinned lock, record complete execution provenance, reject or archive dirty production runs, add staged scientific regression checks, and create a canonical artifact registry.

### F16. OOP foundations exist, but independent substitution is incomplete

**Severity:** Medium. **Confidence:** High.

Typed records, runners, stores, and solver interfaces are substantial. However, synthesis depends directly on the concrete verifier, the verifier constructs concrete CAE internally, generation policy remains partly free-function business logic, and validation semantics changed without a model-version increment.

**Resolution:** Introduce injected validator, CAE, generator-family, and oracle strategy interfaces; move generation policy into cohesive objects; and version the full validation specification on every semantic change.

### F17. Demonstrated strengths

**Disposition:** Sustained positive evidence. **Confidence:** High.

The passing tests, frozen per-instance hashes, typed certificates, immutable bundle-store API, solver interfaces, FE kernel verification, and explicit digital-only scope form a credible software and auditability foundation. They do not by themselves validate the stronger synthesis, learning, CAE, or manufacturing claims.

## 3. Verdict council

All three verdict members sustained F1-F14 and F17. Two sustained F15 and one partially sustained it because existing hashes and tests mitigate, but do not remove, the reproducibility risk. All three partially sustained F16: it is a maintainability and independent-validation limitation, not a reason by itself to invalidate results.

There was no material disagreement about the critical blockers. Differences were limited to whether F7, F10, F11, F14, and F15 should be rated high or critical. The corrective priority is unchanged because F1-F5, F8-F9, F11, and F14 independently prevent the intended top-level claim.

## 4. Verdict

**Current AEI decision: not submission-ready; reconstruct and resubmit rather than submit the current study.**

Demonstrated now: a tested, object-oriented foundation for machine-readable validation records, bounded path enumeration, frozen digital experiments, low-fidelity structural screening, and conceptual geometry export.

Plausible but unproven: requirements-driven compound-gear synthesis, independent certified feasibility, generalization to unseen engineering problems, and an AEI-level engineering-knowledge representation contribution.

Contradicted by current evidence: genuine inverse synthesis on the frozen benchmark, a learned speed advantage, global infeasibility classification, involute tooth-root CAE validity, and manufacturing-ready output.

## 5. AEI reconstruction plan

### Gate A: claim and knowledge contribution

1. Complete the current-literature search and closest-method matrix.
2. Freeze one falsifiable AEI contribution: an object-oriented engineering-knowledge representation with independently checkable certificates for bounded requirements-first compound-gear synthesis.
3. Scope learning as optional and manufacturing output as conceptual until their gates pass.

**Exit evidence:** cited matrix, contribution-to-experiment map, terminology and claim register.

### Gate B: requirements-first benchmark and independent truth

1. Introduce OOP `ProblemSpecification`, `DesignSpace`, `GeneratorFamily`, `GroundTruthOracle`, and versioned schema abstractions.
2. Remove reference trains and solution edges from solver-facing instances.
3. Build at least 50 hand-authored analytical/adversarial cases and a larger procedural benchmark with disjoint train, validation, in-distribution test, OOD test, and external-case partitions.
4. Prove negative labels with a complete independent formulation and cross-check all labels with a second implementation.

**Exit evidence:** zero oracle disagreements on curated cases; independently proven labels; frozen distribution audit; hidden references.

### Gate C: engineering-valid certificate model

1. Enforce finite values, compatible modules and tooth systems, contact ratio, undercut, interference, directed efficiency, and axial interval constraints.
2. Model shafts, bores, hubs, face widths, bearings, obstacles, and prescribed input/output locations as explicit domain objects.
3. Use injected validator strategies and preserve a separate evaluation oracle.

**Exit evidence:** analytical tests, adversarial fault injection, property tests, model-versioned certificates, and independent verifier agreement.

### Gate D: credible synthesis and comparison

1. Implement actual search decisions for topology, tooth counts, modules, axial placement, and shaft positions.
2. Provide exact CP-SAT/MILP, deterministic bounded search, evolutionary, heuristic, and optional learned solvers behind a common OOP interface.
3. Freeze tuning, hardware, stopping rules, objectives, and budgets; measure quality, feasibility, proof status, nodes, time, and scaling.

**Exit evidence:** requirements-to-design synthesis without construction leakage, fair anytime curves, scaling results, and solver ablations.

### Gate E: digitally credible engineering analysis

1. Replace or explicitly demote the trapezoidal surrogate.
2. Implement involute/root-fillet geometry, gear-specific convergence, independent standard calculations, and a trusted digital reference comparison.
3. Define sourced application loads, materials, duty cycles, failure modes, and uncertainty distributions.
4. Couple structural and robustness constraints to synthesis so that they change admissible designs and tradeoffs.

**Exit evidence:** preregistered validation thresholds, near-boundary cases, sensitivity indices, uncertainty intervals, and failure taxonomy. Physical experiments remain outside the paper claim.

### Gate F: reproducible paper artifact

1. Build one class-based experiment orchestrator from the pinned environment lock.
2. Capture clean source identity, dataset/config/model hashes, command line, hardware, numerical backend, thread settings, container digest, and output hashes.
3. Regenerate every table and figure from frozen inputs and release raw records, checkpoints, logs, and manifests under a DOI.
4. Expand CI to validate frozen data, workflow smoke tests, container builds, and deterministic publication artifacts; quarantine legacy outputs.

**Exit evidence:** clean-machine one-command reproduction and a table/figure-to-bundle registry.

## 6. Submission rule

Do not submit to AEI until Gates A-D and F pass. Gate E must pass for any gear-stress or engineering-safety claim; otherwise the paper must explicitly present CAE as a low-fidelity digital screening demonstration. Learning remains outside the main contribution unless its preregistered gate shows a stable benefit.
