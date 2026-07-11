# GearRL: Certified Gear-Train Synthesis Research Platform

GearRL develops reproducible synthesis and validation workflows for planar,
external-spur compound gear trains. The certified model checks full-train signed
speed ratio, finite inputs, compatible modules, standard unshifted undercut
limits, transverse contact ratio, mesh center distances, axial layers, boundary clearance,
interference, and optional in-house plane-stress tooth-root screening.

The current publication path targets a fully digital *Advanced Engineering
Informatics* study. GearRL does not claim physical manufacturing validation.

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

For the full frozen protocol, including the 400-instance mixed benchmark:

```bash
scripts/reproduce_certified_run.sh
```

Persist the preregistered 120-layout static-strength screening study:

```bash
conda run -n ai python run_cae_study.py --dataset data/benchmark/frozen/compound-v1-frozen-400-r2
```

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
