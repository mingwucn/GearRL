from dataclasses import replace
import gzip
from hashlib import sha256
import json
from pathlib import Path

import pytest

from evaluation.confirmatory_assembly import ConfirmatoryAssemblyEvidenceVerifier, ConfirmatoryAssemblyProtocolLoader, ConfirmatoryAssemblyStudy


PROTOCOL = Path("data/protocols/assembly-robustness-confirmatory-v3.json")
DATASET = Path("data/benchmark/frozen/compound-v1-frozen-400-r2")


class FixedSourceCommit:
    def capture(self, _repository: Path) -> str:
        return "test-commit"


def test_small_confirmatory_study_streams_raw_draws_and_primary_inference(tmp_path: Path) -> None:
    declared = ConfirmatoryAssemblyProtocolLoader().load(PROTOCOL)
    protocol = replace(declared, scramble_replicates=4, draws_per_replicate=2)
    root = tmp_path / "evidence"
    temporary_protocol = tmp_path / "protocol.json"
    payload = json.loads(PROTOCOL.read_text())
    payload["computation"]["scramble_replicates"] = 4
    payload["computation"]["draws_per_replicate"] = 2
    payload["computation"]["declared_total_draws"] = 7680
    temporary_protocol.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    protocol = ConfirmatoryAssemblyProtocolLoader().load(temporary_protocol)
    ConfirmatoryAssemblyStudy(FixedSourceCommit()).run(DATASET, protocol, temporary_protocol, root)
    summary = json.loads((root / "summary.json").read_text())
    manifest = json.loads((root / "manifest.json").read_text())
    with gzip.open(root / "draws.jsonl.gz", "rt") as source:
        lines = list(source)
    assert summary["layout_count"] == 120
    assert summary["scenario_count"] == 8
    assert summary["draw_count"] == 7680
    assert len(lines) == 7680
    assert manifest["draw_count"] == 7680
    assert set(summary["primary_inference"]) == {"familywise_alpha", "interaction", "housing_equivalence"}
    assert ConfirmatoryAssemblyEvidenceVerifier().verify(root) == manifest

    raw_path = root / "draws.jsonl.gz"
    original_raw = raw_path.read_bytes()
    first = json.loads(lines[0])
    first["valid"] = not first["valid"]
    first["failure_codes"] = [] if first["valid"] else ["coordinated-corruption"]
    lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":")) + "\n"
    with raw_path.open("wb") as target:
        with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed:
            compressed.write("".join(lines).encode())
    manifest["draws_sha256"] = sha256(raw_path.read_bytes()).hexdigest()
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ValueError, match="modeled outcome replay mismatch"):
        ConfirmatoryAssemblyEvidenceVerifier().verify(root)
    raw_path.write_bytes(original_raw)
    manifest["draws_sha256"] = sha256(original_raw).hexdigest()

    summary["primary_inference"]["interaction"]["supported"] = not summary["primary_inference"]["interaction"]["supported"]
    summary_bytes = (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode()
    (root / "summary.json").write_bytes(summary_bytes)
    manifest["summary_sha256"] = sha256(summary_bytes).hexdigest()
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ValueError, match="semantic summary mismatch"):
        ConfirmatoryAssemblyEvidenceVerifier().verify(root)
