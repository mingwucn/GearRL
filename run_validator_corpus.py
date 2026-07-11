"""Evaluate and freeze the 50-case analytical validator corpus."""

from __future__ import annotations

import argparse
from pathlib import Path

from physics_validator.corpus import ValidatorCaseCatalog, ValidatorCorpusFreezer, ValidatorCorpusRunner


class ValidatorCorpusCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("output", type=Path)
        arguments = parser.parse_args()
        records = ValidatorCorpusRunner().evaluate(ValidatorCaseCatalog().cases())
        print(ValidatorCorpusFreezer().freeze(records, arguments.output))


if __name__ == "__main__":
    ValidatorCorpusCommand().run()
