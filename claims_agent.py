"""Minimal LangGraph workflow for a read-only claim investigation."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Any, TypedDict
import uuid

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from fraud_indicators import evaluate_fraud_indicators
from fraud_risk import calculate_fraud_risk
from claim_lookup import get_claim_details
from missing_documents import get_missing_documents
from policy_search import search_policy
from vehicle_verification import verify_claim_vehicle

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class InvestigationState(TypedDict, total=False):
    claim_id: str
    found: bool
    error: str
    claim_details: dict[str, Any]
    missing_documents: dict[str, Any]
    fraud_indicators: dict[str, Any]
    fraud_risk: dict[str, Any]
    policy_citations: list[dict[str, Any]]
    vehicle_verification: dict[str, Any]
    review_payload: dict[str, Any]
    review_response: str
    review_status: str


POLICY_QUERY = "coverage limits deductibles exclusions and endorsements"
MCP_TIMEOUT_SECONDS = 10
ROOT = Path(__file__).resolve().parent


def _mcp_result_data(result: Any) -> dict[str, Any]:
    if result.structured_content:
        return dict(result.structured_content)
    if not result.content:
        return {"success": False, "error_type": "EMPTY_MCP_RESPONSE"}
    return json.loads(result.content[0].text)


async def _call_mcp_decoder(vin: str) -> dict[str, Any]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "mcp_server.py")],
        cwd=ROOT,
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("decode_vehicle_vin", {"vin": vin})
            return _mcp_result_data(result)


def _lookup_claim(state: InvestigationState) -> InvestigationState:
    details = get_claim_details(state["claim_id"])
    if not details["found"]:
        return {
            "found": False,
            "error": f"Claim not found: {state['claim_id']}",
        }
    return {"found": True, "claim_details": details}


def _route_after_lookup(state: InvestigationState) -> str:
    return "continue" if state.get("found") else "stop"


def _identify_missing_documents(state: InvestigationState) -> InvestigationState:
    return {"missing_documents": get_missing_documents(state["claim_id"])}


def _evaluate_indicators(state: InvestigationState) -> InvestigationState:
    return {"fraud_indicators": evaluate_fraud_indicators(state["claim_id"])}


def _calculate_risk(state: InvestigationState) -> InvestigationState:
    return {"fraud_risk": calculate_fraud_risk(state["claim_id"])}


def _verify_vehicle(state: InvestigationState) -> InvestigationState:
    claim = state["claim_details"]["claim"]
    vin = claim.get("vin", "")
    try:
        decoded_result = asyncio.run(
            asyncio.wait_for(
                _call_mcp_decoder(vin),
                timeout=MCP_TIMEOUT_SECONDS,
            )
        )
    except Exception as exc:
        decoded_result = {
            "success": False,
            "error_type": "MCP_CONNECTION_ERROR",
            "error": type(exc).__name__,
        }

    return {
        "vehicle_verification": verify_claim_vehicle(
            state["claim_id"], decoded_result
        )
    }


def _retrieve_policy(state: InvestigationState) -> InvestigationState:
    claim = state["claim_details"]["claim"]
    policy_id = claim["policy_id"]
    passages = search_policy(POLICY_QUERY, policy_id)
    if any(passage.get("policy_id") != policy_id for passage in passages):
        return {
            "policy_citations": [],
            "error": f"Policy isolation check failed for {policy_id}",
        }
    return {"policy_citations": passages}


def _human_review(state: InvestigationState) -> InvestigationState:
    payload = {
        "claim_id": state["claim_id"],
        "missing_documents": state["missing_documents"],
        "fraud_indicator_findings": state["fraud_indicators"],
        "investigation_priority_score": state["fraud_risk"],
        "vehicle_verification": state["vehicle_verification"],
        "policy_citations": state["policy_citations"],
    }
    response = interrupt(payload)
    if response == "ACCEPT_REPORT":
        review_status = "ACCEPTED_FOR_REPORTING"
    elif response == "REQUEST_MORE_INFO":
        review_status = "NEEDS_MORE_INFORMATION"
    else:
        review_status = "INVALID_REVIEW_RESPONSE"
    return {
        "review_payload": payload,
        "review_response": response,
        "review_status": review_status,
    }


def _build_workflow():
    graph = StateGraph(InvestigationState)
    graph.add_node("lookup_claim", _lookup_claim)
    graph.add_node("identify_missing_documents", _identify_missing_documents)
    graph.add_node("evaluate_indicators", _evaluate_indicators)
    graph.add_node("calculate_risk", _calculate_risk)
    graph.add_node("verify_vehicle", _verify_vehicle)
    graph.add_node("retrieve_policy", _retrieve_policy)
    graph.add_node("human_review", _human_review)

    graph.add_edge(START, "lookup_claim")
    graph.add_conditional_edges(
        "lookup_claim",
        _route_after_lookup,
        {"continue": "identify_missing_documents", "stop": END},
    )
    graph.add_edge("identify_missing_documents", "evaluate_indicators")
    graph.add_edge("evaluate_indicators", "calculate_risk")
    graph.add_edge("calculate_risk", "verify_vehicle")
    graph.add_edge("verify_vehicle", "retrieve_policy")
    graph.add_edge("retrieve_policy", "human_review")
    graph.add_edge("human_review", END)
    return graph.compile(checkpointer=MemorySaver())


WORKFLOW = _build_workflow()


def investigate_claim(claim_id: str, thread_id: str | None = None) -> dict[str, Any]:
    """Run the workflow until the human-review checkpoint."""
    thread_id = thread_id or f"claim-{claim_id}-{uuid.uuid4().hex}"
    result = dict(
        WORKFLOW.invoke(
            {"claim_id": claim_id},
            config={"configurable": {"thread_id": thread_id}},
        )
    )
    result["thread_id"] = thread_id
    return result


def resume_investigation(thread_id: str, response: str) -> dict[str, Any]:
    """Resume a paused workflow with a human-review response."""
    result = dict(
        WORKFLOW.invoke(
            Command(resume=response),
            config={"configurable": {"thread_id": thread_id}},
        )
    )
    result["thread_id"] = thread_id
    return result


__all__ = ["InvestigationState", "investigate_claim", "resume_investigation"]
