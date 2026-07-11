from benchmark.generator import BenchmarkGenerator


def test_generator_is_seeded_and_self_certifying() -> None:
    generator = BenchmarkGenerator()
    first = generator.generate_compound_instances(1234, 3)
    second = generator.generate_compound_instances(1234, 3)
    assert [instance.to_json() for instance in first] == [instance.to_json() for instance in second]
    assert all(instance.certificate["valid"] for instance in first)
    assert all(instance.certificate["signed_speed_ratio"] == instance.problem.constraints.target_speed_ratio for instance in first)


def test_suite_labels_and_certifies_infeasible_cases() -> None:
    suite = BenchmarkGenerator().generate_suite(8, 2, 3)
    assert len(suite) == 5
    assert sum(instance.expected_feasible for instance in suite) == 2
    assert all(not instance.certificate["valid"] for instance in suite if not instance.expected_feasible)


def test_generator_stratifies_instances_across_four_enclosure_families() -> None:
    instances = BenchmarkGenerator().generate_compound_instances(2026, 8)
    assert {instance.family for instance in instances} == {
        "compound-square", "compound-wide", "compound-tall", "compound-chamfered"
    }
