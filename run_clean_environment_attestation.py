"""Create or verify an independent clean-prefix attestation."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess

from reproducibility.clean_environment import CleanEnvironmentAttestationPolicy, CleanEnvironmentAttestor, CleanEnvironmentConfig, CleanEnvironmentEvidenceStore


class CondaExecutableResolver:
    """Resolve Conda without binding the release workflow to one workstation."""

    def resolve(self, explicit: Path | None) -> Path:
        candidate = str(explicit) if explicit else os.environ.get("CONDA_EXE") or shutil.which("conda")
        if not candidate:
            raise FileNotFoundError("Conda is unavailable; pass --conda-executable or set CONDA_EXE")
        path = Path(candidate).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Conda executable does not exist: {path}")
        return path


class CleanEnvironmentAttestationCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--prefix", type=Path, default=Path("/tmp/gearrl-clean-ai"))
        parser.add_argument("--conda-executable", type=Path)
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
                    Path("paper/submission-readiness-v3/report.json"),
                    Path("paper/submission-readiness-v3/manifest.json"),
                ),
            ).validate(report)
            print(f"Verified clean environment at commit {report['source_commit']}: {args.verify}")
            return
        if not args.output:
            parser.error("--output is required unless --verify is used")
        commit = subprocess.run(["git", "rev-parse", "HEAD"], text=True, capture_output=True, check=True).stdout.strip()
        conda = CondaExecutableResolver().resolve(args.conda_executable)
        config = CleanEnvironmentConfig(commit, conda, args.prefix, Path("environment-ai.lock").resolve(), Path("requirements-ai-pip.txt").resolve())
        report = CleanEnvironmentAttestor().run(config, Path.cwd())
        store.write(report, args.output)


if __name__ == "__main__":
    CleanEnvironmentAttestationCommand().run()
