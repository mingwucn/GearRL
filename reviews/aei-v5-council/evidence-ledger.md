# AEI v5 Critical-Review Evidence Ledger

## Scope

Six independent reviewers inspected the committed AEI artifacts, evidence, and implementation: novelty/related work, architecture, gear-domain validity, statistics, reproducibility, and practical impact. The target is a fully digital *Advanced Engineering Informatics* submission. Physical qualification, manufacturing yield, operational gearbox design, and external validity are outside the asserted claim.

## Findings

### R01 - No independent external brief exercises the primary pipeline

The 50 primary cases are authored; the pending-review planetary encoding bypasses the primary mesh-graph pipeline. The current work demonstrates internal bounded validity, not transfer to independently authored engineering briefs. Evidence: `paper/manuscript-v5/GearRL_AEI_MANUSCRIPT.md`, Sections 4 and 7.

### R02 - The bounded model cannot support a downstream gearbox qualification decision

The fixed two-mesh, three-shaft planar family excludes shafts, bearings, fatigue, contact stress, dynamics, thermal behavior, noise, and production qualification; the structural gate failed. A positive certificate supports only declared kinematic/geometric digital admission. Evidence: manuscript Sections 1 and 7; `data/results/cae-refinement-audit-v1/result.json`.

### R03 - Novelty priority is not established by the literature audit

Several comparisons rely on publisher metadata, formal proof/certificate literature is incomplete, and no independent screening was performed. Remediation removes absence, universal-priority, and first-of-kind claims; C3 is now an `unverified-bounded-hypothesis`. Evidence: `literature/aei_closest_methods.json`; `paper/literature-v4`.

### R04 - Transferable informatics value is plausible but not experimentally isolated

The evaluated contribution integrates executable specifications, solver hiding, independent adjudication, replayable proofs, and provenance, but no cross-domain transfer or full component ablation shows the incremental value of each mechanism. The mutation study remains a narrow deterministic competency test.

### R05 - The preregistered design-improvement claim is unsupported

Across 12 independent train-select-test repetitions, the mean envelope-validity difference is 0.003206 with interval [0.003051, 0.003362], below the 0.005 threshold; 61 layouts are selected at least once. The manuscript reports this as a negative result. Evidence: `data/results/repeated-selection-v1`.

### R06 - Engineering usability and adoption cost are unevaluated

No independent engineer study measures brief authoring, diagnostic interpretation, handoff, integration, or decision time. The current interface and schema demonstrate implementation, not adoption impact.

### R07 - Scalability varies only tooth-domain size in one fixed family

The scaling evidence contains 2,048 solver-run records on 16 authored cases, but does not vary topology, stages, obstacles, rule density, or hardware. Runtime is descriptive and not deployment evidence. Evidence: `data/results/scaling-v3`; manuscript Sections 4, 6, and 7.

### R08 - Assembly evidence is a nominal-contact-ratio envelope screen

Perturbed center distance is checked while contact ratio remains evaluated at nominal reference geometry. Only eight independent scrambles support inference, and input distributions are assumed rather than calibrated. Remediation consistently calls the endpoint center-distance-envelope validity, identifies eight inferential units, and disclaims operating engagement, assembly yield, and manufacturing relevance.

### R09 - Noncanonical terminal IDs caused invalid constructive witnesses

The oracle and solvers previously hard-coded `input`/`output`. Remediation introduces an OOP `CompoundTrainFactory`, derives terminal IDs from the specification, chooses a collision-free internal ID, and adds cross-component noncanonical-ID tests. Focused tests pass.

### R10 - A forged serialized certificate Boolean could pass legacy comparison

The legacy comparison trusted `certificate_json["valid"]`. Remediation independently reruns `ReferenceVerifier.verify_with_cae` on every returned train and includes an adversarial forged-certificate test.

### R11 - Certificate matching omitted schema and validator-stack identity

Remediation requires exact subject schema and complete model-identity digest in addition to problem/train hashes; schema and verifier substitutions are tested. Content hashes provide identity/tamper detection, not authentication or nonrepudiation.

### R12 - Oracle independence remains structurally rather than behaviorally established

New noncanonical-ID cross-component tests improve contract coverage, but there is no systematic generated differential suite spanning all numeric, obstacle, topology, and boundary edge cases. Independence beyond the bounded corpus remains partial.

### R13 - Fixed-seed binomial intervals lacked a sampling population

Remediation removes the interval. The planetary artifact reports descriptive counts for 12 declared seeds, stop reasons, and no success-probability claim. Every stored candidate and aggregate is now semantically reevaluated in `planetary-baseline-v3`; the human source conversion remains pending review.

### R14 - Negative-proof replay did not enforce the exact expected population

Remediation derives the evaluator-declared negative-ID set, requires exact equality, uniqueness, infeasible and complete proof status, and per-subject semantic replay. Deletion/count rewrite, duplication, positive substitution, feasible-status, and incomplete-status corruptions are rejected.

### R15 - Scaling timing was described as fixed-thread despite unset variables

Remediation states that library thread environment variables were uncontrolled, deterministic methods had one timing run, and all timing is descriptive only. No comparative timing generalization is retained.

### R16 - Clean attestation and readiness were absent during review

This is a temporal pre-release blocker, not a scientific contradiction. The final release must commit `data/results/clean-environment-v3` and `paper/submission-readiness-v3`, then pass `make release-verify` from the attested commit.

### R17 - Several evidence verifiers do not recompute full scientific derivation

Assembly, negative proofs, repeated selection, and planetary candidates receive semantic replay. Scaling summary hashes/counts, knowledge ablation, and some solver-comparison derivations are not fully recomputed from first principles by the release command. Artifact integrity is stronger than end-to-end semantic coverage for these studies.

### R18 - Child-manifest producer provenance is inconsistent

The aggregate binds committed bytes and source tree, but several legacy child manifests omit producer commit, clean-source state, command, or lock identities. New scaling, repeated-selection, and planetary artifacts carry stronger lineage; legacy evidence remains mixed.

### R19 - Legal, author, and archival metadata are externally incomplete

No author-selected license, citation metadata, signed release tag, public archive DOI, or complete author/declaration fields can be invented by the repository. `paper/aei-submission-v5/validation.json` therefore remains `package_ready: false`.

### R20 - The editable TeX package is not compile-tested

Byte reproduction is verified, but no pinned LaTeX/Inkscape toolchain builds and inspects a PDF in CI. This is an operational submission risk, not evidence that the numerical claims are false.

### R21 - Supply-chain assurance is incomplete

CI actions and pip requirements are pinned, but the container base lacks a digest, Conda URLs lack separately recorded content hashes, CI has no explicit least-privilege permissions block, and no SBOM/signature/vulnerability record is frozen.

### R22 - Concept export naming may imply manufacturing maturity

The repository contains a `ManufacturingWorkflow` whose DXF/SVG output is conceptual circle geometry rather than a qualified manufacturing model. This path is not used as manuscript evidence, but renaming and machine-readable scope guards would reduce downstream misuse risk.
