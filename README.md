# GearRL: Certified Gear-Train Synthesis Research Platform

GearRL develops reproducible synthesis and validation workflows for planar,
external-spur compound gear trains. The certified model checks full-train signed
speed ratio, finite inputs, compatible modules, standard unshifted undercut
limits, transverse contact ratio, mesh center distances, axial layers, boundary clearance,
interference, and optional in-house plane-stress tooth-root screening.

The current publication path targets a fully digital *Advanced Engineering
Informatics* study. GearRL does not claim physical manufacturing validation.

The verifier boundary is exercised by 50 authored analytical cases spanning
simple and compound trains, ratio parity, center distance, boundary clearance,
unintended collisions, axial stacking, tooth rules, module compatibility, and
graph integrity. Regenerate the hash-addressed corpus with:

```bash
conda run -n ai python run_validator_corpus.py \
  data/benchmark/validator/certified-planar-v3-curated-50
```

## Environment

Create or update the required research environment:

```bash
conda env update -n ai -f environment-ai.yml
```

## Certified Benchmark Workflow

Run the deterministic certified baseline. Each run writes a UUID-backed bundle
with a manifest, raw per-instance results, and independent certificates:

```bash
conda run -n ai python main.py --seed 2026 --count 100 --output-root artifacts/runs
```

The primary research plan is documented in `TOP_JOURNAL_RESEARCH_PLAN.md`.
The DOI-backed closest-method matrix and bounded contribution claim register are
generated from `literature/aei_closest_methods.json` into
`paper/literature-v1`. They are verified by `make paper-verify` alongside the
numerical publication artifacts. The claim-guarded AEI manuscript draft is
frozen at `paper/manuscript-v1/GearRL_AEI_MANUSCRIPT.md`; its manifest binds the
draft to the literature matrix, manuscript source, and publication registry.

The requirements-first curated benchmark is frozen at
`data/benchmark/curated/requirements-first-50-v1`. Its 50 explicit briefs keep
solver inputs physically separate from evaluator-only witnesses and exhaustive
negative proofs. Regenerate it with:

```bash
conda run -n ai python run_curated_benchmark.py data/benchmark/curated/requirements-first-50-v1
```

The historical 400-instance data remains a path-selection regression benchmark,
not evidence of inverse synthesis.

Run the requirements-first solver without exposing evaluator evidence, then
adjudicate the sealed predictions in a separate process:

```bash
conda run -n ai python run_blind_synthesis.py \
  data/benchmark/curated/requirements-first-50-v1/solver-inputs \
  data/results/curated-blind-v1/predictions.json
conda run -n ai python run_blind_adjudication.py \
  data/benchmark/curated/requirements-first-50-v1 \
  data/results/curated-blind-v1/predictions.json \
  data/results/curated-blind-v1/adjudication.json
```

Run the frozen 7,000-candidate exact, CP-SAT, and differential-evolution
comparison blindly, then adjudicate its sealed runs:

```bash
conda run -n ai python run_requirements_comparison.py \
  data/benchmark/curated/requirements-first-50-v1/solver-inputs \
  data/results/requirements-comparison-v1/blind
conda run -n ai python run_requirements_comparison_adjudication.py \
  data/benchmark/curated/requirements-first-50-v1 \
  data/results/requirements-comparison-v1/blind \
  data/results/requirements-comparison-v1/adjudication.json
```

OR-Tools CP-SAT runs in a dedicated subprocess because its protobuf runtime is
not binary-compatible with the PyTorch runtime in one process. Exact enumeration
and CP-SAT can prove bounded negative cases. Differential evolution is an
incomplete stochastic comparator and is reported as such.

Run the predeclared scaling and anytime protocol over four tooth-domain sizes,
four equal candidate budgets, and 30 differential-evolution seeds:

```bash
conda run -n ai python run_scaling_study.py \
  --dataset data/benchmark/curated/requirements-first-50-v1 \
  --output data/results/scaling-v1
```

The frozen manifest records source identity, environment hashes, hardware, and
thread settings. Correct negative classification is reported separately from a
complete infeasibility proof.

Freeze the predeclared 400-instance benchmark (250 procedural, 50 tight
clearance, and 100 certificate-backed near-infeasible cases):

```bash
conda run -n ai python -c "from benchmark.freeze import BenchmarkFreezer; BenchmarkFreezer().freeze_protocol('data/benchmark/frozen/compound-v1-frozen-400-r2')"
```

