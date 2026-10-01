from src.spineforge_v19_obligations import load_qualification_cases


def test_v19_has_exactly_six_frozen_case_contracts():
    cases = load_qualification_cases()
    assert len(cases.cases) == 6
    assert len({row.case_id for row in cases.cases}) == 6


def test_age_profiles_do_not_share_one_universal_obligation():
    cases = load_qualification_cases().cases
    age4 = next(row for row in cases if row.obligations.exact_age == 4)
    age12 = next(
        row for row in cases
        if row.obligations.exact_age == 12
        and row.obligations.story_family == "ADVENTURE_EXPLORATION"
    )
    age40 = next(row for row in cases if row.obligations.exact_age == 40)
    age60 = next(row for row in cases if row.obligations.exact_age == 60)

    assert age4.obligations.decision_required is False
    assert age12.obligations.decision_required is True
    assert age12.obligations.minimum_discovery_turns >= 3
    assert any("Layered objective" in x for x in age40.obligations.required_capabilities)
    assert any("age stereotyping" in x.lower() for x in age60.obligations.required_capabilities)


def test_paid_qualification_is_not_ready_until_all_context_fixtures_are_frozen():
    cases = load_qualification_cases().cases
    pending = [row for row in cases if row.context_fixture_status != "FROZEN"]
    assert len(pending) == 5
