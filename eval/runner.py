"""CLI entry point and async evaluation orchestration."""

import argparse
import asyncio
import logging
from typing import Any

import anthropic
from dotenv import load_dotenv

from eval.mcp_tools import MCPToolExecutor
from eval.problems import Problem, load_problems
from eval.results import RunResult, append_result, load_results, result_key
from eval.scorer import extract_answer, is_correct

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

MODELS = [
    "claude-3-haiku-20240307",
    "claude-3-5-haiku-20241022",
    "claude-haiku-4-5",
    "claude-3-7-sonnet-20250219",
    "claude-sonnet-4-5",
    "claude-opus-4-6",
]

CONDITIONS = ["baseline", "tool"]

SYSTEM_PROMPT = (
    "You are solving a college-level physics or chemistry problem. "
    "Work through the problem step by step. "
    "Express your final answer as a decimal number. "
    "Conclude with: The answer is therefore \\boxed{NUMBER}"
)

MAX_TOOL_CALLS = 5

# Seconds between API calls — stays under OTPM limits at Tier 1.
CALL_DELAY: dict[str, float] = {
    "haiku": 3.0,
    "sonnet": 4.0,
    "opus": 4.0,
}


def _delay_for_model(model: str) -> float:
    for family, delay in CALL_DELAY.items():
        if family in model:
            return delay
    return 4.0


async def run_problem(
    api: anthropic.AsyncAnthropic,
    model: str,
    condition: str,
    problem: Problem,
    executor: MCPToolExecutor,
) -> RunResult:
    """Run a single problem through a model with or without tools."""
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                f"{problem.problem_text}\n\nExpress your answer in {problem.unit}."
            ),
        }
    ]

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": 2048,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }
    if condition == "tool":
        kwargs["tools"] = executor.anthropic_tools

    total_tool_calls = 0
    total_input = 0
    total_output = 0
    final_text = ""
    delay = _delay_for_model(model)

    for _ in range(MAX_TOOL_CALLS + 1):
        response = await api.messages.create(**kwargs)
        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens
        await asyncio.sleep(delay)

        text_parts = []
        tool_uses = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        final_text += "\n".join(text_parts)

        if not tool_uses or response.stop_reason != "tool_use":
            break

        total_tool_calls += len(tool_uses)
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tu in tool_uses:
            result_str = await executor.call_tool(tu.name, tu.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": result_str,
                }
            )
        messages.append({"role": "user", "content": tool_results})
        kwargs["messages"] = messages

    predicted = extract_answer(final_text)
    correct = is_correct(predicted, problem.answer_number)

    return RunResult(
        model=model,
        condition=condition,
        problem_id=problem.problem_id,
        predicted=predicted,
        expected=problem.answer_number,
        correct=correct,
        response_text=final_text[:500],
        tool_calls=total_tool_calls,
        input_tokens=total_input,
        output_tokens=total_output,
    )


async def run_eval(args: argparse.Namespace) -> None:
    """Main async evaluation loop."""
    problems = load_problems()
    if args.limit > 0:
        problems = problems[: args.limit]

    if args.dry_run:
        log.info("Problems: %d", len(problems))
        log.info("Models: %s", args.models)
        log.info("Conditions: %s", args.conditions)
        log.info(
            "Total runs: %d",
            len(problems) * len(args.models) * len(args.conditions),
        )
        async with MCPToolExecutor() as executor:
            log.info("Tools: %s", [t["name"] for t in executor.anthropic_tools])
        log.info("Sample: %s", problems[0].problem_text[:200])
        log.info("Answer: %s %s", problems[0].answer_number, problems[0].unit)
        return

    api = anthropic.AsyncAnthropic()
    results = load_results()
    completed = set(results["completed"])

    total = len(problems) * len(args.models) * len(args.conditions)
    done = 0

    async with MCPToolExecutor() as executor:
        for model in args.models:
            for condition in args.conditions:
                for problem in problems:
                    key = result_key(model, condition, problem.problem_id)
                    if key in completed:
                        done += 1
                        continue

                    done += 1
                    log.info(
                        "[%d/%d] %s | %s | %s",
                        done,
                        total,
                        model,
                        condition,
                        problem.problem_id,
                    )

                    try:
                        run = await run_problem(
                            api, model, condition, problem, executor
                        )
                        append_result(results, run)
                        completed.add(key)

                        status = "+" if run.correct else "-"
                        log.info(
                            "  %s predicted=%s expected=%s tools=%d",
                            status,
                            run.predicted,
                            run.expected,
                            run.tool_calls,
                        )
                    except anthropic.RateLimitError:
                        log.warning("  Rate limited — backing off 60s")
                        await asyncio.sleep(60)
                    except anthropic.APIError as e:
                        log.error("  API error: %s", e)

    log.info("\n-- Summary --")
    for model in args.models:
        for condition in args.conditions:
            runs = [
                r
                for r in results["runs"]
                if r["model"] == model and r["condition"] == condition
            ]
            if not runs:
                continue
            correct_count = sum(1 for r in runs if r["correct"])
            total_tokens = sum(r["input_tokens"] + r["output_tokens"] for r in runs)
            log.info(
                "%s | %s: %d/%d (%.1f%%) | %d tokens",
                model,
                condition,
                correct_count,
                len(runs),
                100 * correct_count / len(runs),
                total_tokens,
            )


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="SciBench tool impact evaluation")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--models", nargs="+", default=MODELS)
    parser.add_argument("--conditions", nargs="+", default=CONDITIONS)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(run_eval(args))


if __name__ == "__main__":
    main()
