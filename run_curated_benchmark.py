"""Build and freeze the requirements-first curated benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmark.curated import CuratedBenchmarkFreezer, CuratedRequirementsFirstFactory
from benchmark.oracle import ExactCompoundTrainOracle


class CuratedBenchmarkCommand:
    """Thin command object for the exact curated benchmark workflow."""

    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("output", type=Path)
        arguments = parser.parse_args()
        cases = CuratedRequirementsFirstFactory(ExactCompoundTrainOracle()).build()
        print(CuratedBenchmarkFreezer().freeze(cases, arguments.output))


if __name__ == "__main__":
    CuratedBenchmarkCommand().run()
