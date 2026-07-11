#!/usr/bin/env python3
"""Build or verify the shared AEI scientific artifact manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from reproducibility.scientific_manifest import ScientificArtifactManifestBuilder, ScientificArtifactManifestStore


class ScientificManifestCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--catalog", type=Path, default=Path("data/protocols/aei-release-artifacts-v1.json"))
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--output", type=Path)
        target.add_argument("--verify", type=Path)
        arguments = parser.parse_args()
        store = ScientificArtifactManifestStore()
        if arguments.verify:
            print(store.verify(arguments.verify, Path.cwd()).release_id)
            return
        manifest = ScientificArtifactManifestBuilder().build(arguments.catalog, Path.cwd())
        print(store.write(manifest, arguments.catalog, arguments.output))


if __name__ == "__main__":
    ScientificManifestCommand().run()
