#!/usr/bin/env python3
"""Build or verify replayable negative proofs for the curated benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.replayable_proofs import ReplayableProofEvidenceStore, ReplayableProofStudy


class ReplayableProofCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--dataset", type=Path, default=Path("data/benchmark/curated/requirements-first-50-v2"))
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--output", type=Path)
        target.add_argument("--verify", type=Path)
        arguments = parser.parse_args()
        store = ReplayableProofEvidenceStore()
        if arguments.verify:
            print(store.verify(arguments.verify))
            return
        summary = ReplayableProofStudy().run(arguments.dataset)
        print(store.write(summary, arguments.dataset, arguments.output))


if __name__ == "__main__":
    ReplayableProofCommand().run()
