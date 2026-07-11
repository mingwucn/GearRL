#!/usr/bin/env python3
"""Freeze uncertainty intervals and sensitivity indices from direct CAE evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from evaluation.load_uncertainty import DirectCornerValidator, SobolLoadUncertaintyStudy, StaticLoadUncertaintyModel


@dataclass(frozen=True)
class LoadUncertaintyConfig:
    sobol_exponent: int = 13
    bootstrap_samples: int = 5_000
    random_seed: int = 2026
    maximum_corner_relative_error: float = 1e-10


class LoadEnvelopeRepository:
    """Read direct-CAE envelope records grouped by material."""

    def load(self, root: Path) -> dict[str, tuple[dict, ...]]:
        manifest = json.loads((root / "manifest.json").read_text())
        grouped: dict[str, list[dict]] = {}
        for item in manifest["records"]:
            path = root / "records" / f"{item['case_id']}.json"
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != item["sha256"]:
                raise ValueError(f"Direct envelope hash mismatch: {item['case_id']}")
            record = json.loads(payload)
            grouped.setdefault(record["load_case"]["material_name"], []).append(record)
        return {name: tuple(records) for name, records in grouped.items()}


class LoadUncertaintyEvidenceStore:
    """Persist a self-verifying summary bound to its direct-evidence manifest."""

    @staticmethod
    def _encode(value) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()

    def write(self, root: Path, source_manifest: Path, config: LoadUncertaintyConfig, validation: dict, summaries) -> Path:
        if root.exists() and any(root.iterdir()):
            raise FileExistsError("Uncertainty destination must be empty")
        root.mkdir(parents=True, exist_ok=True)
        result_bytes = self._encode({"validation": validation, "materials": [asdict(item) for item in summaries]})
        (root / "results.json").write_bytes(result_bytes)
        manifest = {
            "scope": "conditional digital static-strength uncertainty; uniform operating ranges; fixed sourced material data",
            "method": "scrambled Sobol propagation with within-layout sensitivity indices and layout-bootstrap failure intervals",
            "config": asdict(config),
            "source_manifest": str(source_manifest),
            "source_manifest_sha256": hashlib.sha256(source_manifest.read_bytes()).hexdigest(),
            "results_sha256": hashlib.sha256(result_bytes).hexdigest(),
        }
        (root / "manifest.json").write_bytes(self._encode(manifest))
        return root / "manifest.json"

    def load(self, root: Path) -> tuple[dict, dict]:
        manifest = json.loads((root / "manifest.json").read_text())
        source = Path(manifest["source_manifest"])
        if hashlib.sha256(source.read_bytes()).hexdigest() != manifest["source_manifest_sha256"]:
            raise ValueError("Uncertainty source-manifest hash mismatch")
        payload = (root / "results.json").read_bytes()
        if hashlib.sha256(payload).hexdigest() != manifest["results_sha256"]:
            raise ValueError("Uncertainty results hash mismatch")
        return manifest, json.loads(payload)


class LoadUncertaintyCommand:
    def run(self, envelope_root: Path, output: Path, config: LoadUncertaintyConfig) -> Path:
        grouped = LoadEnvelopeRepository().load(envelope_root)
        validation, summaries = {}, []
        for material, records in sorted(grouped.items()):
            reference = next(
                record for record in records
                if record["load_case"]["input_torque_nm"] == 1.0
                and record["load_case"]["face_width_mm"] == 12.0
                and record["load_case"]["efficiency"] == 0.95
            )
            error = DirectCornerValidator().maximum_relative_error(reference, records)
            validation[material] = {"direct_corner_count": len(records), "maximum_relative_error": error}
            if error > config.maximum_corner_relative_error:
                raise RuntimeError(f"Linear response validation failed for {material}: {error}")
            summaries.append(
                SobolLoadUncertaintyStudy(
                    StaticLoadUncertaintyModel(), config.random_seed, config.bootstrap_samples
                ).evaluate(material, reference, config.sobol_exponent)
            )
        return LoadUncertaintyEvidenceStore().write(
            output, envelope_root / "manifest.json", config, validation, tuple(summaries)
        )


class LoadUncertaintyCLI:
    def run(self) -> None:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--envelope", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--sobol-exponent", type=int, default=13)
        args = parser.parse_args()
        config = LoadUncertaintyConfig(sobol_exponent=args.sobol_exponent)
        print(LoadUncertaintyCommand().run(args.envelope, args.output, config))


if __name__ == "__main__":
    LoadUncertaintyCLI().run()
