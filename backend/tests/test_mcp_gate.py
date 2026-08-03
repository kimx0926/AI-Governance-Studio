# Copyright (c) 2026 Minsun Kim. All rights reserved. See LICENSE.
from app.mcp_gate import attempt_tool_call
from app.models import OutputType, Persona, PolicyManifest, UseCaseIntake
from app.policy_engine import _derive_mcp_policies
from app.risk_engine import score_use_case


def _high_risk_sensitive_intake() -> UseCaseIntake:
    return UseCaseIntake(
        use_case_name="High Risk Finance Agent",
        business_unit="Finance",
        description="Autonomous agent handling customer financial records.",
        problem_statement="x" * 60,
        persona=Persona.CONSUMER,
        output_type=OutputType.AUTONOMOUS,
        personal_data_privacy=True,
        high_impact_domain=True,
        autonomous_decision_making=True,
        security_exposure=True,
    )


def _low_risk_intake() -> UseCaseIntake:
    return UseCaseIntake(
        use_case_name="Internal Summary Tool",
        business_unit="Ops",
        description="Summarizes internal meeting notes.",
        problem_statement="x" * 60,
        persona=Persona.INTERNAL,
        output_type=OutputType.SUMMARY,
    )


def _manifest_for(intake):
    risk = score_use_case(intake)
    policies = _derive_mcp_policies(intake, risk)
    return PolicyManifest(
        use_case_name=intake.use_case_name,
        applicable_frameworks=["NIST AI RMF"],
        governance_narrative="test",
        controls=["test control"],
        mcp_tool_policies=policies,
        system_prompt_constraint="test",
    )


def test_high_risk_sensitive_sql_read_blocked_even_with_token():
    manifest = _manifest_for(_high_risk_sensitive_intake())
    result = attempt_tool_call(manifest, "sql_read", hitl_token_present=True)
    assert result.allowed is False


def test_autonomous_agent_sql_write_always_blocked():
    manifest = _manifest_for(_high_risk_sensitive_intake())
    result = attempt_tool_call(manifest, "sql_write", hitl_token_present=True)
    assert result.allowed is False


def test_low_risk_sql_read_allowed_without_token():
    manifest = _manifest_for(_low_risk_intake())
    result = attempt_tool_call(manifest, "sql_read", hitl_token_present=False)
    assert result.allowed is True


def test_unknown_tool_category_defaults_to_deny():
    manifest = _manifest_for(_low_risk_intake())
    result = attempt_tool_call(manifest, "shell_exec", hitl_token_present=True)
    assert result.allowed is False
    assert "default-deny" in result.reason


def test_medium_risk_sql_write_requires_token():
    intake = _low_risk_intake()
    intake.high_impact_domain = True
    intake.external_users_reputation = True  # -> 35 pts, Medium
    manifest = _manifest_for(intake)

    denied = attempt_tool_call(manifest, "sql_write", hitl_token_present=False)
    allowed = attempt_tool_call(manifest, "sql_write", hitl_token_present=True)
    assert denied.allowed is False
    assert allowed.allowed is True
