"""Build or verify the editable AEI submission package."""

from __future__ import annotations

import argparse
from pathlib import Path

from reporting.aei_submission import AEISubmissionPackageStore


class AEISubmissionCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        destination = parser.add_mutually_exclusive_group(required=True)
        destination.add_argument("--output", type=Path)
        destination.add_argument("--verify", type=Path)
        args = parser.parse_args()
        store = AEISubmissionPackageStore()
        if args.verify:
            store.verify_reproduction(args.verify)
            print(f"Verified byte-identical AEI package: {args.verify}")
        else:
            store.build(Path("paper/manuscript_source.json"), Path("paper/aei_submission_source.json"), Path("literature/aei_closest_methods.json"), Path("paper/generated-v4"), args.output)


if __name__ == "__main__":
    AEISubmissionCommand().run()
