# Copyright (c) 2026 Minsun Kim. All rights reserved. See LICENSE.
"""
F-02: Deterministic Risk Scoring Engine (Stage 2 -- Risk Dimension Assessment).

Deliberately NOT an LLM call. The PRD's success signal for this module is
"risk scores identical across repeated runs for the same inputs" --
that reproducibility guarantee only holds if the scoring is pure,
deterministic arithmetic.

Why 8 factors, and why binary (Present / Not Present) rather than a
1-to-5 subjective scale:

1. A 1-to-5 scale is exactly where reviewer-to-reviewer inconsistency
   creeps in -- "is this a 3 or a 4" is a judgment call, while "is
   personal data present" is a fact check most reviewers answer the
   same way. Severity is encoded once, in the fixed weight assigned to
   each factor at design time, not re-judged on every submission.
2. Eight is a realistic upper bound for a form a reviewer completes in
   the couple of minutes the Product Vision's "as easy as an expense
   report" goal implies.
3. Eight binary factors produce 256 distinct combinations across the
   0-130 range -- enough resolution to distinguish "barely High" from
   "maximally High" rather than collapsing everything into three flat
   buckets.
4. Each factor corresponds to a specific regulatory concern surfaced
   later in F-03's framework mapping (Personal Data -> GDPR, Autonomous
   Decision Making -> EU AI Act high-risk provisions, Third-Party
   Dependency -> vendor risk) -- F-02 and F-03 are designed to interlock.
"""
from __future__ import annotations

from .models import RiskFactorContribution, RiskLevel, RiskScore, UseCaseIntake

# (attribute name on UseCaseIntake, human label, point weight) -- matches
# the PRD F-02 Stage 2 table exactly, in the same order.
RISK_FACTORS: list[tuple[str, str, int]] = [
    ("personal_data_privacy", "Personal Data / Privacy", 20),
    ("sensitive_data_enterprise_ip", "Sensitive Data / Enterprise IP", 20),
    ("autonomous_decision_making", "Autonomous Decision Making", 20),
    ("high_impact_domain", "High-Impact Domain", 20),
    ("external_users_reputation", "External Users / Reputation", 15),
    ("model_transparency", "Model Transparency", 15),
    ("security_exposure", "Security Exposure", 10),
    ("third_party_dependency", "Third-Party Dependency", 10),
]


def classify(total_score: int) -> RiskLevel:
    if total_score <= 29:
        return RiskLevel.LOW
    if total_score <= 59:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


def score_use_case(intake: UseCaseIntake) -> RiskScore:
    breakdown: list[RiskFactorContribution] = []
    total = 0

    for attr, label, weight in RISK_FACTORS:
        active = bool(getattr(intake, attr))
        points = weight if active else 0
        total += points
        breakdown.append(RiskFactorContribution(factor=label, active=active, points=points))

    return RiskScore(total_score=total, risk_level=classify(total), breakdown=breakdown)
