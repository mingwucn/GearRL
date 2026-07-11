"""Claim-guarded assembly of the evidence-bound AEI manuscript draft."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory


@dataclass(frozen=True)
class ProhibitedClaim:
    phrase: str
    rationale: str


class ManuscriptClaimGuard:
    """Enforce the frozen claim register on manuscript prose."""

    REQUIRED_SCOPE = "valid under the declared kinematic, geometric, and static-strength model"
    PROHIBITED = (
        ProhibitedClaim("manufacturing-ready", "No production qualification exists"),
        ProhibitedClaim("fatigue-qualified", "The CAE model is static"),
        ProhibitedClaim("physically validated", "The selected AEI path is fully digital"),
        ProhibitedClaim("learning improves", "The requirements-first learning gate has not passed"),
        ProhibitedClaim("state-of-the-art", "No universal performance comparison exists"),
        ProhibitedClaim("first ever", "The literature audit cannot prove universal priority"),
        ProhibitedClaim("novel graph-based", "Graph-based engineering design is established prior art"),
    )

    def validate(self, text: str) -> None:
        lowered = text.lower()
        if self.REQUIRED_SCOPE not in lowered:
            raise ValueError("Manuscript is missing the mandatory modeled-validity scope")
        violations = [item.phrase for item in self.PROHIBITED if item.phrase in lowered]
        if violations:
            raise ValueError(f"Manuscript contains prohibited claims: {', '.join(violations)}")


class AEIManuscriptAssembler:
    """Compose prose, registered evidence assets, and DOI references."""

    def assemble(self, source: Path, literature: Path, publication_root: Path) -> str:
        manuscript = json.loads(source.read_text())
        if manuscript["schema_version"] != "aei-manuscript-source-v1":
            raise ValueError("Unsupported manuscript source schema")
        literature_payload = json.loads(literature.read_text())
        registry = json.loads((publication_root / "registry.json").read_text())
        tables = {item["table_id"]: publication_root / item["output"] for item in registry["tables"]}
        figures = {item["figure_id"]: publication_root / item["output"] for item in registry["figures"]}
        lines = [f"# {manuscript['title']}", "", f"## {manuscript['subtitle']}", "", "## Abstract", "", manuscript["abstract"], "", "**Keywords:** " + "; ".join(manuscript["keywords"]), ""]
        for section in manuscript["sections"]:
            lines.extend([f"## {section['title']}", ""])
            for paragraph in section["paragraphs"]:
                lines.extend([paragraph, ""])
            for table_id in section.get("tables", ()):
                if table_id not in tables:
                    raise ValueError(f"Unknown manuscript table: {table_id}")
                lines.extend([f"**Registered table: `{table_id}`**", "", tables[table_id].read_text().rstrip(), ""])
            for figure_id in section.get("figures", ()):
                if figure_id not in figures:
                    raise ValueError(f"Unknown manuscript figure: {figure_id}")
                relative = Path("../generated-v1") / figures[figure_id].relative_to(publication_root)
                lines.extend([f"![{figure_id}]({relative.as_posix()})", ""])
        lines.extend(["## References", ""])
        for index, method in enumerate(sorted(literature_payload["methods"], key=lambda item: (item["year"], item["id"])), 1):
            lines.append(f"{index}. {method['title']}. *{method['venue']}* ({method['year']}). https://doi.org/{method['doi']}")
        result = "\n".join(lines).rstrip() + "\n"
        ManuscriptClaimGuard().validate(result)
        return result


class ManuscriptArtifactStore:
    """Build and reproduce a manuscript bound to all directly read sources."""

    @staticmethod
    def _encode(value) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()

    def build(self, source: Path, literature: Path, publication_root: Path, output: Path) -> Path:
        if output.exists() and any(output.iterdir()):
            raise FileExistsError("Manuscript destination must be empty")
        output.mkdir(parents=True, exist_ok=True)
        text = AEIManuscriptAssembler().assemble(source, literature, publication_root).encode()
        manuscript_path = output / "GearRL_AEI_MANUSCRIPT.md"
        manuscript_path.write_bytes(text)
        registry_path = publication_root / "registry.json"
        manifest = {
            "schema_version": "aei-manuscript-artifact-v1",
            "source": str(source),
            "source_sha256": sha256(source.read_bytes()).hexdigest(),
            "literature": str(literature),
            "literature_sha256": sha256(literature.read_bytes()).hexdigest(),
            "publication_registry": str(registry_path),
            "publication_registry_sha256": sha256(registry_path.read_bytes()).hexdigest(),
            "manuscript_sha256": sha256(text).hexdigest(),
        }
        path = output / "manifest.json"
        path.write_bytes(self._encode(manifest))
        return path

    def verify(self, root: Path) -> dict:
        manifest = json.loads((root / "manifest.json").read_text())
        for key in ("source", "literature", "publication_registry"):
            if sha256(Path(manifest[key]).read_bytes()).hexdigest() != manifest[f"{key}_sha256"]:
                raise ValueError(f"Manuscript {key} hash mismatch")
        manuscript = (root / "GearRL_AEI_MANUSCRIPT.md").read_bytes()
        if sha256(manuscript).hexdigest() != manifest["manuscript_sha256"]:
            raise ValueError("Manuscript output hash mismatch")
        ManuscriptClaimGuard().validate(manuscript.decode())
        return manifest

    def verify_reproduction(self, frozen: Path) -> None:
        manifest = self.verify(frozen)
        with TemporaryDirectory(prefix="gearrl-manuscript-") as temporary:
            generated = Path(temporary)
            publication_root = Path(manifest["publication_registry"]).parent
            self.build(Path(manifest["source"]), Path(manifest["literature"]), publication_root, generated)
            frozen_files = {path.name: path.read_bytes() for path in frozen.iterdir() if path.is_file()}
            generated_files = {path.name: path.read_bytes() for path in generated.iterdir() if path.is_file()}
            if frozen_files != generated_files:
                raise ValueError("Regenerated manuscript is not byte-identical")
