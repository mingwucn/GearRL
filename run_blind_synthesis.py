"""Run requirements-first synthesis with only the solver-input directory mounted."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmark import SolverInputDirectoryLoader
from evaluation.blind_synthesis import BlindPredictionStore, BlindSynthesisExperiment
from synthesis import EnumerativeCompoundSynthesizer, ProductionCandidateValidator


class BlindSynthesisCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("solver_inputs", type=Path)
        parser.add_argument("predictions", type=Path)
        arguments = parser.parse_args()
        views = SolverInputDirectoryLoader().load(arguments.solver_inputs)
        solver = EnumerativeCompoundSynthesizer(ProductionCandidateValidator())
        predictions = BlindSynthesisExperiment(solver).run(views)
        print(BlindPredictionStore().write(predictions, arguments.predictions))


if __name__ == "__main__":
    BlindSynthesisCommand().run()
