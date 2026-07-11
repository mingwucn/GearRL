.PHONY: test paper-verify

PYTHON ?= python

test:
	$(PYTHON) -m pytest -q

paper-verify:
	$(PYTHON) run_publication_artifacts.py --verify paper/generated-v1
