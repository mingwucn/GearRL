import json

import pytest

from benchmark.freeze import BenchmarkFreezer


def test_freeze_benchmark_writes_hashed_immutable_index(tmp_path) -> None:
    freezer = BenchmarkFreezer()
    index_path = freezer.freeze(tmp_path / "benchmark", 7, 2, 1)
    index = json.loads(index_path.read_text())
    assert index["instance_count"] == 3
    assert len(index["instances"]) == 3
    assert all(len(record["sha256"]) == 64 for record in index["instances"])
    with pytest.raises(FileExistsError):
        freezer.freeze(index_path.parent, 7, 2, 1)
