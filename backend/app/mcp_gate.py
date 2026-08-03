# Copyright (c) 2026 Minsun Kim. All rights reserved. See LICENSE.
"""
MCP Policy Gate.

Simulates the position a real Model Context Protocol server would sit in:
between an agent and the enterprise tools it wants to call. Every tool-call
attempt is checked against PolicyManifest.mcp_tool_policies (generated in
policy_engine.py), and against whether an HITL approval token is present.
Nothing here trusts the agent's own judgment -- the gate is the
enforcement point, not the model.
"""
from __future__ import annotations

from .models import PolicyManifest, ToolCallAttempt


def attempt_tool_call(manifest: PolicyManifest, tool_category: str, hitl_token_present: bool) -> ToolCallAttempt:
    matching = next((p for p in manifest.mcp_tool_policies if p.tool_category == tool_category), None)

    if matching is None:
        return ToolCallAttempt(
            use_case_name=manifest.use_case_name,
            tool_category=tool_category,
            hitl_token_present=hitl_token_present,
            allowed=False,
            reason=f"No policy defined for tool category '{tool_category}'; default-deny.",
        )

    if not matching.allowed:
        return ToolCallAttempt(
            use_case_name=manifest.use_case_name,
            tool_category=tool_category,
            hitl_token_present=hitl_token_present,
            allowed=False,
            reason=matching.condition,
        )

    if matching.requires_hitl_token and not hitl_token_present:
        return ToolCallAttempt(
            use_case_name=manifest.use_case_name,
            tool_category=tool_category,
            hitl_token_present=hitl_token_present,
            allowed=False,
            reason=f"Tool allowed in principle but requires an HITL token: {matching.condition}",
        )

    return ToolCallAttempt(
        use_case_name=manifest.use_case_name,
        tool_category=tool_category,
        hitl_token_present=hitl_token_present,
        allowed=True,
        reason=matching.condition,
    )
