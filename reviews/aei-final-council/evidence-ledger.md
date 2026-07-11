# AEI Final Critical-Review Evidence Ledger

Date: 2026-07-11

## Scope

Target: the GearRL repository, frozen computational evidence, and AEI manuscript/package. Decision: whether the current fully digital work supports submission to *Advanced Engineering Informatics* and what must change for a top-level submission.

Six independent remits were used: novelty/related work, architecture/correctness, gear-domain validity, experimental/statistical validity, reproducibility, and AEI impact/adoption. This ledger deduplicates their comments but preserves distinct root causes. Physical experiments are not required for the selected digital scope; external digital cases, independent computational references, and valid internal evidence remain required.

## Numbered Ledger

### L01 - Confirmatory robustness scenarios collide (critical)

`AssemblyScenarioFactory` formats backlash to three decimals (`evaluation/assembly_robustness.py:78`) and aggregation is keyed by that string (`:141`, `:154`). Thus 0.0005 and 0.001 mm both become `backlash-0.001`. The frozen summary repeats the identifier and reports 122,506 failures for a nominal 61,440-draw scenario (`data/results/assembly-robustness-confirmatory-v2/summary.json:51,61,77`). The affected estimates, intervals, raw provenance, table, and interaction claim are invalid. Resolution: injective canonical keys, uniqueness/count checks, full rerun into a new evidence version, and regeneration of dependants.

### L02 - CP-SAT completeness is unsound for positive ratio tolerance (critical)

The enumerator/oracle accept `isclose` within `ratio_tolerance`, while `solver/cp_sat_worker.py:58` converts the target to a fraction and enforces exact equality. CP-SAT can therefore return a complete negative result when tolerance-valid, non-exact tuples exist. Resolution: sound integer interval constraints or fail-closed rejection of nonzero tolerance, plus adversarial cross-solver tests and withdrawal/regeneration of affected proof claims.

### L03 - Full solver-visible specification is not production-validated (high)

`ProblemSpecification` includes prescribed shafts and `DesignSpace`, but `ProductionCandidateValidator` passes only `specification.problem` to `ReferenceVerifier`; it does not independently enforce prescribed centers, allowed modules, stage counts, compound bounds, or layer bounds. Resolution: an OOP composite `ProblemSpecificationValidator` with mutation tests for every field.

### L04 - Negative “proofs” are execution assertions, not replayable proof objects (high)

`OracleProof`/`benchmark/specification.py:131-154` retain booleans, counts, kinds, and reasons rather than an independently checkable elimination ledger. “Complete bounded infeasibility proof” and “independently checkable negative conclusion” overstate an attested exhaustive execution. Resolution: emit a compact domain/coverage/elimination ledger and separate checker, or rename claims to independently reproduced bounded-search results.

### L05 - Certificate model/version identity is ambiguous (high)

Obstacle and CAE mutations retain the `certified-planar-v3` label and the certificate is a mutable aggregate, so the label does not uniquely identify all component models. Resolution: immutable certificate aggregates with explicit versioned component identities and migration/compatibility rules.

### L06 - Oracle independence is inadequately demonstrated (medium-high)

Geometry logic is duplicated and the independence test largely checks absence of selected strings, rather than differential semantic independence. Resolution: high-precision or independently maintained geometry references, broad property-based differential tests, and documented non-shared derivations.

### L07 - Production CAE mesh is not shown converged for admission (critical)

The default 8x12 mesh has 240 elements (`cae/gear_screening.py:123`). Frozen refinement stress rises from 80.50 to 121.45 MPa; the default is about 24% below the finest result. The gate passes only because the final pair differs by 7.36% (`cae/verification.py:117`), yet classifications use the coarse model. Resolution: reference/asymptotic convergence across representative extremes, a production error bound, and rerun; at minimum prove classifications invariant at the finest verified mesh.

### L08 - Backlash variable is physically mischaracterized (high)

`physics_validator/reference_verifier.py:233` maps supplied backlash directly to positive center-distance error using a local linear relation, while contact ratio remains nominal (`:275`). It represents allowable center-distance-induced transverse backlash increase, not general available assembly backlash. Resolution: rename/scope throughout, or model working pressure angle, operating radii, tooth thickness/backlash, interference, and operating contact ratio.

### L09 - Root-stress verification is only a one-case sanity check (high)

