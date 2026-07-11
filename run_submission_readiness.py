"""Build or verify the frozen AEI submission-readiness assessment."""

from __future__ import annotations

import argparse
from pathlib import Path

from reporting.submission_readiness import SubmissionReadinessArtifactStore


class SubmissionReadinessCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--source", type=Path, default=Path("paper/submission_readiness_source.json"))
        destination = parser.add_mutually_exclusive_group(required=True)
        destination.add_argument("--output", type=Path)
        destination.add_argument("--verify", type=Path)
        args = parser.parse_args()
        store = SubmissionReadinessArtifactStore()
        if args.verify:
            store.verify_reproduction(args.verify)
            print(f"Verified byte-identical readiness artifact: {args.verify}")
        else:
            store.build(args.source, args.output)


if __name__ == "__main__":
    SubmissionReadinessCommand().run()
