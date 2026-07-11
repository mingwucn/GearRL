from evaluation.multiseed import MultiSeedPolicyStudy


def test_multiseed_study_records_each_seed_without_invalid_actions() -> None:
    outcomes = MultiSeedPolicyStudy(train_instances=2, test_instances=3).run((1, 2, 3))
    assert [outcome.seed for outcome in outcomes] == [1, 2, 3]
    assert all(outcome.valid_rate == 1.0 for outcome in outcomes)