Loads are distributed at the tooth-tip edge (`cae/gear_screening.py:87`), fillet geometry is heuristic (`cae/involute.py:118`), and one m=2,z=24 case is compared with Lewis (`cae/verification.py:106`). This does not validate domain-wide fillet stress. Resolution: label it a Lewis sanity check or validate representative boundaries against ISO/AGMA or an independently built trusted FE reference.

### L10 - Strength admission threshold is unexplained and compounded (high)

`run_strength_coupled_study.py:25,31` divides S355 yield by 1.5, then requires allowable/stress >=2.3, an effective yield factor of 3.45. The manuscript does not state or justify both factors. Resolution: one declared limit-state equation with justified factors and threshold-sensitivity analysis of retained/redesigned/rejected counts.

### L11 - Mesh force equilibrium is inconsistent with efficiency propagation (high)

`physics_validator/reference_verifier.py:85-86` applies efficiency-reduced shaft torque separately to each member, yielding unequal tangential contact forces across a mesh. Resolution: equal-and-opposite mesh contact force with losses represented separately, followed by strength/sensitivity reruns.

### L12 - Robustness layout bootstrap has no defensible population estimand (high)

The first 120 feasible instances are taken (`evaluation/assembly_robustness.py:135`); the frozen order makes them the training prefix (`data/benchmark/frozen/compound-v1-frozen-400-r2/index.json:4,482,486`). Treating these as exchangeable layouts (`assembly_robustness.py:115`) does not support inference to the 400 cases or unseen designs. Resolution: declare target population/estimand and use seeded probability or family-stratified held-out sampling with identities frozen.

### L13 - “Confirmatory” interaction/no-effect conclusions were not predeclared (high)

The protocol freezes a 56-cell grid but no primary contrast, effect/equivalence margin, decision rule, or multiplicity policy. Code reports separate means and marginal percentile intervals (`evaluation/assembly_robustness.py:155`). Resolution: preregister difference-in-differences and equivalence contrasts, simultaneous/hierarchical uncertainty, and label other cells exploratory.

### L14 - Zero failures are reported with a zero-width interval (high)

Finite Sobol sampling yields all-zero per-layout rates, and layout-only bootstrap consequently reports Toolox `[0,0]` (`evaluation/load_uncertainty.py:170,212`; `data/results/load-uncertainty-v1/results.json:208`). Resolution: repeated scrambles and an appropriate one-sided upper/tolerance bound; say “no failures observed” absent an analytical bound.

### L15 - Nested simulation error and convergence are not quantified (high)

Assembly and load studies use one seed/scramble and fixed samples, bootstrap only layouts, and report probabilities near 1e-4 to five decimals (`evaluation/assembly_robustness.py:143,157`; `evaluation/load_uncertainty.py:167`). Resolution: multiple randomizations, draw-count convergence, variance decomposition/nested intervals, and precision-appropriate rounding.

### L16 - Sobol sensitivity estimand and uncertainty are missing (medium)

Per-layout indices are arithmetically averaged (`evaluation/load_uncertainty.py:194,209`) without interval or a definition separating average conditional sensitivity from joint-response sensitivity. Resolution: define estimand, report layout dispersion and repeated-scramble intervals, and verify convergence.

### L17 - Closest-method literature audit is not reproducible or broad enough (high)

The ten-item manually curated audit lacks database/query dates, screening flow, citation chaining, full-text extraction, and independent screening. It also undercovers formal design-space exploration, SAT/SMT proof logging, MBSE, constraint configuration, KBE, and proof-carrying workflows. Resolution: reproducible multi-database protocol, recorded screening/extraction, broader fields, and calibrated absence claims.

### L18 - Engineering-knowledge novelty is asserted but not isolated (critical for AEI fit)

The fixed directed graph/object schema is called executable knowledge, but there are no formal semantics, competency questions, reasoning coverage measures, schema baseline, knowledge/rule ablation, interoperability mapping, reuse study, or extension-effort result (`benchmark/specification.py:30-100`; manuscript methods/results). Resolution: falsifiable informatics hypotheses and comparison with a flat encoding on coverage, error detection, traceability, authoring/extension effort, and exchange/reuse.

### L19 - Novelty is a workflow conjunction rather than a tested scientific advance (high)

Current novelty combines graph representation, solvers, certificates, CAE, and uncertainty, but does not test which informatics mechanism causes improvement. Resolution: explicit hypotheses and component/baseline ablations tied to measurable informatics outcomes.

