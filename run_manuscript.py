#!/usr/bin/env python3
"""Build or verify the claim-guarded AEI manuscript draft."""

from __future__ import annotations

import argparse
from pathlib import Path

from reporting.manuscript import ManuscriptArtifactStore


class ManuscriptCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser(description=__doc__)
        action = parser.add_mutually_exclusive_group(required=True)
        action.add_argument("--output", type=Path)
        action.add_argument("--verify", type=Path)
        arguments = parser.parse_args()
        store = ManuscriptArtifactStore()
        if arguments.output:
            print(store.build(
                Path("paper/manuscript_source.json"),
                Path("literature/aei_closest_methods.json"),
                Path("paper/generated-v2"),
                arguments.output,
            ))
        else:
            store.verify_reproduction(arguments.verify)
            print(f"Verified byte-identical manuscript artifact: {arguments.verify}")


if __name__ == "__main__":
    ManuscriptCommand().run()
