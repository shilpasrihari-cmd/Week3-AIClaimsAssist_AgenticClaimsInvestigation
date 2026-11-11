"""Small live compatibility test for Nebius Gemma tool calling."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import types

from dotenv import load_dotenv


try:
    import jiter  # type: ignore[import-not-found]
except ImportError:
    jiter_fallback = types.ModuleType("jiter")

    def _from_json(value, *args, **kwargs):
        return json.loads(value)

    jiter_fallback.from_json = _from_json
    sys.modules["jiter"] = jiter_fallback

from openai import APIConnectionError, OpenAI


ROOT = Path(__file__).resolve().parent
CLAIM_IDS = ["CLM-TEST-001", "CLM-TEST-002", "CLM-TEST-003"]
TOOL = {
    "type": "function",
    "function": {
        "name": "get_claim_status",
        "description": "Returns the status of a fictional insurance claim.",
        "parameters": {
            "type": "object",
            "properties": {"claim_id": {"type": "string"}},
            "required": ["claim_id"],
            "additionalProperties": False,
        },
    },
}


def _safe_error(error: Exception, api_key: str, base_url: str) -> str:
    message = str(error).replace(api_key, "[REDACTED_KEY]")
    return message.replace(base_url, "[REDACTED_BASE_URL]")[:300]


def main() -> int:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("NEBIUS_API_KEY")
    base_url = os.getenv("NEBIUS_BASE_URL")
    model = os.getenv("LLM_MODEL", "google/gemma-3-27b-it")

    if not api_key or not base_url:
        print("Configuration error: required Nebius settings are unavailable.")
        return 1

    base_url = base_url.strip()
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"

    client = OpenAI(api_key=api_key, base_url=base_url)
    successful_calls = 0

    print(f"model={model}")
    for request_number, claim_id in enumerate(CLAIM_IDS, start=1):
        prompt = f"Call get_claim_status to retrieve the status for fictional claim {claim_id}."
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                tools=[TOOL],
                tool_choice="auto",
                temperature=0,
                max_tokens=100,
            )
        except Exception as error:
            recommendation = (
                "INCONCLUSIVE"
                if isinstance(error, (ImportError, APIConnectionError, ConnectionError))
                else "NOT_SUPPORTED"
            )
            request_count = 0 if isinstance(error, ImportError) else request_number
            print(
                f"request={request_number} api_error={type(error).__name__} "
                f"detail={_safe_error(error, api_key, base_url)}"
            )
            print(f"requests={request_count} successful_structured_calls={successful_calls}")
            print(f"recommendation={recommendation}")
            return 1

        tool_calls = response.choices[0].message.tool_calls or []
        valid_call = False
        function_name = None
        argument_claim_id = None
        if tool_calls:
            function = tool_calls[0].function
            function_name = function.name
            try:
                arguments = json.loads(function.arguments)
                argument_claim_id = arguments.get("claim_id")
                valid_call = (
                    function_name == "get_claim_status"
                    and argument_claim_id == claim_id
                )
            except (TypeError, json.JSONDecodeError):
                valid_call = False

        successful_calls += int(valid_call)
        print(
            f"request={request_number} structured_tool_call={bool(tool_calls)} "
            f"function={function_name} claim_id_match={argument_claim_id == claim_id} "
            f"valid={valid_call}"
        )

    if successful_calls == len(CLAIM_IDS):
        recommendation = "SUPPORTED"
    elif successful_calls:
        recommendation = "UNRELIABLE"
    else:
        recommendation = "NOT_SUPPORTED"
    print(f"requests={len(CLAIM_IDS)} successful_structured_calls={successful_calls}")
    print(f"tool_choice_auto=tested recommendation={recommendation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
