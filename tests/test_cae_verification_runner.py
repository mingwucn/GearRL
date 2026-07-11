import json

from run_cae_verification import CAEVerificationRunner


def test_verification_runner_persists_all_passing_gates(tmp_path) -> None:
    bundle = CAEVerificationRunner(tmp_path).run()
    summary = json.loads((bundle / "verification_summary.json").read_text())
    assert all(summary.values())
    assert (bundle / "results" / "verification-suite.json").is_file()
