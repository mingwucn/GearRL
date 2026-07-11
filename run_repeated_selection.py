#!/usr/bin/env python3
"""Run or verify outer-replicated tolerance-aware selection."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.repeated_selection import (
    RepeatedSelectionEvidenceStore,
    RepeatedSelectionProtocolLoader,
    RepeatedToleranceAwareSelectionStudy,
)


class RepeatedSelectionCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--dataset", type=Path)
        parser.add_argument("--protocol", type=Path)
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--output", type=Path)
        target.add_argument("--verify", type=Path)
        arguments = parser.parse_args()
        store = RepeatedSelectionEvidenceStore()
        if arguments.verify:
            print(store.verify(arguments.verify))
            return
        if arguments.dataset is None or arguments.protocol is None:
            parser.error("--dataset and --protocol are required with --output")
        protocol = RepeatedSelectionProtocolLoader().load(arguments.protocol)
        summary = RepeatedToleranceAwareSelectionStudy().run(arguments.dataset, protocol)
        print(store.write(summary, arguments.protocol, arguments.dataset, arguments.output))


if __name__ == "__main__":
    RepeatedSelectionCommand().run()
