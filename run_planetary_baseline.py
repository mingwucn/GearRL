#!/usr/bin/env python3
"""Run selected frozen seeds for the published planetary baseline."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmark.planetary_external import PublishedPlanetaryGearBrief
from evaluation.planetary_baseline import PlanetaryBaselineEvidenceStore, PlanetaryBaselineProtocolLoader, PlanetaryDifferentialEvolutionBaseline


class PlanetaryBaselineCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--protocol", type=Path)
        parser.add_argument("--output", type=Path)
        parser.add_argument("--seed-offset", type=int, default=0)
        parser.add_argument("--seed-count", type=int)
        parser.add_argument("--verify", type=Path)
        args = parser.parse_args()
        store = PlanetaryBaselineEvidenceStore()
        if args.verify:
            print(store.verify(args.verify))
            return
        if args.protocol is None or args.output is None:
            parser.error("--protocol and --output are required")
        protocol = PlanetaryBaselineProtocolLoader().load(args.protocol)
        seeds = protocol.seeds[args.seed_offset:None if args.seed_count is None else args.seed_offset + args.seed_count]
        solver = PlanetaryDifferentialEvolutionBaseline()
        results = tuple(solver.solve(PublishedPlanetaryGearBrief(), protocol, seed) for seed in seeds)
        print(store.write(protocol, results, args.protocol, args.output))


if __name__ == "__main__":
    PlanetaryBaselineCommand().run()
