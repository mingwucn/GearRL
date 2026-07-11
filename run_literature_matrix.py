#!/usr/bin/env python3
"""Build or verify the AEI closest-method matrix."""

from __future__ import annotations

import argparse
from pathlib import Path

from reporting.literature_matrix import LiteratureArtifactStore


class LiteratureMatrixCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser(description=__doc__)
        action = parser.add_mutually_exclusive_group(required=True)
        action.add_argument("--output", type=Path)
        action.add_argument("--verify", type=Path)
        parser.add_argument("--source", type=Path, default=Path("literature/aei_closest_methods.json"))
        arguments = parser.parse_args()
        store = LiteratureArtifactStore()
        if arguments.output:
            print(store.build(arguments.source, arguments.output))
        else:
            store.verify_reproduction(arguments.verify)
            print(f"Verified byte-identical literature artifact: {arguments.verify}")


if __name__ == "__main__":
    LiteratureMatrixCommand().run()
