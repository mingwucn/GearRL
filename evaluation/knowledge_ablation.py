"""AEI representation ablation for executable versus flat engineering knowledge."""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable

from benchmark.curated import SolverInputDirectoryLoader
from benchmark.specification import SolverBenchmarkView


@dataclass(frozen=True)
class KnowledgeAblationProtocol:
    study_id: str
    case_count: int
    competency_ids: tuple[str, ...]
    mutation_ids: tuple[str, ...]
    minimum_detection_advantage: float
    maximum_typed_rule_sites: int


class KnowledgeAblationProtocolLoader:
    def load(self, path: Path) -> KnowledgeAblationProtocol:
        payload = json.loads(path.read_text())
        if payload.get("schema_version") != "aei-knowledge-ablation-protocol-v1":
            raise ValueError("Unsupported knowledge-ablation protocol")
        return KnowledgeAblationProtocol(
            payload["study_id"],
            int(payload["case_count"]),
            tuple(payload["competency_questions"]),
            tuple(payload["semantic_mutations"]),
            float(payload["hypotheses"]["minimum_detection_advantage"]),
            int(payload["hypotheses"]["maximum_typed_rule_sites"]),
        )


@dataclass(frozen=True)
class ValidationTrace:
    accepted: bool
    localized_fields: tuple[str, ...]
    messages: tuple[str, ...]


