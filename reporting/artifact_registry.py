"""Deterministic publication tables bound to frozen scientific evidence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory


@dataclass(frozen=True)
class EvidenceSource:
    source_id: str
    path: Path

    def record(self) -> dict[str, str]:
        return {"source_id": self.source_id, "path": str(self.path), "sha256": sha256(self.path.read_bytes()).hexdigest()}


class PublicationTable(ABC):
    """Strategy contract for one evidence-derived manuscript table."""

    @property
    @abstractmethod
    def table_id(self) -> str:
        """Stable publication identifier."""

    @property
    @abstractmethod
    def sources(self) -> tuple[EvidenceSource, ...]:
        """Every frozen payload read by the renderer."""

    @abstractmethod
    def render(self) -> str:
        """Return deterministic Markdown derived only from sources."""

    @staticmethod
    def _json(path: Path) -> dict:
        return json.loads(path.read_text())


class SolverComparisonTable(PublicationTable):
    def __init__(self, source: Path):
        self._source = source

    @property
    def table_id(self) -> str:
        return "solver-comparison"

    @property
    def sources(self) -> tuple[EvidenceSource, ...]:
        return (EvidenceSource("requirements-comparison-adjudication-v2", self._source),)

    def render(self) -> str:
        payload = self._json(self._source)
        lines = [
            "| Method | Runs | Minimum accuracy | Median candidates | Median runtime (s) |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for method, values in sorted(payload["methods"].items()):
            lines.append(
                f"| {method} | {values['run_count']} | {values['accuracy_min']:.3f} | "
                f"{values['median_parameter_tuples_across_runs']:.1f} | {values['median_runtime_s_across_runs']:.6f} |"
            )
        return "\n".join(lines) + "\n"


class CAEVerificationTable(PublicationTable):
    def __init__(self, manifest: Path, summary: Path):
        self._manifest, self._summary = manifest, summary

    @property
    def table_id(self) -> str:
        return "cae-verification"

    @property
    def sources(self) -> tuple[EvidenceSource, ...]:
        return (
            EvidenceSource("cae-verification-v3-manifest", self._manifest),
            EvidenceSource("cae-verification-v3-summary", self._summary),
        )

    def render(self) -> str:
        summary = self._json(self._summary)
        labels = {
            "patch_passed": "Constant-stress patch test",
            "cantilever_converged": "Cantilever analytical convergence",
            "gear_tooth_convergence_passed": "Involute tooth mesh convergence",
            "gear_agreement_passed": "Independent root-stress agreement",
        }
        lines = ["| Verification gate | Result |", "| --- | ---: |"]
        lines.extend(f"| {label} | {'Pass' if summary[key] else 'Fail'} |" for key, label in labels.items())
        return "\n".join(lines) + "\n"


class LoadUncertaintyTable(PublicationTable):
    def __init__(self, manifest: Path, results: Path):
        self._manifest, self._results = manifest, results

    @property
    def table_id(self) -> str:
        return "load-uncertainty"

    @property
    def sources(self) -> tuple[EvidenceSource, ...]:
        return (
            EvidenceSource("load-uncertainty-v1-manifest", self._manifest),
            EvidenceSource("load-uncertainty-v1-results", self._results),
        )

    def render(self) -> str:
        materials = self._json(self._results)["materials"]
        lines = [
            "| Material condition | Layouts | Samples | Failure probability | Layout-bootstrap 95% CI | Torque ST | Width ST | Efficiency ST |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for material in materials:
            indices = {item["parameter"]: item["total_order"] for item in material["sensitivity"]}
            lower, upper = material["layout_bootstrap_ci95"]
            lines.append(
                f"| {material['material_name']} | {material['layout_count']} | {material['sample_count']} | "
                f"{material['pooled_failure_probability']:.3f} | [{lower:.3f}, {upper:.3f}] | "
                f"{indices['input_torque']:.3f} | {indices['face_width']:.3f} | {indices['per_mesh_efficiency']:.3f} |"
            )
        return "\n".join(lines) + "\n"


class StrengthCouplingTable(PublicationTable):
    def __init__(self, manifest: Path, summary: Path):
        self._manifest, self._summary = manifest, summary

    @property
    def table_id(self) -> str:
        return "strength-coupling"

    @property
    def sources(self) -> tuple[EvidenceSource, ...]:
        return (
            EvidenceSource("strength-coupled-v1-manifest", self._manifest),
            EvidenceSource("strength-coupled-v1-summary", self._summary),
        )

    def render(self) -> str:
        summary = self._json(self._summary)
        return (
            "| Cases | Baseline strength-admissible | Retained | Redesigned | Rejected by complete search |\n"
            "| ---: | ---: | ---: | ---: | ---: |\n"
            f"| {summary['case_count']} | {summary['baseline_strength_admissible_count']} | "
            f"{summary['retained_count']} | {summary['redesigned_count']} | {summary['rejected_count']} |\n"
        )


class PublicationArtifactRegistry:
    """Build a write-once table bundle with bidirectional hash traceability."""

    @staticmethod
    def _encode(value) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()

    def build(self, output: Path, tables: tuple[PublicationTable, ...], figures=()) -> Path:
        if output.exists() and any(output.iterdir()):
            raise FileExistsError("Publication artifact destination must be empty")
        if not tables or len({table.table_id for table in tables}) != len(tables):
            raise ValueError("Publication table IDs must be non-empty and unique")
        table_root = output / "tables"
        table_root.mkdir(parents=True, exist_ok=True)
        records = []
        for table in sorted(tables, key=lambda item: item.table_id):
            payload = table.render().encode()
            destination = table_root / f"{table.table_id}.md"
            destination.write_bytes(payload)
            records.append(
                {
                    "table_id": table.table_id,
                    "output": str(destination.relative_to(output)),
                    "output_sha256": sha256(payload).hexdigest(),
                    "sources": [source.record() for source in table.sources],
                }
            )
        figure_root = output / "figures"
        figure_root.mkdir(parents=True, exist_ok=True)
        figure_records = []
        if len({figure.figure_id for figure in figures}) != len(figures):
            raise ValueError("Publication figure IDs must be unique")
        for figure in sorted(figures, key=lambda item: item.figure_id):
            payload = figure.render()
            destination = figure_root / f"{figure.figure_id}.svg"
            destination.write_bytes(payload)
            figure_records.append(
                {
                    "figure_id": figure.figure_id,
                    "output": str(destination.relative_to(output)),
                    "output_sha256": sha256(payload).hexdigest(),
                    "sources": [source.record() for source in figure.sources],
                }
            )
        manifest = {
            "schema_version": "publication-artifact-registry-v2",
            "generation_policy": "deterministic evidence-only tables and figures; no manually supplied metrics",
            "tables": records,
            "figures": figure_records,
        }
        path = output / "registry.json"
        path.write_bytes(self._encode(manifest))
        return path

    def verify(self, root: Path) -> dict:
        registry = json.loads((root / "registry.json").read_text())
        if registry["schema_version"] != "publication-artifact-registry-v2":
            raise ValueError("Unsupported publication registry schema")
        for kind, records, identifier in (
            ("table", registry["tables"], "table_id"),
            ("figure", registry["figures"], "figure_id"),
        ):
            for record in records:
                output = root / record["output"]
                if sha256(output.read_bytes()).hexdigest() != record["output_sha256"]:
                    raise ValueError(f"Publication {kind} hash mismatch: {record[identifier]}")
                for source in record["sources"]:
                    if sha256(Path(source["path"]).read_bytes()).hexdigest() != source["sha256"]:
                        raise ValueError(f"Publication source hash mismatch: {source['source_id']}")
        return registry


class PublicationReproducer:
    """Regenerate a bundle and require byte identity with the frozen target."""

    def __init__(self, registry: PublicationArtifactRegistry):
        self._registry = registry

    def verify_reproduction(self, frozen: Path, tables: tuple[PublicationTable, ...], figures=()) -> None:
        self._registry.verify(frozen)
        with TemporaryDirectory(prefix="gearrl-paper-") as temporary:
            generated = Path(temporary)
            self._registry.build(generated, tables, figures)
            frozen_files = {path.relative_to(frozen): path.read_bytes() for path in frozen.rglob("*") if path.is_file()}
            generated_files = {path.relative_to(generated): path.read_bytes() for path in generated.rglob("*") if path.is_file()}
            if frozen_files != generated_files:
                raise ValueError("Regenerated publication artifacts are not byte-identical")
