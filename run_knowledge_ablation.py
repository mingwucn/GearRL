#!/usr/bin/env python3
"""Run or verify the frozen AEI engineering-knowledge ablation."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.knowledge_ablation import KnowledgeAblationEvidenceStore, KnowledgeAblationProtocolLoader, KnowledgeAblationStudy


class KnowledgeAblationCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--solver-inputs", type=Path)
        parser.add_argument("--protocol", type=Path)
        parser.add_argument("--output", type=Path)
        parser.add_argument("--verify", type=Path)
        args = parser.parse_args()
        store = KnowledgeAblationEvidenceStore()
        if args.verify:
            print(store.verify(args.verify))
            return
        if not all((args.solver_inputs, args.protocol, args.output)):
            parser.error("--solver-inputs, --protocol, and --output are required")
        protocol = KnowledgeAblationProtocolLoader().load(args.protocol)
        summary = KnowledgeAblationStudy().run(args.solver_inputs, protocol)
        print(store.write(summary, args.protocol, args.output))


if __name__ == "__main__":
    KnowledgeAblationCommand().run()
