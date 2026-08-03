# Copyright (c) 2026 Minsun Kim. All rights reserved. See LICENSE.
"""
Core data contracts for the AI Governance Studio.

Every artifact that crosses a module boundary (intake -> risk engine ->
action plan -> policy engine -> MCP gate -> audit) is a typed Pydantic
model. The 8 risk factors on UseCaseIntake match PRD Section F-02 Stage 2
exactly (names and point weights) -- this is deliberate: the wireframe's
"Risk Factors" checklist on the New Intake screen is supposed to be
*literally* the same 8 dimensions the engine scores, not an approximation
of them. See docs/PRD or the risk_engine.py docstring for why 8, and why
binary.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OutputType(str, Enum):
    SUMMARY = "Summary"
    DECISION_SUPPORT = "Decision Support"
    AUTONOMOUS = "Autonomous"
    GENERATIVE = "Generative"


class Persona(str, Enum):
    INTERNAL = "Internal"
    ENTERPRISE = "Enterprise"
    CONSUMER = "Consumer"
    PARTNER = "Partner"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class UseCaseIntake(BaseModel):
    """F-01: Standardized AI Use Case Intake."""

    model_config = ConfigDict(protected_namespaces=())

    use_case_name: str = Field(..., min_length=3)
    business_unit: str = Field(..., min_length=2)
    email: Optional[str] = None
    business_goal: Optional[str] = None
    description: str = Field(..., min_length=10)
    problem_statement: str = Field(..., min_length=50)
    persona: Persona = Persona.INTERNAL
    output_type: OutputType = OutputType.DECISION_SUPPORT

    # 8 binary risk factors (F-02 Stage 2). Names and weights match the
    # PRD table exactly -- see risk_engine.py RISK_FACTORS.
    personal_data_privacy: bool = False
    sensitive_data_enterprise_ip: bool = False
    autonomous_decision_making: bool = False
    high_impact_domain: bool = False
    external_users_reputation: bool = False
    model_transparency: bool = False
    security_exposure: bool = False
    third_party_dependency: bool = False

    # F-10 Tier 1: evidence attachment only -- stored and linked, not
    # analyzed. See action_plan.py / policy_engine.py: none of these
    # fields feed the deterministic score or the MCP gate at Tier 1.
    technical_evidence_url: Optional[str] = None
    foundation_model: Optional[str] = None
    enterprise_policies: List[str] = Field(default_factory=list)


class RiskFactorContribution(BaseModel):
    factor: str
    active: bool
    points: int


class RiskScore(BaseModel):
    """F-02: Deterministic Risk Scoring Engine output."""

    total_score: int = Field(..., ge=0, le=130)
    risk_level: RiskLevel
    breakdown: List[RiskFactorContribution]
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActionCategory(str, Enum):
    TECHNICAL = "Technical"
    BUSINESS = "Business"


class ActionItem(BaseModel):
    """
    A single recommended control in the Playbook (F-07). `triggered_by`
    names the specific risk factor that produced this item -- every item
    traces back to RiskScore, never to free-form LLM judgment.
    """

    label: str
    category: ActionCategory
    triggered_by: str


class ActionPlan(BaseModel):
    """F-07: Playbook Engine (Risk-to-Action Plan). Deterministic, no LLM call."""

    use_case_name: str
    risk_level: RiskLevel
    action_items: List[ActionItem]
    suggested_owner: str
    review_cadence_days: int
    estimated_residual_risk: RiskLevel
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MCPToolPolicy(BaseModel):
    """
    A single entry in the MCP tool-calling policy manifest -- the artifact
    that turns a risk score into an enforceable runtime boundary.
    """

    tool_category: str
    allowed: bool
    requires_hitl_token: bool
    condition: str


class PolicyManifest(BaseModel):
    """F-03: Actionable Guardrail & Policy-as-Code Generation Engine output."""

    use_case_name: str
    applicable_frameworks: List[str]
    governance_narrative: str
    controls: List[str] = Field(..., min_length=1)
    mcp_tool_policies: List[MCPToolPolicy]
    system_prompt_constraint: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("controls")
    @classmethod
    def cap_controls(cls, v: List[str]) -> List[str]:
        return v[:6] if len(v) > 6 else v


class HITLDecisionValue(str, Enum):
    APPROVE = "Approve"
    REJECT = "Reject"
    CONDITIONAL_APPROVE = "Conditional Approve"


class HITLDecision(BaseModel):
    """F-04: HITL Approval Dashboard entry."""

    use_case_name: str
    reviewer_id: str
    decision: HITLDecisionValue
    notes: Optional[str] = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolCallAttempt(BaseModel):
    """A simulated MCP tool-call event, intercepted by the policy gate."""

    use_case_name: str
    tool_category: str
    hitl_token_present: bool
    allowed: bool
    reason: str
    attempted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
