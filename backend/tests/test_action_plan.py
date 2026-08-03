# Copyright (c) 2026 Minsun Kim. All rights reserved. See LICENSE.
from app.action_plan import generate_action_plan
from app.models import ActionCategory, OutputType, Persona, RiskLevel, UseCaseIntake
from app.risk_engine import score_use_case


def _intake(**overrides) -> UseCaseIntake:
    defaults = dict(
        use_case_name="Test Use Case",
        business_unit="Marketing",
        description="A test use case.",
        problem_statement="x" * 60,
        persona=Persona.INTERNAL,
        output_type=OutputType.SUMMARY,
    )
    defaults.update(overrides)
    return UseCaseIntake(**defaults)


def test_low_risk_plan_is_minimal_and_low_owner():
    intake = _intake()
    risk = score_use_case(intake)
    plan = generate_action_plan(intake, risk)

    assert plan.risk_level == RiskLevel.LOW
    assert plan.suggested_owner == "Marketing Team"
    assert plan.review_cadence_days == 180
    assert plan.estimated_residual_risk == RiskLevel.LOW
    assert any("Annual Re-validation" in i.label for i in plan.action_items)


def test_high_risk_finance_plan_matches_wireframe_example():
    intake = _intake(
        business_unit="Finance",
        personal_data_privacy=True,
        high_impact_domain=True,
        autonomous_decision_making=True,
        security_exposure=True,
    )
    risk = score_use_case(intake)
    plan = generate_action_plan(intake, risk)

    assert risk.risk_level == RiskLevel.HIGH
    assert plan.suggested_owner == "Finance Director + Legal/Security"
    assert plan.review_cadence_days == 30
    assert plan.estimated_residual_risk == RiskLevel.MEDIUM

    labels = {item.label for item in plan.action_items}
    assert "Enable PII Masking" in labels
    assert "Enable Runtime Monitoring" in labels
    assert "Human Approval Required" in labels
    assert "Tool Allowlist Enforcement" in labels


def test_every_action_item_has_a_traceable_trigger():
    intake = _intake(personal_data_privacy=True, high_impact_domain=True)
    risk = score_use_case(intake)
    plan = generate_action_plan(intake, risk)

    for item in plan.action_items:
        assert item.triggered_by
        assert item.category in (ActionCategory.TECHNICAL, ActionCategory.BUSINESS)


def test_plan_is_reproducible():
    intake = _intake(personal_data_privacy=True, third_party_dependency=True)
    risk = score_use_case(intake)
    first = generate_action_plan(intake, risk)
    second = generate_action_plan(intake, risk)
    assert [i.label for i in first.action_items] == [i.label for i in second.action_items]
