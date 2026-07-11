"""Independent verifier for the certified planar GearRL model.

The verifier does not depend on the simulator or RL environment.  It checks
the declared design model directly and emits a serialisable certificate.
"""

from __future__ import annotations

from collections import deque
from math import hypot, isclose

from common.design_models import (
    DesignProblem,
    GearStage,
    GearTrain,
    Point2D,
    ValidationCertificate,
    ValidationIssue,
)


class ReferenceVerifier:
    MODEL_VERSION = "certified-planar-v1"

    @classmethod
    def verify(cls, problem: DesignProblem, train: GearTrain) -> ValidationCertificate:
        issues: list[ValidationIssue] = []
        stages = train.stage_map()
        cls._check_problem_stages(problem, stages, issues)
        cls._check_stage_constraints(problem, train, issues)
        cls._check_boundary(problem, train, issues)
        cls._check_collisions(train, issues)
        cls._check_meshes(train, stages, issues)
        ratio = cls._propagate_ratio(problem, train, stages, issues)

        if ratio is not None and problem.constraints.target_speed_ratio is not None:
            if not isclose(
                ratio,
                problem.constraints.target_speed_ratio,
                rel_tol=problem.constraints.ratio_tolerance,
                abs_tol=problem.constraints.ratio_tolerance,
            ):
                issues.append(ValidationIssue(
                    "speed_ratio_mismatch",
                    f"Computed signed speed ratio {ratio:.8g} does not match "
                    f"target {problem.constraints.target_speed_ratio:.8g}",
                ))

        return ValidationCertificate(
            valid=not issues,
            issues=issues,
            signed_speed_ratio=ratio,
            minimum_clearance_mm=cls._minimum_boundary_clearance(problem, train),
            model_version=cls.MODEL_VERSION,
        )

    @classmethod
    def verify_with_cae(cls, problem: DesignProblem, train: GearTrain) -> ValidationCertificate:
        """Validate the planar model and apply declared static-strength limits.

        CAE screening is opt-in: it runs only when both a load case and a
        minimum safety factor are present in the canonical problem definition.
        """
        certificate = cls.verify(problem, train)
        if not certificate.valid:
            return certificate
        if problem.load_case is None or problem.constraints.min_safety_factor is None:
            return certificate

        from cae.gear_screening import screen_tooth_root

        ratios = cls._stage_speed_ratios(problem, train, train.stage_map())
        reports: list[dict] = []
        for stage in train.stages:
            speed_ratio = ratios.get(stage.id)
            if speed_ratio is None or speed_ratio == 0:
                certificate.issues.append(ValidationIssue("cae_missing_kinematics", f"No speed ratio for {stage.id}"))
                continue
            # Ideal power transmission gives T_stage = T_input / |omega_stage/omega_input|.
            stage_torque = problem.load_case.input_torque_nm / abs(speed_ratio)
            for member in range(len(stage.teeth)):
                report = screen_tooth_root(stage, member, problem.load_case, stage_torque, problem.constraints.pressure_angle_deg)
                reports.append(report.to_json())
                if report.safety_factor + 1e-12 < problem.constraints.min_safety_factor:
                    certificate.issues.append(
                        ValidationIssue(
                            "cae_safety_factor",
                            f"{stage.id}[{member}] safety factor {report.safety_factor:.6g} is below "
                            f"{problem.constraints.min_safety_factor:.6g}",
                        )
                    )
        certificate.cae_reports = reports
        certificate.valid = not certificate.issues
        return certificate

    @staticmethod
    def _add(issues: list[ValidationIssue], code: str, message: str) -> None:
        issues.append(ValidationIssue(code, message))

    @classmethod
    def _check_problem_stages(
        cls, problem: DesignProblem, stages: dict[str, GearStage], issues: list[ValidationIssue]
    ) -> None:
        for stage_id in (problem.input_stage_id, problem.output_stage_id):
            if stage_id not in stages:
                cls._add(issues, "missing_terminal_stage", f"Missing terminal stage {stage_id}")

    @classmethod
    def _check_stage_constraints(
        cls, problem: DesignProblem, train: GearTrain, issues: list[ValidationIssue]
    ) -> None:
        for stage in train.stages:
            for member, teeth in enumerate(stage.teeth):
                if not problem.constraints.min_teeth <= teeth <= problem.constraints.max_teeth:
                    cls._add(
                        issues,
                        "tooth_count_out_of_bounds",
                        f"{stage.id}[{member}] has {teeth} teeth outside "
                        f"[{problem.constraints.min_teeth}, {problem.constraints.max_teeth}]",
                    )

    @classmethod
    def _check_boundary(
        cls, problem: DesignProblem, train: GearTrain, issues: list[ValidationIssue]
    ) -> None:
        for stage in train.stages:
            if not cls._inside(stage.center, problem.boundary):
                cls._add(issues, "outside_boundary", f"Stage {stage.id} center is outside the boundary")
                continue
            required = stage.outer_radius_mm() + problem.constraints.boundary_clearance
            actual = cls._distance_to_boundary(stage.center, problem.boundary)
            if actual + 1e-9 < required:
                cls._add(
                    issues,
                    "boundary_clearance",
                    f"Stage {stage.id} requires {required:.6g} mm boundary clearance, has {actual:.6g}",
                )

    @classmethod
    def _check_collisions(cls, train: GearTrain, issues: list[ValidationIssue]) -> None:
        intended_meshes = {
            (edge.driver_stage_id, edge.driver_member, edge.driven_stage_id, edge.driven_member)
            for edge in train.meshes
        }
        for index, first in enumerate(train.stages):
            for second in train.stages[index + 1:]:
                distance = hypot(first.center.x - second.center.x, first.center.y - second.center.y)
                for first_member in range(len(first.teeth)):
                    for second_member in range(len(second.teeth)):
                        if first.layer(first_member) != second.layer(second_member):
                            continue
                        direct = (first.id, first_member, second.id, second_member)
                        reverse = (second.id, second_member, first.id, first_member)
                        # An intended external mesh overlaps addendum circles;
                        # its exact pitch-center distance is checked separately.
                        if direct in intended_meshes or reverse in intended_meshes:
                            continue
                        minimum = (
                            first.module_mm * (first.teeth[first_member] + 2) / 2.0
                            + second.module_mm * (second.teeth[second_member] + 2) / 2.0
                        )
                        if distance + 1e-9 < minimum:
                            cls._add(
                                issues,
                                "stage_collision",
                                f"Stages {first.id}[{first_member}] and {second.id}[{second_member}] "
                                f"overlap: {distance:.6g} < {minimum:.6g}",
                            )

    @classmethod
    def _check_meshes(
        cls, train: GearTrain, stages: dict[str, GearStage], issues: list[ValidationIssue]
    ) -> None:
        seen: set[tuple[str, int, str, int]] = set()
        for edge in train.meshes:
            key = (edge.driver_stage_id, edge.driver_member, edge.driven_stage_id, edge.driven_member)
            if key in seen:
                cls._add(issues, "duplicate_mesh", f"Duplicate mesh {key}")
                continue
            seen.add(key)
            driver, driven = stages.get(edge.driver_stage_id), stages.get(edge.driven_stage_id)
            if driver is None or driven is None:
                cls._add(issues, "mesh_missing_stage", f"Mesh {key} references a missing stage")
                continue
            if edge.driver_member >= len(driver.teeth) or edge.driven_member >= len(driven.teeth):
                cls._add(issues, "mesh_member_index", f"Mesh {key} references an invalid gear member")
                continue
            if driver.layer(edge.driver_member) != driven.layer(edge.driven_member):
                cls._add(issues, "axial_layer_mismatch", f"Mesh {key} connects different axial layers")
            expected = driver.pitch_radius_mm(edge.driver_member) + driven.pitch_radius_mm(edge.driven_member)
            actual = hypot(driver.center.x - driven.center.x, driver.center.y - driven.center.y)
            if abs(actual - expected) > edge.center_distance_tolerance_mm:
                cls._add(
                    issues,
                    "mesh_center_distance",
                    f"Mesh {key} requires {expected:.6g} mm, has {actual:.6g} mm",
                )

    @classmethod
    def _propagate_ratio(
        cls,
        problem: DesignProblem,
        train: GearTrain,
        stages: dict[str, GearStage],
        issues: list[ValidationIssue],
    ) -> float | None:
        if problem.input_stage_id not in stages or problem.output_stage_id not in stages:
            return None
        ratios = cls._stage_speed_ratios(problem, train, stages, issues)
        if problem.output_stage_id not in ratios:
            if not any(issue.code == "disconnected_output" for issue in issues):
                cls._add(issues, "disconnected_output", "No mesh path connects input to output")
            return None
        return ratios[problem.output_stage_id]

    @classmethod
    def _stage_speed_ratios(
        cls,
        problem: DesignProblem,
        train: GearTrain,
        stages: dict[str, GearStage],
        issues: list[ValidationIssue] | None = None,
    ) -> dict[str, float]:
        graph: dict[str, list[tuple[str, float]]] = {stage_id: [] for stage_id in stages}
        for edge in train.meshes:
            driver, driven = stages.get(edge.driver_stage_id), stages.get(edge.driven_stage_id)
            if driver is None or driven is None:
                continue
            if edge.driver_member >= len(driver.teeth) or edge.driven_member >= len(driven.teeth):
                continue
            forward = -driver.teeth[edge.driver_member] / driven.teeth[edge.driven_member]
            reverse = 1.0 / forward
            graph[edge.driver_stage_id].append((edge.driven_stage_id, forward))
            graph[edge.driven_stage_id].append((edge.driver_stage_id, reverse))

        ratios = {problem.input_stage_id: 1.0}
        queue: deque[str] = deque([problem.input_stage_id])
        while queue:
            current = queue.popleft()
            for nxt, factor in graph[current]:
                candidate = ratios[current] * factor
                if nxt not in ratios:
                    ratios[nxt] = candidate
                    queue.append(nxt)
                elif not isclose(ratios[nxt], candidate, rel_tol=1e-9, abs_tol=1e-9):
                    if issues is not None:
                        cls._add(issues, "inconsistent_kinematics", f"Conflicting speed ratios reach stage {nxt}")
        return ratios

    @classmethod
    def _minimum_boundary_clearance(cls, problem: DesignProblem, train: GearTrain) -> float | None:
        if not train.stages:
            return None
        return min(
            cls._distance_to_boundary(stage.center, problem.boundary) - stage.outer_radius_mm()
            for stage in train.stages
        )

    @staticmethod
    def _inside(point: Point2D, polygon: tuple[Point2D, ...]) -> bool:
        inside = False
        for index, first in enumerate(polygon):
            second = polygon[(index + 1) % len(polygon)]
            if (first.y > point.y) != (second.y > point.y):
                crossing_x = (second.x - first.x) * (point.y - first.y) / (second.y - first.y) + first.x
                if point.x < crossing_x:
                    inside = not inside
        return inside

    @staticmethod
    def _distance_to_boundary(point: Point2D, polygon: tuple[Point2D, ...]) -> float:
        distances = []
        for index, first in enumerate(polygon):
            second = polygon[(index + 1) % len(polygon)]
            dx, dy = second.x - first.x, second.y - first.y
            length_sq = dx * dx + dy * dy
            if length_sq == 0:
                distances.append(hypot(point.x - first.x, point.y - first.y))
                continue
            t = max(0.0, min(1.0, ((point.x - first.x) * dx + (point.y - first.y) * dy) / length_sq))
            distances.append(hypot(point.x - (first.x + t * dx), point.y - (first.y + t * dy)))
        return min(distances)
