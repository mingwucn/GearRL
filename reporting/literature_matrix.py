"""Validated, deterministic closest-method matrix and contribution claim register."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory


@dataclass(frozen=True)
class LiteratureMethod:
    id: str
    year: int
    title: str
    venue: str
    doi: str
    url: str
    knowledge_representation: str
    synthesis_scope: str
    validation_scope: str
    closest_overlap: str
    remaining_difference: str


@dataclass(frozen=True)
class ContributionClaim:
    claim_id: str
    status: str
    claim: str
    required_evidence: str


@dataclass(frozen=True)
class LiteratureEvidence:
    schema_version: str
    search_cutoff: str
    venue_scope: dict
    methods: tuple[LiteratureMethod, ...]
    claims: tuple[ContributionClaim, ...]


class LiteratureEvidenceLoader:
    """Fail closed on malformed, duplicate, or untraceable literature records."""

    def load(self, source: Path) -> LiteratureEvidence:
        payload = json.loads(source.read_text())
        if payload["schema_version"] != "aei-literature-matrix-v1":
            raise ValueError("Unsupported literature evidence schema")
        methods = tuple(LiteratureMethod(**item) for item in payload["methods"])
        claims = tuple(ContributionClaim(**item) for item in payload["claim_register"])
        if len(methods) < 8 or len({item.id for item in methods}) != len(methods):
            raise ValueError("Closest-method matrix requires at least eight unique records")
        if len({item.doi.lower() for item in methods}) != len(methods):
            raise ValueError("Closest-method DOI records must be unique")
        if any(not item.url.startswith("https://") or "/" not in item.doi for item in methods):
            raise ValueError("Every method requires a DOI and traceable HTTPS source")
        if len({item.claim_id for item in claims}) != len(claims):
            raise ValueError("Contribution claim IDs must be unique")
        if any(item.status not in {"supported", "candidate-novelty", "unsupported"} for item in claims):
            raise ValueError("Unsupported contribution-claim status")
        return LiteratureEvidence(
            payload["schema_version"], payload["search_cutoff"], payload["venue_scope"], methods, claims
        )


class LiteratureMatrixRenderer:
    """Render the review matrix without manually supplied summary metrics."""

    def render(self, evidence: LiteratureEvidence) -> str:
        lines = [
            "# AEI Closest-Method Matrix and Claim Register",
            "",
            f"Search cutoff: `{evidence.search_cutoff}`",
            "",
            "## Venue gate",
            "",
            f"[{evidence.venue_scope['title']}]({evidence.venue_scope['url']}): "
            f"{evidence.venue_scope['operational_requirement']}",
            "",
            "## Closest methods",
            "",
            "| Year | Method | Knowledge representation | Synthesis scope | Validation | Closest overlap | Remaining difference |",
            "| ---: | --- | --- | --- | --- | --- | --- |",
        ]
        for item in sorted(evidence.methods, key=lambda method: (-method.year, method.id)):
            method = f"[{item.title}]({item.url}) ({item.venue}; DOI `{item.doi}`)"
            cells = (
                str(item.year), method, item.knowledge_representation, item.synthesis_scope,
                item.validation_scope, item.closest_overlap, item.remaining_difference,
            )
            lines.append("| " + " | ".join(value.replace("|", "\\|") for value in cells) + " |")
        lines.extend(
            [
                "",
                "## Claim register",
                "",
                "| ID | Status | Permitted or prohibited claim | Evidence condition |",
                "| --- | --- | --- | --- |",
            ]
        )
        for claim in evidence.claims:
            lines.append(f"| {claim.claim_id} | {claim.status} | {claim.claim} | {claim.required_evidence} |")
        lines.extend(
            [
                "",
                "## Defensible contribution",
                "",
                "The literature does not support novelty claims for graph-based design, gear optimization, "
                "knowledge formalization, constrained learning, or simulation-coupled generation by themselves. "
                "The candidate contribution is the integration of an executable engineering-knowledge schema, "
                "blind requirements-first bounded synthesis, independent positive certificates and complete negative "
                "proofs, strength-coupled admission, and hash-bound reporting. The phrase `within the audited "
                "closest-method set` is mandatory because the matrix cannot prove a universal first.",
                "",
            ]
        )
        return "\n".join(lines)


class LiteratureArtifactStore:
    """Build and reproduce a hash-bound literature review artifact."""

    @staticmethod
    def _encode(value) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()

    def build(self, source: Path, output: Path) -> Path:
        if output.exists() and any(output.iterdir()):
            raise FileExistsError("Literature artifact destination must be empty")
        output.mkdir(parents=True, exist_ok=True)
        evidence = LiteratureEvidenceLoader().load(source)
        matrix_bytes = LiteratureMatrixRenderer().render(evidence).encode()
        (output / "AEI_CLOSEST_METHODS_MATRIX.md").write_bytes(matrix_bytes)
        manifest = {
            "schema_version": "aei-literature-artifact-v1",
            "source": str(source),
            "source_sha256": sha256(source.read_bytes()).hexdigest(),
            "matrix_sha256": sha256(matrix_bytes).hexdigest(),
            "method_count": len(evidence.methods),
            "claim_count": len(evidence.claims),
        }
        path = output / "manifest.json"
        path.write_bytes(self._encode(manifest))
        return path

    def verify(self, root: Path) -> dict:
        manifest = json.loads((root / "manifest.json").read_text())
        if sha256(Path(manifest["source"]).read_bytes()).hexdigest() != manifest["source_sha256"]:
            raise ValueError("Literature source hash mismatch")
        if sha256((root / "AEI_CLOSEST_METHODS_MATRIX.md").read_bytes()).hexdigest() != manifest["matrix_sha256"]:
            raise ValueError("Literature matrix hash mismatch")
        return manifest

    def verify_reproduction(self, frozen: Path) -> None:
        manifest = self.verify(frozen)
        with TemporaryDirectory(prefix="gearrl-literature-") as temporary:
            generated = Path(temporary)
            self.build(Path(manifest["source"]), generated)
            frozen_files = {path.name: path.read_bytes() for path in frozen.iterdir() if path.is_file()}
            generated_files = {path.name: path.read_bytes() for path in generated.iterdir() if path.is_file()}
            if frozen_files != generated_files:
                raise ValueError("Regenerated literature artifact is not byte-identical")
