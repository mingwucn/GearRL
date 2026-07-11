"""Create or verify an independent clean-prefix attestation."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

from reproducibility.clean_environment import CleanEnvironmentAttestationPolicy, CleanEnvironmentAttestor, CleanEnvironmentConfig, CleanEnvironmentEvidenceStore


class CleanEnvironmentAttestationCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--prefix", type=Path, default=Path("/tmp/gearrl-clean-ai"))
        parser.add_argument("--output", type=Path)
        parser.add_argument("--verify", type=Path)
        args = parser.parse_args()
        store = CleanEnvironmentEvidenceStore()
        if args.verify:
            report = store.verify(args.verify)
            destination = args.verify.resolve().relative_to(Path.cwd().resolve())
            CleanEnvironmentAttestationPolicy(
                Path.cwd(),
                Path("environment-ai.lock"),
                Path("requirements-ai-pip.txt"),
                (
                    destination / "report.json",
                    destination / "manifest.json",
                    Path("paper/submission-readiness-v2/report.json"),
                    Path("paper/submission-readiness-v2/manifest.json"),
                ),
            ).validate(report)
            print(f"Verified clean environment at commit {report['source_commit']}: {args.verify}")
            return
        if not args.output:
            parser.error("--output is required unless --verify is used")
        commit = subprocess.run(["git", "rev-parse", "HEAD"], text=True, capture_output=True, check=True).stdout.strip()
        config = CleanEnvironmentConfig(commit, Path("/home/mingwucn/miniconda3/bin/conda"), args.prefix, Path("environment-ai.lock").resolve(), Path("requirements-ai-pip.txt").resolve())
        report = CleanEnvironmentAttestor().run(config, Path.cwd())
        store.write(report, args.output)


if __name__ == "__main__":
    CleanEnvironmentAttestationCommand().run()
