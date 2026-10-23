"""A tool-calling loop on Foundry's Responses API: the model asks for tools, we run them, it answers."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from matchvoice.agents.client import model_deployment, project_client
from matchvoice.tools.match_tools import TOOLS, MatchContext, call_tool

MAX_STEPS = 5  # rounds of tool calls before the model must answer


def function_specs(names: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": n,
            "description": TOOLS[n]["description"],
            "parameters": TOOLS[n]["parameters"],
            "strict": False,
        }
        for n in names
    ]


def run_with_tools[T: BaseModel](
    instructions: str,
    user_input: str,
    tool_names: list[str],
    ctx: MatchContext,
    output: type[T],
) -> tuple[T | None, list[dict[str, Any]], list[str]]:
    """Returns (parsed answer, every tool result, names of the tools called)."""
    specs = function_specs(tool_names)
    results: list[dict[str, Any]] = []
    used: list[str] = []
    with project_client() as project, project.get_openai_client() as openai:

        def ask(**kwargs: Any) -> Any:
            return openai.responses.parse(
                model=model_deployment(), instructions=instructions, tools=specs, text_format=output, **kwargs
            )

        response = ask(input=user_input)
        for _ in range(MAX_STEPS):
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                break
            outputs = []
            for call in calls:
                try:
                    args = json.loads(call.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = call_tool(ctx, call.name, args)
                results.append(result)
                used.append(call.name)
                payload = json.dumps(result, ensure_ascii=False)
                outputs.append({"type": "function_call_output", "call_id": call.call_id, "output": payload})
            response = ask(previous_response_id=response.id, input=outputs)
        return response.output_parsed, results, used
