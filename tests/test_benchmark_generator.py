from benchmark.generator import generate_benchmark_suite, generate_compound_instances


def test_generator_is_seeded_and_self_certifying() -> None:
    first = generate_compound_instances(1234, 3)
    second = generate_compound_instances(1234, 3)
    assert [instance.to_json() for instance in first] == [instance.to_json() for instance in second]
    assert all(instance.certificate["valid"] for instance in first)
    assert all(instance.certificate["signed_speed_ratio"] == instance.problem.constraints.target_speed_ratio for instance in first)


def test_suite_labels_and_certifies_infeasible_cases() -> None:
    suite = generate_benchmark_suite(8, 2, 3)
    assert len(suite) == 5
    assert sum(instance.expected_feasible for instance in suite) == 2
    assert all(not instance.certificate["valid"] for instance in suite if not instance.expected_feasible)