## Learned-Policy Evidence Gate

`PairedEfficiencyStudy` evaluates a fixed masked policy and the predeclared
branch-and-bound baseline on the same instances. It retains the learned-policy
claim only when every policy result remains valid under the declared model and
the paired bootstrap lower confidence bound exceeds a 30% median time
reduction. A failed gate is reported as evidence against that claim; it does
not alter the certified deterministic-solver result.

Create a traceable paired-policy bundle, including the trained model checkpoint,
raw same-instance comparisons, and the bootstrap decision summary:

```bash
conda run -n ai python run_paired_policy_study.py --seed 2026 --train-instances 40 --test-instances 120
```

## Verification

```bash
conda run -n ai pytest -q
```

Regenerate every committed manuscript table and figure plus the literature
matrix and assembled manuscript in temporary directories, then require byte
identity with their hash-bound registries:

```bash
conda run -n ai make paper-verify
```

The same target verifies `paper/submission-readiness-v1`. This fail-closed audit
hash-checks the blind 50-case benchmark, all 400 legacy benchmark members, CAE
and uncertainty evidence, the 30-seed scaling protocol, literature positioning,
publication assets, and manuscript scope. Its current verdict is not yet ready
to submit: independent container execution and an archival release/DOI require
external evidence, while the 400-case path-ranking benchmark is explicitly
partial rather than requirements-first synthesis evidence.

The provisional editable journal package is frozen at
`paper/aei-submission-v1`. It contains an `elsarticle` LaTeX source, separate
highlights, numbered figure files and captions, and a machine-readable
validation report. The report enforces the current official AEI limits of a
250-word abstract, 1-7 keywords, and 3-5 highlights of no more than 85
characters. It intentionally remains `package_ready: false` until the authors
provide authorship/contact metadata, funding and competing-interest statements,
and a persistent archival dataset identifier.

The clean-environment attestation is stored at
`data/results/clean-environment-v1`. It was produced from a detached local clone
of the recorded commit in a newly created `/tmp` prefix using
`environment-ai.lock` plus the hash-pinned pip requirements. The full test suite
and all six frozen-artifact verifiers passed there. The report binds the source
tree, explicit Conda inventory, pip inventory, commands, outputs, and runtimes.
This is an independent locked-prefix reproduction, not a container execution;
the host does not provide Docker or Podman.

The frozen joint assembly-robustness pilot is stored at
`data/results/assembly-robustness-v1`. It retains 1,658,880 draw-level outcomes
from 120 feasible frozen layouts, 27 declared shaft/housing/backlash scenarios,
and 512 seeded perturbations per layout. The pilot is diagnostic: zero declared
backlash yields zero modeled acceptance under continuous location error, while
0.02 and 0.05 mm allowances both yield 3.19%, and housing-clearance erosion up
to 0.1 mm is inactive against nominal 20-102 mm boundary margins. These
saturated factors are not used for a magnitude-effect claim; they predeclare
the need for a finer confirmatory backlash grid.

The frozen bundle is stored at `paper/generated-v1`. Its registry maps each
table and vector figure to the exact solver, CAE, uncertainty, or
strength-coupling evidence files used to generate it. Figures use a structured,
backend-independent SVG renderer so clean reproduction does not depend on a
host font rasterizer. This verifies reporting provenance; the underlying
scientific experiments retain their separate commands and manifests.

For the full frozen protocol, including the 400-instance mixed benchmark:

```bash
scripts/reproduce_certified_run.sh
```

Persist the preregistered 120-layout v3 involute-tooth static-strength screening study:

```bash
conda run -n ai python run_cae_study.py --dataset data/benchmark/frozen/compound-v1-frozen-400-r2
```

The frozen publication artifact is generated with
`--frozen-output data/results/cae-study-v3`. It is an illustrative static
bending screen under the declared 1 N m load case, not contact-fatigue or
physical safety evidence.

Persist the owned solver verification gates before using CAE screening results:

```bash
conda run -n ai python run_cae_verification.py
```

Persist the signed shaft-offset sensitivity study under the exact mesh-center model:

```bash
conda run -n ai python run_tolerance_study.py --dataset data/benchmark/frozen/compound-v1-frozen-400-r2
```

Persist the transverse-backlash versus center-expansion response surface:

```bash
conda run -n ai python run_backlash_study.py --dataset data/benchmark/frozen/compound-v1-frozen-400-r2
```
