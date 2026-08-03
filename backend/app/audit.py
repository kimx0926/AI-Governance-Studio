# Copyright (c) 2026 Minsun Kim. All rights reserved. See LICENSE.
"""
In-memory audit trail + lightweight evaluation metrics.

MVP scope note (Security & Privacy NFR): no PII is persisted beyond
process memory, and this store resets on restart. A production version
would swap this for a real datastore behind the same interface.

EvalTracker implements the scoped 06A evaluation framework (schema
validity rate, policy-denial accuracy) without any external eval
service -- the numbers are real and reproducible by anyone who runs the
test suite. It deliberately does NOT track LLM-quality metrics like
groundedness or hallucination rate: this project has no real production
traffic to measure those against, so it doesn't display them. See
README "What's built vs. what's vision".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .models import ActionPlan, HITLDecision, PolicyManifest, RiskScore, ToolCallAttempt, UseCaseIntake


@dataclass
class AuditRecord:
    intake: UseCaseIntake
    risk: RiskScore
    manifest: PolicyManifest
    action_plan: ActionPlan


class AuditStore:
    def __init__(self) -> None:
        self._records: dict[str, AuditRecord] = {}
        self._hitl_decisions: List[HITLDecision] = []
        self._tool_calls: List[ToolCallAttempt] = []

    def save(self, intake: UseCaseIntake, risk: RiskScore, manifest: PolicyManifest, action_plan: ActionPlan) -> None:
        self._records[intake.use_case_name] = AuditRecord(intake, risk, manifest, action_plan)

    def get(self, use_case_name: str) -> Optional[AuditRecord]:
        return self._records.get(use_case_name)

    def list_records(self) -> List[AuditRecord]:
        return list(self._records.values())

    def record_hitl_decision(self, decision: HITLDecision) -> None:
        self._hitl_decisions.append(decision)

    def list_hitl_decisions(self) -> List[HITLDecision]:
        return list(self._hitl_decisions)

    def record_tool_call(self, attempt: ToolCallAttempt) -> None:
        self._tool_calls.append(attempt)

    def list_tool_calls(self) -> List[ToolCallAttempt]:
        return list(self._tool_calls)

    def recent_activity(self, limit: int = 10) -> List[dict]:
        """
        Merges manifest-generation, tool-call, and HITL-decision events
        into a single, time-sorted feed for the Overview page. Every
        event traces to something already recorded elsewhere -- this
        method only sorts and labels, it invents nothing.
        """
        events: List[dict] = []

        for record in self._records.values():
            events.append({
                "type": "Manifest passed validation",
                "use_case_name": record.intake.use_case_name,
                "detail": f"{record.risk.risk_level.value} risk · {len(record.action_plan.action_items)} controls recommended",
                "at": record.manifest.generated_at,
            })

        for attempt in self._tool_calls:
            events.append({
                "type": "MCP Gate denied" if not attempt.allowed else "MCP Gate allowed",
                "use_case_name": attempt.use_case_name,
                "detail": f"{attempt.tool_category}: {attempt.reason}",
                "at": attempt.attempted_at,
            })

        for decision in self._hitl_decisions:
            events.append({
                "type": f"HITL {decision.decision.value.lower()}",
                "use_case_name": decision.use_case_name,
                "detail": decision.notes or f"Reviewed by {decision.reviewer_id}",
                "at": decision.decided_at,
            })

        events.sort(key=lambda e: e["at"], reverse=True)
        return events[:limit]

    def risk_distribution(self) -> dict:
        counts = {"Low": 0, "Medium": 0, "High": 0}
        for record in self._records.values():
            counts[record.risk.risk_level.value] += 1
        return counts

    def completed_use_case_names(self) -> set[str]:
        """
        A use case counts as "Completed" once a human reviewer has
        recorded an HITL decision for it (F-04) -- a real, checkable
        condition, not a placeholder number.
        """
        return {d.use_case_name for d in self._hitl_decisions}

    def last_action_for(self, use_case_name: str) -> Optional[str]:
        """Most recent tool-call outcome for a use case, for the Audit Trail 'Action' column."""
        matches = [t for t in self._tool_calls if t.use_case_name == use_case_name]
        if not matches:
            return None
        latest = max(matches, key=lambda t: t.attempted_at)
        verb = "denied" if not latest.allowed else "allowed"
        return f"MCP Gate {verb} {latest.tool_category} — {latest.reason}"


@dataclass
class EvalMetrics:
    total_manifests_generated: int = 0
    schema_valid_count: int = 0
    total_tool_calls: int = 0
    denied_tool_calls: int = 0

    @property
    def schema_validity_rate(self) -> float:
        if self.total_manifests_generated == 0:
            return 0.0
        return round(100 * self.schema_valid_count / self.total_manifests_generated, 1)

    @property
    def policy_denial_rate(self) -> float:
        if self.total_tool_calls == 0:
            return 0.0
        return round(100 * self.denied_tool_calls / self.total_tool_calls, 1)


class EvalTracker:
    """Tracks the two metrics defined in PRD Section 06A that are actually measured."""

    def __init__(self) -> None:
        self.metrics = EvalMetrics()

    def record_manifest_generated(self, valid: bool) -> None:
        self.metrics.total_manifests_generated += 1
        if valid:
            self.metrics.schema_valid_count += 1

    def record_tool_call(self, attempt: ToolCallAttempt) -> None:
        self.metrics.total_tool_calls += 1
        if not attempt.allowed:
            self.metrics.denied_tool_calls += 1
