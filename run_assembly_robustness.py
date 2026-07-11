"""Run or verify the frozen joint assembly-robustness protocol."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.assembly_robustness import AssemblyRobustnessEvidenceStore, AssemblyRobustnessProtocol, AssemblyRobustnessStudy


class AssemblyRobustnessCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--dataset", type=Path, default=Path("data/benchmark/frozen/compound-v1-frozen-400-r2"))
        destination = parser.add_mutually_exclusive_group(required=True)
        destination.add_argument("--output", type=Path)
        destination.add_argument("--verify", type=Path)
        parser.add_argument("--sample-size", type=int, default=120)
        parser.add_argument("--draws", type=int, default=512)
        parser.add_argument("--bootstrap-samples", type=int, default=5000)
        args = parser.parse_args()
        store = AssemblyRobustnessEvidenceStore()
        if args.verify:
            manifest = store.verify(args.verify)
            print(f"Verified {manifest['draw_count']} assembly-robustness draws: {args.verify}")
            return
        protocol = AssemblyRobustnessProtocol(sample_size=args.sample_size, draws_per_layout=args.draws, bootstrap_samples=args.bootstrap_samples)
        summary, outcomes, _, _ = AssemblyRobustnessStudy().run(args.dataset, protocol)
        store.write(summary, outcomes, args.dataset / "index.json", args.output)


if __name__ == "__main__":
    AssemblyRobustnessCommand().run()
