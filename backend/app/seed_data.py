# Copyright (c) 2026 Minsun Kim. All rights reserved. See LICENSE.
"""
Seed data: 5 example use cases loaded automatically on startup so the
demo shows a populated Overview, Risk Assessment, and Audit Trail
immediately, spanning Low to High risk. These mirror the wireframe's
"My AI Governance List" examples (Marketing Content Assistant, HR Resume
Screener, Customer Support Bot, Finance Report Generator, Legal Document
Analyzer).

Each runs through the exact same risk_engine / action_plan / policy_engine
/ mcp_gate code path as a live form submission -- nothing here is a
canned response.
"""
from __future__ import annotations

from .models import OutputType, Persona, UseCaseIntake

SEED_USE_CASES: list[UseCaseIntake] = [
    UseCaseIntake(
        use_case_name="Marketing Content Assistant",
        business_unit="Marketing",
        description="Drafts first-pass social captions and blog outlines for the marketing team to edit.",
        problem_statement="Marketing writers spend disproportionate time on first drafts of routine, low-stakes social content instead of on strategy and editing.",
        persona=Persona.INTERNAL,
        output_type=OutputType.GENERATIVE,
        third_party_dependency=True,
    ),
    UseCaseIntake(
        use_case_name="HR Resume Screener",
        business_unit="People",
        description="Screens inbound resumes and ranks candidates for recruiter review.",
        problem_statement="Recruiters manually review over 400 resumes per open role, and initial screening consistency varies significantly between reviewers.",
        persona=Persona.INTERNAL,
        output_type=OutputType.DECISION_SUPPORT,
        personal_data_privacy=True,
        model_transparency=True,
    ),
    UseCaseIntake(
        use_case_name="Customer Support Bot",
        business_unit="Support",
        description="Customer-facing chatbot that answers billing and account questions using a third-party LLM.",
        problem_statement="Support tickets for routine billing questions take 2+ days to resolve during peak volume, and customers want answers immediately.",
        persona=Persona.CONSUMER,
        output_type=OutputType.DECISION_SUPPORT,
        personal_data_privacy=True,
        external_users_reputation=True,
        third_party_dependency=True,
    ),
    UseCaseIntake(
        use_case_name="Legal Document Analyzer",
        business_unit="Legal",
        description="Analyzes inbound contracts and flags non-standard clauses for legal review, using a third-party LLM.",
        problem_statement="Legal spends a significant share of contract review time on first-pass clause identification that follows a predictable pattern.",
        persona=Persona.INTERNAL,
        output_type=OutputType.DECISION_SUPPORT,
        sensitive_data_enterprise_ip=True,
        high_impact_domain=True,
        model_transparency=True,
        third_party_dependency=True,
    ),
    UseCaseIntake(
        use_case_name="Finance Report Generator",
        business_unit="Finance",
        description="Generates quarterly financial summaries from internal data sources, autonomously, for exec review.",
        problem_statement="Analysts spend a full week each quarter manually compiling summaries from multiple internal finance systems before the exec review.",
        persona=Persona.INTERNAL,
        output_type=OutputType.AUTONOMOUS,
        personal_data_privacy=True,
        high_impact_domain=True,
        autonomous_decision_making=True,
        security_exposure=True,
    ),
]

# One simulated tool-call attempt per seeded use case, so the Audit Trail
# and Recent Activity feed have real, varied examples on first load.
SEED_TOOL_CALLS: list[tuple[str, str, bool]] = [
    ("Marketing Content Assistant", "sql_read", False),
    ("HR Resume Screener", "external_api", False),
    ("Customer Support Bot", "sql_read", False),
    ("Legal Document Analyzer", "external_api", False),
    ("Finance Report Generator", "sql_write", False),
]
