from __future__ import annotations

import json

import claims_agent


def test_known_claim_runs_all_steps_and_preserves_policy_isolation(monkeypatch) -> None:
    calls = []

    original_missing = claims_agent.get_missing_documents
    original_indicators = claims_agent.evaluate_fraud_indicators
    original_risk = claims_agent.calculate_fraud_risk
    original_search = claims_agent.search_policy

    def missing(claim_id):
        calls.append(("missing", claim_id))
        return original_missing(claim_id)

    def indicators(claim_id):
        calls.append(("indicators", claim_id))
        return original_indicators(claim_id)

    def risk(claim_id):
        calls.append(("risk", claim_id))
        return original_risk(claim_id)

    def search(query, policy_id, top_k=5):
        calls.append(("policy", policy_id))
        return original_search(query, policy_id, top_k)

    monkeypatch.setattr(claims_agent, "get_missing_documents", missing)
    monkeypatch.setattr(claims_agent, "evaluate_fraud_indicators", indicators)
    monkeypatch.setattr(claims_agent, "calculate_fraud_risk", risk)
    monkeypatch.setattr(claims_agent, "search_policy", search)

    async def decode(_vin):
        return {
            "success": True,
            "vin": "SYNTHETICVIN00001",
            "manufacturer": "Peugeot",
            "model": "208",
            "model_year": 2016,
        }

    monkeypatch.setattr(claims_agent, "_call_mcp_decoder", decode)

    result = claims_agent.investigate_claim("CLM-MOT-0001", "test-known")

    assert result["found"] is True
    assert result["claim_details"]["claim"]["claim_id"] == "CLM-MOT-0001"
    assert result["claim_details"]["claim"]["policy_id"] == "MOT-0000002"
    assert result["missing_documents"]["claim_id"] == "CLM-MOT-0001"
    assert result["fraud_indicators"]["claim_id"] == "CLM-MOT-0001"
    assert result["fraud_risk"]["claim_id"] == "CLM-MOT-0001"
    assert result["vehicle_verification"]["verification_status"] == "MATCHED"
    assert result["policy_citations"]
    assert all(item["policy_id"] == "MOT-0000002" for item in result["policy_citations"])
    assert [item[0] for item in calls] == ["missing", "indicators", "risk", "policy"]


def test_unknown_claim_stops_before_other_tools(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        claims_agent,
        "get_missing_documents",
        lambda claim_id: calls.append(claim_id),
    )
    monkeypatch.setattr(
        claims_agent,
        "evaluate_fraud_indicators",
        lambda claim_id: calls.append(claim_id),
    )
    monkeypatch.setattr(
        claims_agent,
        "calculate_fraud_risk",
        lambda claim_id: calls.append(claim_id),
    )
    monkeypatch.setattr(
        claims_agent,
        "search_policy",
        lambda *args: calls.append(args),
    )

    result = claims_agent.investigate_claim("CLM-UNKNOWN", "test-unknown")

    assert result["claim_id"] == "CLM-UNKNOWN"
    assert result["found"] is False
    assert result["error"] == "Claim not found: CLM-UNKNOWN"
    assert calls == []


def test_mcp_failure_returns_unable_to_verify(monkeypatch) -> None:
    async def failing_decoder(_vin):
        raise TimeoutError("test timeout")

    monkeypatch.setattr(claims_agent, "_call_mcp_decoder", failing_decoder)

    result = claims_agent.investigate_claim("CLM-MOT-0001", "test-mcp-failure")

    assert result["vehicle_verification"]["verification_status"] == "UNABLE_TO_VERIFY"


def test_invalid_mcp_response_returns_unable_to_verify(monkeypatch) -> None:
    async def invalid_decoder(_vin):
        return {"success": False, "error_type": "INVALID_VIN"}

    monkeypatch.setattr(claims_agent, "_call_mcp_decoder", invalid_decoder)

    result = claims_agent.investigate_claim("CLM-MOT-0001", "test-invalid-mcp")

    assert result["vehicle_verification"]["verification_status"] == "UNABLE_TO_VERIFY"


def test_vehicle_mismatch_is_preserved_without_changing_risk(monkeypatch) -> None:
    async def mismatching_decoder(_vin):
        return {
            "success": True,
            "vin": "SYNTHETICVIN00001",
            "manufacturer": "Other Manufacturer",
            "model": "208",
            "model_year": 2016,
        }

    monkeypatch.setattr(claims_agent, "_call_mcp_decoder", mismatching_decoder)

    result = claims_agent.investigate_claim("CLM-MOT-0001", "test-mismatch")

    assert result["vehicle_verification"]["verification_status"] == "MISMATCH"
    assert result["fraud_risk"]["risk_score"] == 0


def test_workflow_does_not_modify_claim_dataset() -> None:
    path = claims_agent.get_claim_details.__globals__["DATASET_PATH"]
    before = json.loads(path.read_text(encoding="utf-8"))
    claims_agent.investigate_claim("CLM-AUTO-0001", "test-read-only")
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after == before


def test_review_pauses_with_required_payload_and_accepts_report(monkeypatch) -> None:
    async def matching_decoder(_vin):
        return {
            "success": True,
            "vin": "SYNTHETICVIN00001",
            "manufacturer": "Peugeot",
            "model": "208",
            "model_year": 2016,
        }

    monkeypatch.setattr(claims_agent, "_call_mcp_decoder", matching_decoder)

    paused = claims_agent.investigate_claim("CLM-MOT-0001", "review-accept")
    interrupt_value = paused["__interrupt__"][0].value

    assert set(interrupt_value) == {
        "claim_id",
        "missing_documents",
        "fraud_indicator_findings",
        "investigation_priority_score",
        "vehicle_verification",
        "policy_citations",
    }
    assert interrupt_value["claim_id"] == "CLM-MOT-0001"
    original_risk = paused["fraud_risk"]
    resumed = claims_agent.resume_investigation("review-accept", "ACCEPT_REPORT")

    assert resumed["review_response"] == "ACCEPT_REPORT"
    assert resumed["review_status"] == "ACCEPTED_FOR_REPORTING"
    assert resumed["fraud_risk"] == original_risk
    assert resumed["claim_details"] == paused["claim_details"]


def test_review_can_request_more_information(monkeypatch) -> None:
    async def unavailable_decoder(_vin):
        return {"success": False, "error_type": "INVALID_VIN"}

    monkeypatch.setattr(claims_agent, "_call_mcp_decoder", unavailable_decoder)

    paused = claims_agent.investigate_claim("CLM-MOT-0001", "review-more-info")
    resumed = claims_agent.resume_investigation(
        "review-more-info", "REQUEST_MORE_INFO"
    )

    assert paused["__interrupt__"]
    assert resumed["review_response"] == "REQUEST_MORE_INFO"
    assert resumed["review_status"] == "NEEDS_MORE_INFORMATION"
    assert resumed["vehicle_verification"]["verification_status"] == "UNABLE_TO_VERIFY"


def test_unknown_claim_does_not_trigger_review() -> None:
    result = claims_agent.investigate_claim("CLM-UNKNOWN-REVIEW", "review-unknown")

    assert result["found"] is False
    assert "__interrupt__" not in result
