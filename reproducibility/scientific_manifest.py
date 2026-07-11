"""Shared aggregate provenance for submission-critical scientific artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess

from reproducibility.clean_environment import CommittedSourceTreeHasher


@dataclass(frozen=True)
class ScientificArtifactReference:
    artifact_id: str
    path: str
    sha256: str


@dataclass(frozen=True)
class ScientificEnvironmentIdentity:
    source_commit: str
    source_tree_sha256: str
    conda_lock_sha256: str
    pip_lock_sha256: str
    platform: str
    python_version: str


@dataclass(frozen=True)
class ScientificArtifactManifest:
    schema_version: str
    release_id: str
    model_scope: str
    environment: ScientificEnvironmentIdentity
    artifacts: tuple[ScientificArtifactReference, ...]

    def to_json(self) -> dict:
        return asdict(self)


class ScientificArtifactManifestBuilder:
    """Build one canonical release identity from a frozen artifact catalog."""

    SCHEMA_VERSION = "scientific-artifact-manifest-v1"

    def build(self, catalog_path: Path, repository: Path) -> ScientificArtifactManifest:
        repository = repository.resolve()
        catalog = json.loads(catalog_path.read_text())
        if catalog.get("schema_version") != "scientific-artifact-catalog-v1":
            raise ValueError("Unsupported scientific artifact catalog")
        commit = subprocess.run(("git", "rev-parse", "HEAD"), cwd=repository, text=True, capture_output=True, check=True).stdout.strip()
        references = []
        identifiers = set()
        for item in catalog["artifacts"]:
            identifier = str(item["artifact_id"])
            if identifier in identifiers:
                raise ValueError(f"Duplicate scientific artifact id: {identifier}")
            identifiers.add(identifier)
            relative = Path(item["path"])
            absolute = (repository / relative).resolve()
            if not absolute.is_relative_to(repository) or not absolute.is_file():
                raise ValueError(f"Scientific artifact path is invalid: {relative}")
            references.append(ScientificArtifactReference(identifier, relative.as_posix(), sha256(absolute.read_bytes()).hexdigest()))
        environment = ScientificEnvironmentIdentity(
            commit,
            CommittedSourceTreeHasher().digest(repository, commit),
            sha256((repository / "environment-ai.lock").read_bytes()).hexdigest(),
            sha256((repository / "requirements-ai-pip.txt").read_bytes()).hexdigest(),
            platform.platform(),
            platform.python_version(),
        )
        return ScientificArtifactManifest(
            self.SCHEMA_VERSION,
            catalog["release_id"],
            catalog["model_scope"],
            environment,
            tuple(references),
        )


class ScientificArtifactManifestStore:
    @staticmethod
    def _encode(payload: dict) -> bytes:
        return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()

    def write(self, manifest: ScientificArtifactManifest, catalog: Path, destination: Path) -> Path:
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Scientific manifest destination must be empty")
        destination.mkdir(parents=True, exist_ok=True)
        manifest_bytes = self._encode(manifest.to_json())
        (destination / "manifest.json").write_bytes(manifest_bytes)
        envelope = {
            "schema_version": "scientific-artifact-manifest-envelope-v1",
            "catalog": str(catalog),
            "catalog_sha256": sha256(catalog.read_bytes()).hexdigest(),
            "manifest_sha256": sha256(manifest_bytes).hexdigest(),
        }
        path = destination / "envelope.json"
        path.write_bytes(self._encode(envelope))
        return path

    def verify(self, destination: Path, repository: Path) -> ScientificArtifactManifest:
        repository = repository.resolve()
        envelope = json.loads((destination / "envelope.json").read_text())
        manifest_bytes = (destination / "manifest.json").read_bytes()
        if sha256(manifest_bytes).hexdigest() != envelope["manifest_sha256"]:
            raise ValueError("Scientific aggregate manifest hash mismatch")
        catalog = Path(envelope["catalog"])
        if sha256(catalog.read_bytes()).hexdigest() != envelope["catalog_sha256"]:
            raise ValueError("Scientific aggregate catalog hash mismatch")
        payload = json.loads(manifest_bytes)
        environment = ScientificEnvironmentIdentity(**payload["environment"])
        references = tuple(ScientificArtifactReference(**item) for item in payload["artifacts"])
        manifest = ScientificArtifactManifest(
            payload["schema_version"], payload["release_id"], payload["model_scope"], environment, references,
        )
        if len({item.artifact_id for item in references}) != len(references):
            raise ValueError("Scientific aggregate contains duplicate artifact ids")
        for item in references:
            path = (repository / item.path).resolve()
            if not path.is_relative_to(repository) or sha256(path.read_bytes()).hexdigest() != item.sha256:
                raise ValueError(f"Scientific aggregate artifact mismatch: {item.artifact_id}")
        if CommittedSourceTreeHasher().digest(repository, environment.source_commit) != environment.source_tree_sha256:
            raise ValueError("Scientific aggregate source tree mismatch")
        if sha256((repository / "environment-ai.lock").read_bytes()).hexdigest() != environment.conda_lock_sha256:
            raise ValueError("Scientific aggregate Conda lock mismatch")
        if sha256((repository / "requirements-ai-pip.txt").read_bytes()).hexdigest() != environment.pip_lock_sha256:
            raise ValueError("Scientific aggregate pip lock mismatch")
        return manifest
