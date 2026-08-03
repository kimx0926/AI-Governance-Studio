# Copyright (c) 2026 Minsun Kim. All rights reserved. See LICENSE.
"""
F-07: Playbook Engine (Risk-to-Action Plan).

Deterministic, same principle as risk_engine.py and the MCP policy
derivation in policy_engine.py -- see Design Decision T-06. "What do we
do about this risk" is answered by code a reviewer can read, not by an
LLM call, so the Playbook is exactly as reproducible as the score that
produced it.

Every ActionItem's `triggered_by` names the exact risk factor (with its
point weight) that produced it, matching the wireframe's "Recommended
Actions -- traceable to risk factors" display.
"""
from __future__ import annotations

from typing import List

from .models import ActionCategory, ActionItem, ActionPlan, RiskLevel, RiskScore, UseCaseIntake
from .risk_engine import RISK_FACTORS

_WEIGHT_BY_FACTOR = {attr: (label, weight) for attr, label, weight in RISK_FACTORS}

REVIEW_CADENCE_DAYS = {
    RiskLevel.LOW: 180,
    RiskLevel.MEDIUM: 90,
    RiskLevel.HIGH: 30,
}

# One-level-down heuristic: applying the recommended controls is assumed
# to move a use case one risk tier down, floored at Low. Illustrative
# planning estimate, not a measured outcome -- see Section 06A.
_RESIDUAL_STEP_DOWN = {
    RiskLevel.HIGH: RiskLevel.MEDIUM,
    RiskLevel.MEDIUM: RiskLevel.LOW,
    RiskLevel.LOW: RiskLevel.LOW,
}


def _trigger_label(factor_attr: str) -> str:
    label, weight = _WEIGHT_BY_FACTOR[factor_attr]
    return f"{label} ({weight} pts)"


def _owner_for(business_unit: str, risk_level: RiskLevel) -> str:
    if risk_level == RiskLevel.HIGH:
        return f"{business_unit} Director + Legal/Security"
    if risk_level == RiskLevel.MEDIUM:
        return f"{business_unit} Director"
    return f"{business_unit} Team"


def _derive_action_items(intake: UseCaseIntake, risk: RiskScore) -> List[ActionItem]:
    items: List[ActionItem] = []

    def add(label: str, category: ActionCategory, factor_attr: str) -> None:
        items.append(ActionItem(label=label, category=category, triggered_by=_trigger_label(factor_attr)))

    if intake.personal_data_privacy:
        add("Enable PII Masking", ActionCategory.TECHNICAL, "personal_data_privacy")
        add("Enable Audit Logging", ActionCategory.BUSINESS, "personal_data_privacy")

    if intake.sensitive_data_enterprise_ip:
        add("Enable Data Encryption", ActionCategory.TECHNICAL, "sensitive_data_enterprise_ip")

    if intake.autonomous_decision_making:
        add("Enable Runtime Monitoring", ActionCategory.TECHNICAL, "autonomous_decision_making")
        add("Mandatory HITL Sign-off Before Deployment", ActionCategory.BUSINESS, "autonomous_decision_making")

    if intake.high_impact_domain:
        add("Human Approval Required", ActionCategory.BUSINESS, "high_impact_domain")
        add("Legal & Compliance Review", ActionCategory.BUSINESS, "high_impact_domain")

    if intake.external_users_reputation:
        add("Enable Prompt-Injection Detection", ActionCategory.TECHNICAL, "external_users_reputation")

    if intake.model_transparency:
        add("Document Model Card & Explainability Notes", ActionCategory.TECHNICAL, "model_transparency")

    if intake.security_exposure:
        add("Tool Allowlist Enforcement", ActionCategory.TECHNICAL, "security_exposure")

    if intake.third_party_dependency:
        add("Vendor Risk Review", ActionCategory.BUSINESS, "third_party_dependency")

    # Risk-level rules aren't tied to a single factor, so triggered_by
    # states the rule directly rather than looking up a weight.
    def add_level(label: str, category: ActionCategory, rule: str) -> None:
        items.append(ActionItem(label=label, category=category, triggered_by=rule))

    if risk.risk_level == RiskLevel.HIGH:
        add_level("Monthly Re-validation Required", ActionCategory.BUSINESS, "risk_level = High")
    elif risk.risk_level == RiskLevel.MEDIUM:
        add_level("Quarterly Re-validation Required", ActionCategory.BUSINESS, "risk_level = Medium")
    else:
        add_level("Annual Re-validation Required", ActionCategory.BUSINESS, "risk_level = Low")

    seen, deduped = set(), []
    for item in items:
        if item.label not in seen:
            seen.add(item.label)
            deduped.append(item)
    return deduped


def generate_action_plan(intake: UseCaseIntake, risk: RiskScore) -> ActionPlan:
    return ActionPlan(
        use_case_name=intake.use_case_name,
        risk_level=risk.risk_level,
        action_items=_derive_action_items(intake, risk),
        suggested_owner=_owner_for(intake.business_unit, risk.risk_level),
        review_cadence_days=REVIEW_CADENCE_DAYS[risk.risk_level],
        estimated_residual_risk=_RESIDUAL_STEP_DOWN[risk.risk_level],
    )