### L20 - External validity and structural generality are absent (critical for broad claims)

All outcomes use authored cases and one three-shaft topology; the external registry is only a scaffold (`benchmark/external.py:31-45`) and its test uses synthetic metadata. Resolution: independently authored/practitioner or published digital briefs, blind conversion/provenance, held-out acceptance criteria, and at least one structurally different topology; otherwise scope as a bounded proof of concept.

### L21 - Comparator set cannot establish superiority (high)

Only project-local enumeration, CP-SAT, and differential evolution are compared (`evaluation/requirements_comparison.py:39-63`). Resolution: an independently maintained formal solver/baseline and an established domain workflow, equalized budgets/objectives, and metrics for effort and certificate capability as well as runtime.

### L22 - Practical engineering impact and adoption are not measured (high)

No engineer time, authoring cost, trace-debugging improvement, downstream handoff, decision change, or design-quality endpoint is measured. There is no installable package/public API/adapter; usage is repository scripts and environment mutation. Resolution: realistic workflow KPI with independent users/case authors, a representative traceable decision case, and a versioned installable package/API/CLI plus external-consumer integration test.

### L23 - Robustness is diagnosed after synthesis rather than designed (high)

Certificates admit nominal designs whose downstream modeled acceptance is about 3.19%; tolerance/robustness is neither an admission criterion nor objective. Resolution: tolerance-aware synthesis with preregistered threshold/objective, held-out comparison against nominal synthesis, and tradeoffs in size, strength, feasibility, and modeled acceptance.

### L24 - Clean attestation can remain green after source/environment drift (critical)

`CleanEnvironmentEvidenceStore.verify` checks the report hash and two stored fields (`reproducibility/clean_environment.py:156-164`) but not current lock hashes, tree hash, command ledger, exits, or commit/content relationship. Current report attests an earlier commit. Resolution: an OOP fail-closed attestation-policy verifier with full command, lock, tree, and ancestry/content checks plus mutation tests.

### L25 - No end-to-end scientific regeneration workflow exists (high)

`make paper-verify` verifies committed artifacts; `scripts/reproduce_certified_run.sh` runs pytest and `main.py`, not every solver, CAE, uncertainty, robustness, summary, and figure pipeline. Resolution: locked/containerized OOP orchestration that regenerates all studies into fresh paths, compares deterministic outputs/declared tolerances, and retains logs.

### L26 - Robustness verifier checks bytes/counts, not scientific semantics (critical)

`AssemblyRobustnessEvidenceStore.verify` hashes files and counts gzip lines (`evaluation/assembly_robustness.py:215-231`) but does not stream and reconstruct summary statistics or enforce unique complete keys. Resolution: an independent semantic checker for schema, keys, counts, rates, failure totals, and seeded bootstrap reconstruction, including coordinated-corruption tests.

### L27 - Clean run is host-specific and self-attested (high)

The runner hard-codes a local Conda path (`run_clean_environment_attestation.py:26-28`), report commands retain workstation paths, and stdout/stderr and inventories are discarded after hashing (`reproducibility/clean_environment.py:42-55,115-131`). Resolution: portable parameters/container, normalized retained logs/inventories, and public CI or independent-worker execution.

### L28 - Provenance schemas are fragmented (medium-high)

Bespoke manifests inconsistently bind commit/tree, lock, runtime inventory, platform, thread settings, inputs, and outputs; the robustness manifest omits source/environment identity. Resolution: a shared immutable OOP `ScientificArtifactManifest` aggregate and central validator, followed by regeneration/migration of submission-critical bundles.

### L29 - Artifact is not archival or legally reusable (medium)

There is no persistent DOI, LICENSE, CITATION.cff, or CodeMeta; readiness marks archival/author metadata pending. Resolution: licensed versioned release, public DOI archive, citation metadata, checksums/commit in manuscript, and independent retrieval verification.

## Evidence Boundaries

Demonstrated despite these findings: a substantial OOP digital prototype, bounded authored benchmark infrastructure, multiple solver implementations, traceable positive-candidate checking, automated tests, and large computational experiments whose unaffected portions may be recoverable after semantic revalidation.

Not demonstrated: industrial or topology-general effectiveness, an isolated AEI knowledge-method advance, formal negative proof artifacts, domain-wide CAE accuracy, or reproducible confirmatory robustness interactions. The two collided robustness cells and any nonzero-tolerance CP-SAT completeness conclusions are contradicted by source evidence.
