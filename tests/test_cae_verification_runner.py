import json

from run_cae_verification import CAEVerificationRunner, CAEVerificationStudy, FrozenCAEVerificationStore


def test_verification_runner_persists_all_passing_gates(tmp_path) -> None:
    bundle = CAEVerificationRunner(tmp_path).run()
    summary = json.loads((bundle / "verification_summary.json").read_text())
    assert all(summary.values())
    assert (bundle / "results" / "verification-suite.json").is_file()


def test_frozen_v3_verification_is_content_addressed(tmp_path) -> None:
    payload, summary = CAEVerificationStudy().execute()

    manifest = FrozenCAEVerificationStore().write(tmp_path / "frozen", payload, summary)

    value = json.loads(manifest.read_text())
    assert value["model_version"] == "involute-tooth-root-plane-stress-v3"
    assert value["all_gates_passed"] is True
    assert len(value["verification_sha256"]) == 64
