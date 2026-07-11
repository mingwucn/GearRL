#!/usr/bin/env python3
"""Run the preregistered v3 confirmatory digital assembly study."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.confirmatory_assembly import ConfirmatoryAssemblyEvidenceVerifier, ConfirmatoryAssemblyProtocolLoader, ConfirmatoryAssemblyStudy


class ConfirmatoryAssemblyCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--dataset", type=Path)
        parser.add_argument("--protocol", type=Path)
        parser.add_argument("--output", type=Path)
        parser.add_argument("--verify", type=Path)
        args = parser.parse_args()
        if args.verify:
            print(ConfirmatoryAssemblyEvidenceVerifier().verify(args.verify))
            return
        if args.output is None or args.dataset is None or args.protocol is None:
            parser.error("--dataset, --protocol, and --output are required unless --verify is used")
        protocol = ConfirmatoryAssemblyProtocolLoader().load(args.protocol)
        print(ConfirmatoryAssemblyStudy().run(args.dataset, protocol, args.protocol, args.output))


if __name__ == "__main__":
    ConfirmatoryAssemblyCommand().run()
