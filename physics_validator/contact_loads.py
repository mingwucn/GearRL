"""Mechanically consistent mesh-contact loads for static tooth screening."""

from __future__ import annotations

from dataclasses import dataclass

from common.design_models import DesignProblem, GearTrain, ValidationIssue


@dataclass(frozen=True)
class MemberContactLoad:
    stage_id: str
    member: int
    mesh_id: str
    tangential_force_n: float
    equivalent_torque_nm: float
    upstream_efficiency: float


class MeshContactLoadResolver:
    """Apply one equal tangential contact force to both members of each mesh."""

    def resolve(
        self,
        problem: DesignProblem,
        train: GearTrain,
        speed_ratios: dict[str, float],
        stage_efficiencies: dict[str, float],
    ) -> tuple[dict[tuple[str, int], MemberContactLoad], tuple[ValidationIssue, ...]]:
        if problem.load_case is None:
            return {}, ()
        stages = train.stage_map()
        loads: dict[tuple[str, int], MemberContactLoad] = {}
        issues: list[ValidationIssue] = []
        for edge_index, edge in enumerate(train.meshes):
            driver = stages.get(edge.driver_stage_id)
            driven = stages.get(edge.driven_stage_id)
            speed_ratio = speed_ratios.get(edge.driver_stage_id)
            upstream_efficiency = stage_efficiencies.get(edge.driver_stage_id)
            if driver is None or driven is None or speed_ratio in (None, 0) or upstream_efficiency is None:
                issues.append(ValidationIssue("cae_missing_power_flow", f"Cannot resolve contact load for mesh {edge_index}"))
                continue
            driver_torque = problem.load_case.input_torque_nm * upstream_efficiency / abs(speed_ratio)
            force = driver_torque * 1_000.0 / driver.pitch_radius_mm(edge.driver_member)
            mesh_id = f"{edge.driver_stage_id}[{edge.driver_member}]->{edge.driven_stage_id}[{edge.driven_member}]"
            for stage, member in ((driver, edge.driver_member), (driven, edge.driven_member)):
                key = (stage.id, member)
                if key in loads:
                    issues.append(ValidationIssue("cae_multiple_contact_loads", f"Multiple mesh loads reach {stage.id}[{member}]"))
                    continue
                loads[key] = MemberContactLoad(
                    stage.id,
                    member,
                    mesh_id,
                    force,
                    force * stage.pitch_radius_mm(member) / 1_000.0,
                    upstream_efficiency,
                )
        return loads, tuple(issues)
