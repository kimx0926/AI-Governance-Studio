# Copyright (c) 2026 Minsun Kim. All rights reserved. See LICENSE.
"""
LangGraph orchestration for the end-to-end governance workflow.

Intake -> Risk Score -> Playbook -> Policy Manifest -> Audit Save -> Tool Call Attempt

Each node wraps a module with its own single responsibility. The graph's
job is only sequencing and state-passing -- the workflow shape is fixed
code, not something the LLM improvises.
"""
from __future__ import annotations

from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph

from . import mcp_gate, risk_engine
from .action_plan import generate_action_plan
from .audit import AuditStore, EvalTracker
from .models import ActionPlan, PolicyManifest, RiskScore, ToolCallAttempt, UseCaseIntake
from .policy_engine import generate_policy_manifest


class GovernanceState(TypedDict, total=False):
    intake: UseCaseIntake
    risk: RiskScore
    action_plan: ActionPlan
    manifest: PolicyManifest
    requested_tool_category: Optional[str]
    hitl_token_present: bool
    tool_call_result: Optional[ToolCallAttempt]
    audit_saved: bool


def build_governance_graph(store: AuditStore, tracker: EvalTracker):
    graph = StateGraph(GovernanceState)

    def score_node(state: GovernanceState) -> GovernanceState:
        return {"risk": risk_engine.score_use_case(state["intake"])}

    def action_plan_node(state: GovernanceState) -> GovernanceState:
        return {"action_plan": generate_action_plan(state["intake"], state["risk"])}

    def policy_node(state: GovernanceState) -> GovernanceState:
        manifest = generate_policy_manifest(state["intake"], state["risk"])
        tracker.record_manifest_generated(valid=True)
        return {"manifest": manifest}

    def audit_save_node(state: GovernanceState) -> GovernanceState:
        store.save(state["intake"], state["risk"], state["manifest"], state["action_plan"])
        return {"audit_saved": True}

    def tool_call_node(state: GovernanceState) -> GovernanceState:
        requested = state.get("requested_tool_category")
        if not requested:
            return {"tool_call_result": None}
        attempt = mcp_gate.attempt_tool_call(state["manifest"], requested, state.get("hitl_token_present", False))
        store.record_tool_call(attempt)
        tracker.record_tool_call(attempt)
        return {"tool_call_result": attempt}

    graph.add_node("score_risk", score_node)
    graph.add_node("generate_action_plan", action_plan_node)
    graph.add_node("generate_policy", policy_node)
    graph.add_node("save_audit_record", audit_save_node)
    graph.add_node("attempt_tool_call", tool_call_node)

    graph.set_entry_point("score_risk")
    graph.add_edge("score_risk", "generate_action_plan")
    graph.add_edge("generate_action_plan", "generate_policy")
    graph.add_edge("generate_policy", "save_audit_record")
    graph.add_edge("save_audit_record", "attempt_tool_call")
    graph.add_edge("attempt_tool_call", END)

    return graph.compile()


def run_intake_workflow(
    intake: UseCaseIntake,
    store: AuditStore,
    tracker: EvalTracker,
    requested_tool_category: Optional[str] = None,
    hitl_token_present: bool = False,
) -> GovernanceState:
    app = build_governance_graph(store, tracker)
    return app.invoke({
        "intake": intake,
        "requested_tool_category": requested_tool_category,
        "hitl_token_present": hitl_token_present,
    })
