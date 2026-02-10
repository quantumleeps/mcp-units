"""Results persistence and RunResult dataclass."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

RESULTS_FILE = Path(__file__).parent / "results.json"


@dataclass
class RunResult:
    model: str
    condition: str
    problem_id: str
    predicted: float | None
    expected: float
    correct: bool
    response_text: str
    tool_calls: int
    input_tokens: int
    output_tokens: int


def result_key(model: str, condition: str, problem_id: str) -> str:
    return f"{model}|{condition}|{problem_id}"


def load_results() -> dict[str, Any]:
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text())
    return {"runs": [], "completed": []}


def save_results(results: dict[str, Any]) -> None:
    RESULTS_FILE.write_text(json.dumps(results, indent=2))


def append_result(results: dict[str, Any], run: RunResult) -> None:
    """Append a run result and save immediately."""
    results["runs"].append(asdict(run))
    key = result_key(run.model, run.condition, run.problem_id)
    results["completed"].append(key)
    save_results(results)
