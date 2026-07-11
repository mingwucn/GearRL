"""Immutable experiment-bundle metadata for reproducible GearRL results."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import uuid
from hashlib import sha256
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    created_at_utc: str
    git_commit: str | None
    git_dirty: bool | None
    python_version: str
    platform: str
    random_seed: int
    dataset_id: str
    dataset_hash: str
    config: dict[str, Any]
    model_version: str
    environment_hash: str | None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def create_run_bundle(
    root: str | Path,
    *,
    random_seed: int,
    dataset_id: str,
    dataset_hash: str,
    config: Mapping[str, Any],
    model_version: str,
    repository_root: str | Path = ".",
    environment_file: str | Path | None = None,
) -> tuple[Path, RunManifest]:
    """Create a write-once experiment directory and its manifest.

    Callers write raw per-instance records beneath the returned directory.  A
    second call can never overwrite an existing bundle because every run gets a
    UUID-backed directory name.
    """

    run_id = str(uuid.uuid4())
    bundle = Path(root) / run_id
    bundle.mkdir(parents=True, exist_ok=False)
    commit, dirty = _git_state(Path(repository_root))
    manifest = RunManifest(
        run_id=run_id,
        created_at_utc=datetime.now(UTC).isoformat(),
        git_commit=commit,
        git_dirty=dirty,
        python_version=sys.version,
        platform=platform.platform(),
        random_seed=random_seed,
        dataset_id=dataset_id,
        dataset_hash=dataset_hash,
        config=dict(config),
        model_version=model_version,
        environment_hash=_file_hash(Path(environment_file)) if environment_file else None,
    )
    (bundle / "manifest.json").write_text(json.dumps(manifest.to_json(), indent=2, sort_keys=True) + "\n")
    (bundle / "results").mkdir()
    return bundle, manifest


def write_result(bundle: str | Path, instance_id: str, result: Mapping[str, Any]) -> Path:
    """Atomically store one raw per-instance result under an existing bundle."""

    if not instance_id or "/" in instance_id or ".." in instance_id:
        raise ValueError("instance_id must be a simple identifier")
    result_dir = Path(bundle) / "results"
    if not result_dir.is_dir():
        raise ValueError("bundle does not contain a results directory")
    destination = result_dir / f"{instance_id}.json"
    if destination.exists():
        raise FileExistsError(f"Result already exists for {instance_id}")
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(dict(result), indent=2, sort_keys=True) + "\n")
    temporary.replace(destination)
    return destination


def _git_state(repository_root: Path) -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repository_root, check=True, capture_output=True, text=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"], cwd=repository_root, check=True, capture_output=True, text=True
            ).stdout.strip()
        )
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return None, None


def _file_hash(path: Path) -> str | None:
    try:
        return sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None
