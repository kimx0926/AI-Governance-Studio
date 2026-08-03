# Copyright (c) 2026 Minsun Kim. All rights reserved. See LICENSE.
from app.models import OutputType, Persona, RiskLevel, UseCaseIntake
from app.risk_engine import score_use_case


def _base_intake(**overrides) -> UseCaseIntake:
    defaults = dict(
        use_case_name="Test Use Case",
        business_unit="Marketing",
        description="A test use case for scoring.",
        problem_statement="x" * 60,
        persona=Persona.INTERNAL,
        output_type=OutputType.SUMMARY,
    )
    defaults.update(overrides)
    return UseCaseIntake(**defaults)


def test_zero_risk_factors_scores_zero_and_low():
    result = score_use_case(_base_intake())
    assert result.total_score == 0
    assert result.risk_level == RiskLevel.LOW


def test_all_risk_factors_scores_max_and_high():
    result = score_use_case(
        _base_intake(
            personal_data_privacy=True,
            sensitive_data_enterprise_ip=True,
            autonomous_decision_making=True,
            high_impact_domain=True,
            external_users_reputation=True,
            model_transparency=True,
            security_exposure=True,
            third_party_dependency=True,
        )
    )
    assert result.total_score == 130
    assert result.risk_level == RiskLevel.HIGH


def test_medium_boundary():
    # personal_data_privacy (20) + external_users_reputation (15) = 35 -> Medium
    result = score_use_case(_base_intake(personal_data_privacy=True, external_users_reputation=True))
    assert result.total_score == 35
    assert result.risk_level == RiskLevel.MEDIUM


def test_score_is_reproducible_across_calls():
    intake = _base_intake(personal_data_privacy=True, third_party_dependency=True)
    first = score_use_case(intake)
    second = score_use_case(intake)
    assert first.total_score == second.total_score == 30
