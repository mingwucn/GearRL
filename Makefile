.PHONY: test paper-verify

PYTHON ?= python

test:
	$(PYTHON) -m pytest -q

paper-verify:
	$(PYTHON) run_publication_artifacts.py --verify paper/generated-v1
	$(PYTHON) run_literature_matrix.py --verify paper/literature-v1
	$(PYTHON) run_manuscript.py --verify paper/manuscript-v1
	$(PYTHON) run_submission_readiness.py --verify paper/submission-readiness-v1
	$(PYTHON) run_aei_submission.py --verify paper/aei-submission-v1
	$(PYTHON) run_clean_environment_attestation.py --verify data/results/clean-environment-v1
	$(PYTHON) run_assembly_robustness.py --verify data/results/assembly-robustness-v1
	$(PYTHON) run_assembly_robustness.py --verify data/results/assembly-robustness-confirmatory-v2
