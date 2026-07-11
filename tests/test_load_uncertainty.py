import json
from pathlib import Path

import numpy as np
import pytest

from evaluation.load_uncertainty import StaticLoadUncertaintyModel, ToothResponseSurface
from run_load_uncertainty_study import LoadUncertaintyCommand, LoadUncertaintyConfig, LoadUncertaintyEvidenceStore


def test_tooth_surface_obeys_linear_load_width_and_efficiency_scaling() -> None:
    surface = ToothResponseSurface(100.0, 200.0, 1.0, 10.0, 0.95, 2)
    samples = np.array([[1.0, 10.0, 0.95], [2.0, 5.0, 0.95], [1.0, 10.0, 0.98]])
    safety = surface.safety_factor(samples)
    assert safety[0] == pytest.approx(2.0)
    assert safety[1] == pytest.approx(0.5)
    assert safety[2] == pytest.approx(2.0 * (0.95 / 0.98) ** 2)


def test_uncertainty_ranges_are_explicit_and_bounded() -> None:
    transformed = StaticLoadUncertaintyModel().transform(np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]))
    assert transformed.tolist() == [[1.0, 8.0, 0.95], [3.0, 12.0, 0.98]]


def test_uncertainty_command_validates_direct_corners_and_freezes_results(tmp_path) -> None:
    root = tmp_path / "uncertainty"
    path = LoadUncertaintyCommand().run(
        Path("data/results/load-envelope-v1"), root, LoadUncertaintyConfig(sobol_exponent=4, bootstrap_samples=100)
    )
    manifest, results = LoadUncertaintyEvidenceStore().load(root)
    assert path == root / "manifest.json"
    assert "uniform operating ranges" in manifest["scope"]
    assert len(results["materials"]) == 2
    assert all(item["maximum_relative_error"] < 1e-10 for item in results["validation"].values())
    assert all(len(item["sensitivity"]) == 3 for item in results["materials"])
    for material in results["materials"]:
        assert len(material["layout_outcomes"]) == 24
        total_orders = {item["parameter"]: item["total_order"] for item in material["sensitivity"]}
        assert total_orders["input_torque"] > total_orders["face_width"] > total_orders["per_mesh_efficiency"]
        assert sum(total_orders.values()) > 0.9


def test_uncertainty_store_rejects_result_tampering(tmp_path) -> None:
    root = tmp_path / "uncertainty"
    LoadUncertaintyCommand().run(
        Path("data/results/load-envelope-v1"), root, LoadUncertaintyConfig(sobol_exponent=4, bootstrap_samples=100)
    )
    results = root / "results.json"
    results.write_text(json.dumps(json.loads(results.read_text())) + " ")
    with pytest.raises(ValueError, match="results hash mismatch"):
        LoadUncertaintyEvidenceStore().load(root)
