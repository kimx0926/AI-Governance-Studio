# Copyright (c) 2026 Minsun Kim. All rights reserved. See LICENSE.
"""
FastAPI entrypoint. Run with:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .audit import AuditStore, EvalTracker
from .langgraph_workflow import run_intake_workflow
from .mcp_gate import attempt_tool_call
from .models import HITLDecision, UseCaseIntake
from .seed_data import SEED_TOOL_CALLS, SEED_USE_CASES

app = FastAPI(
    title="AI Governance Studio API",
    description="Intake -> Risk Scoring -> Playbook -> Policy-as-Code -> MCP Gate -> HITL Audit",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP only; scope this down before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

store = AuditStore()
tracker = EvalTracker()


@app.on_event("startup")
def load_seed_data() -> None:
    """
    Runs the 5 example use cases from seed_data.py through the exact same
    LangGraph workflow a live form submission uses, so Overview / Risk
    Assessment / Audit Trail are populated on first load instead of empty.
    """
    for intake, (name, tool_category, hitl_token) in zip(SEED_USE_CASES, SEED_TOOL_CALLS):
        run_intake_workflow(intake, store, tracker, requested_tool_category=tool_category, hitl_token_present=hitl_token)


@app.post("/api/intake", response_model=dict)
def submit_intake(intake: UseCaseIntake, requested_tool_category: Optional[str] = None):
    """F-01 -> F-02 -> F-07 -> F-03 in one call, plus an optional MCP tool-call simulation."""
    result = run_intake_workflow(intake, store, tracker, requested_tool_category=requested_tool_category, hitl_token_present=False)
    return {
        "risk": result["risk"],
        "action_plan": result["action_plan"],
        "manifest": result["manifest"],
        "tool_call_result": result.get("tool_call_result"),
    }


@app.get("/api/overview")
def overview():
    """
    Aggregate view for the Overview page. Every number here is derived
    live from AuditStore/EvalTracker. Deliberately does NOT include an
    LLM-quality "system telemetry" table (groundedness, hallucination
    rate, etc.) -- that would require production traffic this project
    doesn't have. See README "What's built vs. what's vision".
    """
    records = store.list_records()
    completed = store.completed_use_case_names()
    return {
        "total_use_cases": len(records),
        "active_count": len(records) - len({r.intake.use_case_name for r in records} & completed),
        "completed_count": len({r.intake.use_case_name for r in records} & completed),
        "risk_distribution": store.risk_distribution(),
        "recent_activity": store.recent_activity(limit=8),
        "use_cases_by_risk": sorted(
            [
                {
                    "use_case_name": r.intake.use_case_name,
                    "risk_level": r.risk.risk_level,
                    "risk_score": r.risk.total_score,
                }
                for r in records
            ],
            key=lambda x: x["risk_score"],
            reverse=True,
        ),
    }


@app.get("/api/use-case/{use_case_name}")
def get_use_case(use_case_name: str):
    """Full detail for one use case -- backs the Playbook / Risk Assessment / Overview drill-down."""
    record = store.get(use_case_name)
    if record is None:
        raise HTTPException(status_code=404, detail="Use case not found")
    return {
        "intake": record.intake,
        "risk": record.risk,
        "action_plan": record.action_plan,
        "manifest": record.manifest,
    }


@app.get("/api/audit", response_model=list)
def list_audit_records():
    """F-04: Audit trail feed."""
    return [
        {
            "use_case_name": r.intake.use_case_name,
            "business_unit": r.intake.business_unit,
            "risk_score": r.risk.total_score,
            "risk_level": r.risk.risk_level,
            "frameworks": r.manifest.applicable_frameworks,
            "estimated_residual_risk": r.action_plan.estimated_residual_risk,
            "suggested_owner": r.action_plan.suggested_owner,
            "recent_action": store.last_action_for(r.intake.use_case_name),
        }
        for r in store.list_records()
    ]


@app.post("/api/hitl-decision", response_model=HITLDecision)
def submit_hitl_decision(decision: HITLDecision):
    record = store.get(decision.use_case_name)
    if record is None:
        raise HTTPException(status_code=404, detail="Use case not found in audit store")
    store.record_hitl_decision(decision)
    return decision


@app.post("/api/mcp/tool-call")
def simulate_tool_call(use_case_name: str, tool_category: str, hitl_token_present: bool = False):
    record = store.get(use_case_name)
    if record is None:
        raise HTTPException(status_code=404, detail="Use case not found")
    attempt = attempt_tool_call(record.manifest, tool_category, hitl_token_present)
    store.record_tool_call(attempt)
    tracker.record_tool_call(attempt)
    return attempt


@app.get("/api/eval-metrics")
def eval_metrics():
    """06A: live evaluation metrics (schema validity rate, policy denial rate)."""
    m = tracker.metrics
    return {
        "total_manifests_generated": m.total_manifests_generated,
        "schema_validity_rate_pct": m.schema_validity_rate,
        "total_tool_calls": m.total_tool_calls,
        "denied_tool_calls": m.denied_tool_calls,
        "policy_denial_rate_pct": m.policy_denial_rate,
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
