"""Isolated OR-Tools worker; this process must not import the synthesis package."""

from __future__ import annotations

from fractions import Fraction
import json
import sys

from ortools.sat.python import cp_model


class CandidateCollector(cp_model.CpSolverSolutionCallback):
    def __init__(self, variables: tuple[cp_model.IntVar, ...], maximum_candidates: int):
        super().__init__()
        self._variables = variables
        self._maximum_candidates = maximum_candidates
        self.candidates: list[tuple[int, int, int, int]] = []

    def on_solution_callback(self) -> None:
        self.candidates.append(tuple(self.value(variable) for variable in self._variables))
        if len(self.candidates) >= self._maximum_candidates:
            self.stop_search()


class CpSatWorker:
    """Build and exhaust the bounded integer model in an isolated process."""

    def run(self) -> None:
        request = json.load(sys.stdin)
        model, variables = self._model(request)
        collector = CandidateCollector(variables, int(request["maximum_candidates"]))
        solver = cp_model.CpSolver()
        solver.parameters.enumerate_all_solutions = True
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = int(request["seed"])
        solver.parameters.max_time_in_seconds = float(request["maximum_time_s"])
        status = solver.solve(model, collector)
        payload = {
            "candidates": collector.candidates,
            "search_complete": status in (cp_model.OPTIMAL, cp_model.INFEASIBLE),
        }
        json.dump(payload, sys.stdout, sort_keys=True)

    @staticmethod
    def _model(request: dict) -> tuple[cp_model.CpModel, tuple[cp_model.IntVar, ...]]:
        minimum = int(request["minimum_teeth"])
        maximum = int(request["maximum_teeth"])
        model = cp_model.CpModel()
        teeth = tuple(
            model.new_int_var(minimum, maximum, name)
            for name in ("input_teeth", "first_compound", "second_compound", "output_teeth")
        )
        input_teeth, first_compound, second_compound, output_teeth = teeth
        numerator_product = model.new_int_var(minimum ** 2, maximum ** 2, "numerator_product")
        denominator_product = model.new_int_var(minimum ** 2, maximum ** 2, "denominator_product")
        model.add_multiplication_equality(numerator_product, (input_teeth, second_compound))
        model.add_multiplication_equality(denominator_product, (first_compound, output_teeth))
        if request["target_speed_ratio"] is not None:
            target = Fraction(str(request["target_speed_ratio"])).limit_denominator(1_000_000)
            model.add(target.denominator * numerator_product == target.numerator * denominator_product)

        module = Fraction(str(request["module_mm"])).limit_denominator(1_000_000)
        distance = Fraction(str(request["terminal_distance_mm"])).limit_denominator(1_000_000)
        model.add(module.numerator * distance.denominator * sum(teeth) >= 2 * distance.numerator * module.denominator)
        first_sum = model.new_int_var(2 * minimum, 2 * maximum, "first_mesh_sum")
        second_sum = model.new_int_var(2 * minimum, 2 * maximum, "second_mesh_sum")
        model.add(first_sum == input_teeth + first_compound)
        model.add(second_sum == second_compound + output_teeth)
        difference = model.new_int_var(-2 * maximum, 2 * maximum, "mesh_sum_difference")
        absolute_difference = model.new_int_var(0, 2 * maximum, "absolute_mesh_sum_difference")
        model.add(difference == first_sum - second_sum)
        model.add_abs_equality(absolute_difference, difference)
        model.add(module.numerator * distance.denominator * absolute_difference <= 2 * distance.numerator * module.denominator)
        return model, teeth


if __name__ == "__main__":
    CpSatWorker().run()