class KnowledgeRepresentationAdapter(ABC):
    adapter_id: str
    semantic_rule_sites: int

    @abstractmethod
    def answer(self, payload: dict, competency_id: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def validate(self, payload: dict) -> ValidationTrace:
        raise NotImplementedError


class CompetencyResolver:
    """Shared question definitions; adapters differ only in representation access."""

    @staticmethod
    def flat(payload: dict, competency_id: str) -> Any:
        specification = payload["specification"]
        problem = specification["problem"]
        space = specification["design_space"]
        values = {
            "CQ-target-ratio": problem["constraints"]["target_speed_ratio"],
            "CQ-allowed-modules": tuple(space["allowed_modules_mm"]),
            "CQ-stage-bounds": (space["minimum_stage_count"], space["maximum_stage_count"]),
            "CQ-prescribed-roles": tuple(sorted(shaft["role"] for shaft in specification["prescribed_shafts"])),
            "CQ-obstacle-count": len(specification.get("obstacles", [])),
            "CQ-boundary-vertices": len(problem["boundary"]),
        }
        if competency_id not in values:
            raise KeyError(competency_id)
        return values[competency_id]

    @staticmethod
    def typed(view: SolverBenchmarkView, competency_id: str) -> Any:
        specification = view.specification
        values = {
            "CQ-target-ratio": specification.problem.constraints.target_speed_ratio,
            "CQ-allowed-modules": specification.design_space.allowed_modules_mm,
            "CQ-stage-bounds": (specification.design_space.minimum_stage_count, specification.design_space.maximum_stage_count),
            "CQ-prescribed-roles": tuple(sorted(shaft.role for shaft in specification.prescribed_shafts)),
            "CQ-obstacle-count": len(specification.obstacles),
            "CQ-boundary-vertices": len(specification.problem.boundary),
        }
        if competency_id not in values:
            raise KeyError(competency_id)
        return values[competency_id]


class TypedExecutableKnowledgeAdapter(KnowledgeRepresentationAdapter):
    adapter_id = "typed-executable-graph"
    semantic_rule_sites = 1
    _LOCALIZATION = {
        "unique": "specification.design_space.allowed_modules_mm",
        "stage-count": "specification.design_space.stage_count_bounds",
        "input and one output": "specification.prescribed_shafts.roles",
        "ratio_tolerance": "specification.problem.constraints.ratio_tolerance",
        "boundary_clearance": "specification.problem.constraints.boundary_clearance",
        "axial_layer_count": "specification.design_space.axial_layer_count",
        "polygon": "specification.obstacles",
    }

    def answer(self, payload: dict, competency_id: str) -> Any:
        return CompetencyResolver.typed(SolverBenchmarkView.from_json(payload), competency_id)

    def validate(self, payload: dict) -> ValidationTrace:
        try:
            SolverBenchmarkView.from_json(payload)
            return ValidationTrace(True, (), ())
        except (KeyError, TypeError, ValueError) as error:
            message = str(error)
            fields = tuple(field for marker, field in self._LOCALIZATION.items() if marker in message)
            return ValidationTrace(False, fields, (message,))


class FlatStructuralKnowledgeAdapter(KnowledgeRepresentationAdapter):
    adapter_id = "flat-structural-record"
    semantic_rule_sites = 0

    def answer(self, payload: dict, competency_id: str) -> Any:
        return CompetencyResolver.flat(payload, competency_id)

    def validate(self, payload: dict) -> ValidationTrace:
        required = ("instance_id", "family", "partition", "specification")
        missing = tuple(field for field in required if field not in payload)
        if missing:
            return ValidationTrace(False, missing, ("Missing required structural fields",))
        return ValidationTrace(True, (), ())


class FlatSemanticKnowledgeAdapter(FlatStructuralKnowledgeAdapter):
    adapter_id = "flat-duplicated-semantic-rules"
    semantic_rule_sites = 7

    def validate(self, payload: dict) -> ValidationTrace:
        structural = super().validate(payload)
        if not structural.accepted:
            return structural
        specification = payload["specification"]
        space = specification["design_space"]
        constraints = specification["problem"]["constraints"]
        issues = []
        modules = space["allowed_modules_mm"]
        if len(modules) != len(set(modules)):
            issues.append("specification.design_space.allowed_modules_mm")
        if space["minimum_stage_count"] > space["maximum_stage_count"]:
            issues.append("specification.design_space.stage_count_bounds")
        if sorted(shaft["role"] for shaft in specification["prescribed_shafts"]) != ["input", "output"]:
            issues.append("specification.prescribed_shafts.roles")
        if constraints["ratio_tolerance"] < 0:
            issues.append("specification.problem.constraints.ratio_tolerance")
        if constraints["boundary_clearance"] < 0:
            issues.append("specification.problem.constraints.boundary_clearance")
        if space["axial_layer_count"] < 1:
            issues.append("specification.design_space.axial_layer_count")
        if any(len(obstacle) < 3 for obstacle in specification.get("obstacles", [])):
            issues.append("specification.obstacles")
        return ValidationTrace(not issues, tuple(issues), tuple(f"Semantic violation: {field}" for field in issues))


@dataclass(frozen=True)
class SemanticMutation:
    mutation_id: str
    expected_field: str
    apply: Callable[[dict], None]


class SemanticMutationCatalog:
    def mutations(self) -> tuple[SemanticMutation, ...]:
        def duplicate_module(value):
            space = value["specification"]["design_space"]
            modules = space["allowed_modules_mm"]
            space["allowed_modules_mm"] = (*modules, modules[0])

        def reverse_stage_bounds(value):
            space = value["specification"]["design_space"]
            space["minimum_stage_count"] = space["maximum_stage_count"] + 1

        def duplicate_role(value):
            value["specification"]["prescribed_shafts"][1]["role"] = "input"

        def negative_ratio_tolerance(value):
            value["specification"]["problem"]["constraints"]["ratio_tolerance"] = -1.0

        def negative_boundary_clearance(value):
            value["specification"]["problem"]["constraints"]["boundary_clearance"] = -1.0

        def zero_axial_layers(value):
            value["specification"]["design_space"]["axial_layer_count"] = 0

        def short_obstacle(value):
            value["specification"]["obstacles"] = [[{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 0.0}]]

        return (
            SemanticMutation("M-duplicate-module", "specification.design_space.allowed_modules_mm", duplicate_module),
            SemanticMutation("M-reversed-stage-bounds", "specification.design_space.stage_count_bounds", reverse_stage_bounds),
            SemanticMutation("M-duplicate-shaft-role", "specification.prescribed_shafts.roles", duplicate_role),
            SemanticMutation("M-negative-ratio-tolerance", "specification.problem.constraints.ratio_tolerance", negative_ratio_tolerance),
            SemanticMutation("M-negative-boundary-clearance", "specification.problem.constraints.boundary_clearance", negative_boundary_clearance),
            SemanticMutation("M-zero-axial-layers", "specification.design_space.axial_layer_count", zero_axial_layers),
            SemanticMutation("M-short-obstacle", "specification.obstacles", short_obstacle),
        )


class KnowledgeAblationStudy:
    def __init__(self, adapters: tuple[KnowledgeRepresentationAdapter, ...] | None = None) -> None:
        self._adapters = adapters or (
            TypedExecutableKnowledgeAdapter(),
            FlatStructuralKnowledgeAdapter(),
            FlatSemanticKnowledgeAdapter(),
        )
        self._mutations = SemanticMutationCatalog().mutations()

    def run(self, solver_inputs: Path, protocol: KnowledgeAblationProtocol) -> dict:
        views = SolverInputDirectoryLoader().load(solver_inputs)[: protocol.case_count]
        if len(views) != protocol.case_count:
            raise ValueError("Knowledge-ablation case count mismatch")
        if tuple(mutation.mutation_id for mutation in self._mutations) != protocol.mutation_ids:
            raise ValueError("Knowledge-ablation mutation catalog drift")
        results = []
        for adapter in self._adapters:
            competency_correct = 0
            mutation_detected = 0
            mutation_localized = 0
            for view in views:
                payload = view.to_json()
                for competency_id in protocol.competency_ids:
                    expected = CompetencyResolver.flat(payload, competency_id)
                    competency_correct += int(adapter.answer(deepcopy(payload), competency_id) == expected)
                for mutation in self._mutations:
                    changed = deepcopy(payload)
                    mutation.apply(changed)
                    trace = adapter.validate(changed)
                    mutation_detected += int(not trace.accepted)
                    mutation_localized += int(mutation.expected_field in trace.localized_fields)
            competency_total = len(views) * len(protocol.competency_ids)
            mutation_total = len(views) * len(self._mutations)
            results.append({
                "adapter_id": adapter.adapter_id,
                "case_count": len(views),
                "competency_accuracy": competency_correct / competency_total,
                "semantic_mutation_detection_rate": mutation_detected / mutation_total,
                "exact_localization_rate": mutation_localized / mutation_total,
                "semantic_rule_sites": adapter.semantic_rule_sites,
            })
        by_id = {result["adapter_id"]: result for result in results}
        typed = by_id["typed-executable-graph"]
        structural = by_id["flat-structural-record"]
        semantic = by_id["flat-duplicated-semantic-rules"]
        return {
            "schema_version": "aei-knowledge-ablation-summary-v1",
            "study_id": protocol.study_id,
            "protocol": asdict(protocol),
            "results": results,
            "hypotheses": {
                "H1-competency-parity": {
                    "supported": typed["competency_accuracy"] == semantic["competency_accuracy"] == 1.0,
                    "interpretation": "Representation choice did not change answers to the frozen competency questions.",
                },
                "H2-early-semantic-detection": {
                    "advantage_over_structural_flat": typed["semantic_mutation_detection_rate"] - structural["semantic_mutation_detection_rate"],
                    "supported": typed["semantic_mutation_detection_rate"] - structural["semantic_mutation_detection_rate"] >= protocol.minimum_detection_advantage,
                },
                "H3-equivalent-semantics": {
                    "supported": typed["semantic_mutation_detection_rate"] == semantic["semantic_mutation_detection_rate"],
                    "interpretation": "Equivalent duplicated flat rules can match typed detection; the tested contribution is executable semantics and centralization, not graph superiority by itself.",
                },
                "H4-rule-centralization": {
                    "supported": typed["semantic_rule_sites"] <= protocol.maximum_typed_rule_sites and typed["semantic_rule_sites"] < semantic["semantic_rule_sites"],
                    "interpretation": "The typed adapter reused one canonical construction boundary while the semantic flat baseline duplicated seven cross-field rule sites.",
                },
            },
            "scope": "Authored representation ablation on frozen solver briefs; no human authoring-time or industrial adoption claim.",
        }


class KnowledgeAblationEvidenceStore:
    @staticmethod
    def _encode(payload: dict) -> bytes:
        return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()

    def write(self, summary: dict, protocol_source: Path, destination: Path) -> Path:
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Knowledge-ablation destination must be empty")
        destination.mkdir(parents=True, exist_ok=True)
        summary_bytes = self._encode(summary)
        (destination / "summary.json").write_bytes(summary_bytes)
        manifest = {
            "schema_version": "aei-knowledge-ablation-artifact-v1",
            "protocol_source": str(protocol_source),
            "protocol_sha256": sha256(protocol_source.read_bytes()).hexdigest(),
            "summary_sha256": sha256(summary_bytes).hexdigest(),
        }
        path = destination / "manifest.json"
        path.write_bytes(self._encode(manifest))
        return path

    def verify(self, destination: Path) -> dict:
        manifest = json.loads((destination / "manifest.json").read_text())
        if sha256((destination / "summary.json").read_bytes()).hexdigest() != manifest["summary_sha256"]:
            raise ValueError("Knowledge-ablation summary hash mismatch")
        protocol = Path(manifest["protocol_source"])
        if sha256(protocol.read_bytes()).hexdigest() != manifest["protocol_sha256"]:
            raise ValueError("Knowledge-ablation protocol hash mismatch")
        return manifest
