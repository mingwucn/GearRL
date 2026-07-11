"""Adjudicate sealed blind predictions against evaluator-only evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmark import CuratedBenchmarkLoader
from evaluation.blind_synthesis import BlindAdjudicator


class BlindAdjudicationCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("dataset", type=Path)
        parser.add_argument("predictions", type=Path)
        parser.add_argument("report", type=Path)
        arguments = parser.parse_args()
        dataset = CuratedBenchmarkLoader().load(arguments.dataset)
        adjudicator = BlindAdjudicator()
        report = adjudicator.adjudicate(dataset, arguments.predictions)
        print(adjudicator.write(report, arguments.report))


if __name__ == "__main__":
    BlindAdjudicationCommand().run()
