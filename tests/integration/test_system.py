import json
from pathlib import Path
import subprocess


def test_end_to_end_certified_system(tmp_path):
    """Run the documented certified workflow in a fresh artifact directory."""
    completed = subprocess.run(
        ["python", "main.py", "--seed", "12", "--count", "3", "--output-root", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    bundle = Path(completed.stdout.strip().split(": ", 1)[1])
    summary = json.loads((bundle / "summary.json").read_text())
    assert summary["classification_accuracy"] == 1.0
    assert len(list((bundle / "results").glob("*.json"))) == 3
