.PHONY: test paper-verify

PYTHON ?= python

test:
	$(PYTHON) -m pytest -q

paper-verify:
	$(PYTHON) run_publication_artifacts.py --verify paper/generated-v1
	$(PYTHON) run_literature_matrix.py --verify paper/literature-v1
	$(PYTHON) run_manuscript.py --verify paper/manuscript-v1
