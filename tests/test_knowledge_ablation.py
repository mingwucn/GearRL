import json
from pathlib import Path

from evaluation.knowledge_ablation import KnowledgeAblationEvidenceStore, KnowledgeAblationProtocolLoader, KnowledgeAblationStudy


PROTOCOL = Path("data/protocols/aei-knowledge-ablation-v1.json")
INPUTS = Path("data/benchmark/curated/requirements-first-50-v2/solver-inputs")


def test_knowledge_ablation_distinguishes_semantics_from_container_choice(tmp_path: Path) -> None:
    protocol = KnowledgeAblationProtocolLoader().load(PROTOCOL)
    summary = KnowledgeAblationStudy().run(INPUTS, protocol)
    by_id = {item["adapter_id"]: item for item in summary["results"]}
    assert all(item["competency_accuracy"] == 1.0 for item in summary["results"])
    assert by_id["typed-executable-graph"]["semantic_mutation_detection_rate"] == 1.0
    assert by_id["flat-structural-record"]["semantic_mutation_detection_rate"] == 0.0
    assert by_id["flat-duplicated-semantic-rules"]["semantic_mutation_detection_rate"] == 1.0
    assert all(item["supported"] for item in summary["hypotheses"].values())
    root = tmp_path / "evidence"
    KnowledgeAblationEvidenceStore().write(summary, PROTOCOL, root)
    assert KnowledgeAblationEvidenceStore().verify(root)["schema_version"] == "aei-knowledge-ablation-artifact-v1"


def test_knowledge_ablation_store_rejects_tampering(tmp_path: Path) -> None:
    protocol = KnowledgeAblationProtocolLoader().load(PROTOCOL)
    summary = KnowledgeAblationStudy().run(INPUTS, protocol)
    root = tmp_path / "evidence"
    KnowledgeAblationEvidenceStore().write(summary, PROTOCOL, root)
    (root / "summary.json").write_text(json.dumps(summary))
    try:
        KnowledgeAblationEvidenceStore().verify(root)
    except ValueError as error:
        assert "summary hash mismatch" in str(error)
    else:
        raise AssertionError("Tampered summary was accepted")
