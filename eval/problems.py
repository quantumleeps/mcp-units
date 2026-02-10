"""SciBench problem loading and filtering."""

import logging
import math
import re
from dataclasses import dataclass
from typing import Any

from datasets import load_dataset

log = logging.getLogger(__name__)

UNIT_PATTERN = re.compile(
    r"\b(m/s|km/h|mph|ft/s|cm|mm|km|inch|inches|feet|foot|yard|mile|"
    r"atm|Pa|kPa|MPa|bar|psi|torr|mmHg|"
    r"mol/L|mg/L|g/L|ppm|"
    r"eV|keV|MeV|GeV|cal|kcal|BTU|"
    r"°C|°F|celsius|fahrenheit|kelvin|"
    r"lb|oz|gram|kg|ton|slug|"
    r"gallon|liter|litre|mL|cm\^?3|dm\^?3|"
    r"Hz|kHz|MHz|GHz|rpm|"
    r"kW|MW|hp|horsepower|"
    r"mA|kV|ohm|Ω)\b",
    re.IGNORECASE,
)


@dataclass
class Problem:
    problem_id: str
    problem_text: str
    answer_number: float
    unit: str
    source: str


def count_unit_types(text: str) -> int:
    """Count distinct unit types mentioned in problem text."""
    return len(set(m.group().lower() for m in UNIT_PATTERN.finditer(text)))


def load_problems(min_unit_types: int = 2) -> list[Problem]:
    """Load SciBench, filtering for problems with multiple unit types."""
    ds = load_dataset("xw27/scibench", split="train")
    problems = []
    skipped = 0
    for row in ds:  # type: ignore[union-attr]
        rec: dict[str, Any] = dict(row)  # type: ignore[arg-type]
        unit = (rec.get("unit") or "").strip()
        if not unit:
            continue
        try:
            answer = float(rec["answer_number"])
        except (ValueError, TypeError):
            continue
        if math.isnan(answer) or math.isinf(answer):
            continue
        if count_unit_types(rec["problem_text"]) < min_unit_types:
            skipped += 1
            continue
        problems.append(
            Problem(
                problem_id=rec["problemid"],
                problem_text=rec["problem_text"],
                answer_number=answer,
                unit=unit,
                source=rec.get("source", ""),
            )
        )
    log.info(
        "Loaded %d problems with %d+ unit types (%d skipped)",
        len(problems),
        min_unit_types,
        skipped,
    )
    return problems
