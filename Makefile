.PHONY: test paper-verify evidence-verify release-verify

PYTHON ?= python

test:
	$(PYTHON) -m pytest -q

paper-verify:
	$(PYTHON) run_publication_artifacts.py --verify paper/generated-v5
	$(PYTHON) run_literature_matrix.py --verify paper/literature-v4
	$(PYTHON) run_manuscript.py --verify paper/manuscript-v5
	$(PYTHON) run_submission_readiness.py --verify paper/submission-readiness-v3
	$(PYTHON) run_aei_submission.py --verify paper/aei-submission-v5

evidence-verify:
	$(PYTHON) run_confirmatory_assembly.py --verify data/results/assembly-robustness-confirmatory-v3
	$(PYTHON) run_replayable_proof_study.py --verify data/results/replayable-negative-proofs-v3
	$(PYTHON) run_repeated_selection.py --verify data/results/repeated-selection-v1
	$(PYTHON) run_planetary_baseline.py --verify data/results/planetary-baseline-v3
	$(PYTHON) run_scientific_manifest.py --verify data/results/aei-release-provenance-v4

release-verify: test paper-verify evidence-verify
	$(PYTHON) run_clean_environment_attestation.py --verify data/results/clean-environment-v3
