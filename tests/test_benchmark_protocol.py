"""Verification for the frozen 400-instance benchmark protocol."""

import json

from benchmark.freeze import BenchmarkFreezer
from benchmark.protocol import BenchmarkProtocol, FrozenBenchmarkFactory


def test_protocol_has_disjoint_partitions_and_certificate_backed_adversarial_cases() -> None:
    instances = FrozenBenchmarkFactory().generate(BenchmarkProtocol())
    assert len(instances) == 400
    assert len({item.instance_id for item in instances}) == 400
    assert {item.partition for item in instances} == {"train", "validation", "test"}
    assert {item.difficulty for item in instances if item.partition != "test" or "procedural" in item.instance_id} == {"easy", "moderate", "hard"}
    assert sum(item.expected_feasible for item in instances) == 300
    assert all(item.certificate["valid"] for item in instances if item.expected_feasible)
    assert all(not item.certificate["valid"] for item in instances if not item.expected_feasible)


def test_freezer_persists_protocol_metadata(tmp_path) -> None:
    index_path = BenchmarkFreezer().freeze_protocol(tmp_path / "frozen")
    index = json.loads(index_path.read_text())
    assert index["dataset_id"] == "compound-v1-frozen-400"
    assert index["instance_count"] == 400
