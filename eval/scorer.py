"""Answer extraction and correctness scoring."""

import re

BOXED_RE = re.compile(r"\\boxed\{([^}]+)\}")
FINAL_NUMBER_RE = re.compile(
    r"(?:answer is|therefore|=)\s*[~≈]?\s*"
    r"(-?[\d]+\.?[\d]*(?:[eE][+-]?\d+)?)",
    re.IGNORECASE,
)
LAST_NUMBER_RE = re.compile(r"(-?[\d]+\.?[\d]*(?:[eE][+-]?\d+)?)")


def extract_answer(text: str) -> float | None:
    """Extract numerical answer from model response.

    Tries in order: \\boxed{}, "answer is / therefore / =" pattern, last number.
    """
    m = BOXED_RE.search(text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    m = FINAL_NUMBER_RE.search(text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    numbers = LAST_NUMBER_RE.findall(text)
    if numbers:
        try:
            return float(numbers[-1].replace(",", ""))
        except ValueError:
            pass
    return None


def is_correct(predicted: float | None, expected: float, tol: float = 0.05) -> bool:
    """Check if predicted answer matches expected within relative tolerance."""
    if predicted is None:
        return False
    if expected == 0:
        return abs(predicted) < 1e-6
    return abs(predicted - expected) / abs(expected) <= tol
