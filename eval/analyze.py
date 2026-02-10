"""Analyze eval results for the mcp-units report.

Reads results.json and prints a comprehensive breakdown of baseline vs tool
performance, failure patterns, regressions, improvements, and MCP tool errors.

Usage:
    uv run python eval/analyze.py
    uv run python eval/analyze.py --results path/to/results.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


def load(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    return data["runs"]


# ── helpers ──────────────────────────────────────────────────────────────


def _pct(n: int, d: int) -> str:
    return f"{n / d * 100:.1f}%" if d else "n/a"


def _ratio(predicted: float, expected: float) -> float | None:
    if expected == 0:
        return None
    return abs(predicted / expected)


# ── sections ─────────────────────────────────────────────────────────────


def section_overall(runs: list[dict]) -> None:
    print("\n## 1. Overall Pass/Fail by Condition\n")
    by_cond: dict[str, dict] = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in runs:
        by_cond[r["condition"]]["total"] += 1
        if r["correct"]:
            by_cond[r["condition"]]["correct"] += 1

    print(f"{'Condition':<12} {'Correct':>8} {'Total':>6} {'Rate':>8}")
    print("-" * 38)
    for cond in ["baseline", "tool"]:
        c = by_cond[cond]
        rate = _pct(c["correct"], c["total"])
        print(f"{cond:<12} {c['correct']:>8} {c['total']:>6} {rate:>8}")


def section_by_model(runs: list[dict]) -> None:
    print("\n## 2. Pass/Fail by Model AND Condition\n")
    grid: dict[str, dict[str, dict]] = defaultdict(
        lambda: defaultdict(lambda: {"correct": 0, "total": 0})
    )
    for r in runs:
        grid[r["model"]][r["condition"]]["total"] += 1
        if r["correct"]:
            grid[r["model"]][r["condition"]]["correct"] += 1

    print(f"{'Model':<35} {'Baseline':>12} {'Tool':>12} {'Delta':>8}")
    print("-" * 70)
    for model in sorted(grid):
        b = grid[model]["baseline"]
        t = grid[model]["tool"]
        b_rate = b["correct"] / b["total"] * 100 if b["total"] else 0
        t_rate = t["correct"] / t["total"] * 100 if t["total"] else 0
        delta = t_rate - b_rate if t["total"] else float("nan")
        b_str = f"{b['correct']}/{b['total']} ({b_rate:.1f}%)"
        t_str = (
            f"{t['correct']}/{t['total']} ({t_rate:.1f}%)" if t["total"] else "not run"
        )
        d_str = f"{delta:+.1f}pp" if t["total"] else "n/a"
        print(f"{model:<35} {b_str:>12} {t_str:>12} {d_str:>8}")


def section_oops(runs: list[dict]) -> None:
    print("\n## 3. 'Oops' Entries (tool errors narrated by model)\n")
    oops = [r for r in runs if "Oops" in r.get("response_text", "")]
    print(f"Total: {len(oops)}")
    if not oops:
        return

    by_model: dict[str, int] = defaultdict(int)
    for r in oops:
        by_model[r["model"]] += 1
    for model, count in sorted(by_model.items()):
        print(f"  {model}: {count}")

    print(f"\n{'Problem':<20} {'Model':<35} {'Correct':>8} {'Tool Calls':>11}")
    print("-" * 78)
    for r in oops:
        print(
            f"{r['problem_id']:<20} {r['model']:<35} "
            f"{str(r['correct']):>8} {r['tool_calls']:>11}"
        )


def section_conversion_errors(runs: list[dict]) -> None:
    print("\n## 4. Unit Conversion Error Patterns in response_text\n")
    patterns = {
        "cm3 / cm³ (not recognized)": r"cm3|cm³",
        "not supported": r"not supported",
        "incompatible units": r"incompatible units",
        "UndefinedUnitError": r"UndefinedUnitError|not defined in the unit registry",
        "Celsius (not recognized)": r"(?i)celsius.{0,30}(not|error|fail|recognize)",
        "Torr (not recognized)": r"(?i)torr.{0,30}(not|error|fail|recognize)",
    }
    for label, pat in patterns.items():
        matches = [r for r in runs if re.search(pat, r.get("response_text", ""))]
        if matches:
            print(f"  {label}: {len(matches)} occurrences")
            for r in matches[:3]:
                print(f"    - {r['problem_id']} ({r['model']}, {r['condition']})")


def section_tool_called_but_wrong(runs: list[dict]) -> None:
    print("\n## 5. Tool Called but Wrong (tool_calls > 0, correct = false)\n")
    bad = [r for r in runs if r["tool_calls"] > 0 and not r["correct"]]
    print(f"Total: {len(bad)}")

    by_problem: dict[str, int] = defaultdict(int)
    for r in bad:
        by_problem[r["problem_id"]] += 1

    worst = sorted(by_problem.items(), key=lambda x: -x[1])[:10]
    print(f"\n{'Problem':<20} {'Models Failed':>14}")
    print("-" * 36)
    for pid, count in worst:
        print(f"{pid:<20} {count:>14}")


def _build_paired(runs: list[dict]) -> dict[str, dict[str, dict]]:
    """Build {(model, problem_id): {condition: run}} lookup."""
    paired: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in runs:
        key = f"{r['model']}|{r['problem_id']}"
        paired[key][r["condition"]] = r
    return paired


def section_regressions(runs: list[dict]) -> None:
    print("\n## 6. Regressions (baseline correct, tool wrong)\n")
    paired = _build_paired(runs)
    regressions = []
    for conds in paired.values():
        if "baseline" in conds and "tool" in conds:
            if conds["baseline"]["correct"] and not conds["tool"]["correct"]:
                regressions.append(conds)

    print(f"Total: {len(regressions)}")
    by_model: dict[str, int] = defaultdict(int)
    for r in regressions:
        by_model[r["tool"]["model"]] += 1
    for model, count in sorted(by_model.items(), key=lambda x: -x[1]):
        print(f"  {model}: {count}")

    print(
        f"\n{'Problem':<20} {'Model':<30} "
        f"{'Base Pred':>10} {'Tool Pred':>10} {'Expected':>10}"
    )
    print("-" * 84)
    for r in sorted(regressions, key=lambda x: x["tool"]["problem_id"]):
        b, t = r["baseline"], r["tool"]
        print(
            f"{t['problem_id']:<20} {t['model']:<30} "
            f"{b['predicted']:>10.3g} {t['predicted']:>10.3g} {t['expected']:>10.3g}"
        )


def section_improvements(runs: list[dict]) -> None:
    print("\n## 7. Improvements (baseline wrong, tool correct)\n")
    paired = _build_paired(runs)
    improvements = []
    for conds in paired.values():
        if "baseline" in conds and "tool" in conds:
            if not conds["baseline"]["correct"] and conds["tool"]["correct"]:
                improvements.append(conds)

    print(f"Total: {len(improvements)}")
    by_model: dict[str, int] = defaultdict(int)
    for r in improvements:
        by_model[r["tool"]["model"]] += 1
    for model, count in sorted(by_model.items(), key=lambda x: -x[1]):
        print(f"  {model}: {count}")

    print(
        f"\n{'Problem':<20} {'Model':<30} "
        f"{'Base Pred':>10} {'Tool Pred':>10} {'Expected':>10} {'Calls':>6}"
    )
    print("-" * 90)
    for r in sorted(improvements, key=lambda x: x["tool"]["problem_id"]):
        b, t = r["baseline"], r["tool"]
        print(
            f"{t['problem_id']:<20} {t['model']:<30} "
            f"{b['predicted']:>10.3g} {t['predicted']:>10.3g} "
            f"{t['expected']:>10.3g} {t['tool_calls']:>6}"
        )


def section_magnitude_errors(runs: list[dict]) -> None:
    print("\n## 8. Magnitude Errors in Tool Condition (>100x off)\n")
    wild = []
    for r in runs:
        if r["condition"] != "tool" or r["correct"]:
            continue
        ratio = _ratio(r["predicted"], r["expected"])
        if ratio is not None and (ratio > 100 or ratio < 0.01):
            wild.append((r, ratio))

    wild.sort(key=lambda x: -x[1])
    print(f"Total: {len(wild)}")
    print(
        f"\n{'Problem':<20} {'Model':<30} "
        f"{'Predicted':>12} {'Expected':>12} {'Ratio':>10}"
    )
    print("-" * 88)
    for r, ratio in wild[:15]:
        print(
            f"{r['problem_id']:<20} {r['model']:<30} "
            f"{r['predicted']:>12.4g} {r['expected']:>12.4g} {ratio:>10.1f}x"
        )


def section_consistent_flips(runs: list[dict]) -> None:
    print("\n## 9. Problems Consistently Helped by Tool (2+ models flipped)\n")
    paired = _build_paired(runs)

    # group flips by problem_id
    flips_by_problem: dict[str, list[dict]] = defaultdict(list)
    for conds in paired.values():
        if "baseline" in conds and "tool" in conds:
            if not conds["baseline"]["correct"] and conds["tool"]["correct"]:
                pid = conds["tool"]["problem_id"]
                flips_by_problem[pid].append(conds)

    multi = {pid: f for pid, f in flips_by_problem.items() if len(f) >= 2}
    print(f"Problems with 2+ models flipped: {len(multi)}")

    for pid in sorted(multi, key=lambda p: -len(multi[p])):
        flips = multi[pid]
        print(f"\n  Problem {pid} — {len(flips)} models flipped:")
        hdr = f"    {'Model':<30} {'Base Pred':>10} {'Tool Pred':>10}"
        print(f"{hdr} {'Expected':>10} {'Calls':>6}")
        for f in flips:
            b, t = f["baseline"], f["tool"]
            print(
                f"    {t['model']:<30} {b['predicted']:>10.3g} "
                f"{t['predicted']:>10.3g} {t['expected']:>10.3g} {t['tool_calls']:>6}"
            )


def section_problem_difficulty(runs: list[dict]) -> None:
    print("\n## 10. Problem Difficulty Distribution\n")

    # Per-problem: how many models solve it in each condition
    base_solves: dict[str, int] = defaultdict(int)
    tool_solves: dict[str, int] = defaultdict(int)
    base_attempts: dict[str, int] = defaultdict(int)
    tool_attempts: dict[str, int] = defaultdict(int)

    for r in runs:
        pid = r["problem_id"]
        if r["condition"] == "baseline":
            base_attempts[pid] += 1
            if r["correct"]:
                base_solves[pid] += 1
        else:
            tool_attempts[pid] += 1
            if r["correct"]:
                tool_solves[pid] += 1

    all_pids = sorted(set(base_attempts) | set(tool_attempts))

    # Bucket problems by baseline solve rate
    buckets = {
        "0% (unsolved)": [],
        "1-25%": [],
        "26-50%": [],
        "51-75%": [],
        "76-100%": [],
    }
    for pid in all_pids:
        ba = base_attempts[pid]
        rate = base_solves[pid] / ba * 100 if ba else 0
        if rate == 0:
            buckets["0% (unsolved)"].append(pid)
        elif rate <= 25:
            buckets["1-25%"].append(pid)
        elif rate <= 50:
            buckets["26-50%"].append(pid)
        elif rate <= 75:
            buckets["51-75%"].append(pid)
        else:
            buckets["76-100%"].append(pid)

    print("Baseline solve-rate distribution:")
    for label, pids in buckets.items():
        print(f"  {label:<16} {len(pids):>3} problems")

    # Show tool's effect per difficulty tier
    print(f"\n{'Difficulty tier':<16} {'Base rate':>10} {'Tool rate':>10} {'Delta':>8}")
    print("-" * 48)
    for label, pids in buckets.items():
        if not pids:
            continue
        b_c = sum(base_solves[p] for p in pids)
        b_t = sum(base_attempts[p] for p in pids)
        t_c = sum(tool_solves[p] for p in pids)
        t_t = sum(tool_attempts[p] for p in pids)
        b_r = b_c / b_t * 100 if b_t else 0
        t_r = t_c / t_t * 100 if t_t else 0
        d = t_r - b_r if t_t else float("nan")
        print(f"{label:<16} {b_r:>9.1f}% {t_r:>9.1f}% {d:>+7.1f}pp")

    # Hardest problems: wrong on ALL models in BOTH conditions
    universal_hard = [
        pid for pid in all_pids if base_solves[pid] == 0 and tool_solves[pid] == 0
    ]
    print(f"\nUniversally unsolved (0% both conditions): {len(universal_hard)}")
    for pid in universal_hard[:10]:
        print(f"  {pid}")
    if len(universal_hard) > 10:
        print(f"  ... and {len(universal_hard) - 10} more")

    # Easiest: solved by all models in both conditions
    universal_easy = [
        pid
        for pid in all_pids
        if base_attempts[pid] > 0
        and tool_attempts[pid] > 0
        and base_solves[pid] == base_attempts[pid]
        and tool_solves[pid] == tool_attempts[pid]
    ]
    print(f"\nUniversally solved (100% both conditions): {len(universal_easy)}")
    for pid in universal_easy[:10]:
        print(f"  {pid}")
    if len(universal_easy) > 10:
        print(f"  ... and {len(universal_easy) - 10} more")


def section_tool_call_correlation(runs: list[dict]) -> None:
    print("\n## 11. Tool Call Count vs Correctness\n")
    tool_runs = [r for r in runs if r["condition"] == "tool"]

    by_count: dict[int, dict] = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in tool_runs:
        by_count[r["tool_calls"]]["total"] += 1
        if r["correct"]:
            by_count[r["tool_calls"]]["correct"] += 1

    print(f"{'Tool calls':>11} {'Correct':>8} {'Total':>6} {'Rate':>8}")
    print("-" * 36)
    for n in sorted(by_count):
        c = by_count[n]
        rate = _pct(c["correct"], c["total"])
        print(f"{n:>11} {c['correct']:>8} {c['total']:>6} {rate:>8}")


def section_error_distribution(runs: list[dict]) -> None:
    print("\n## 12. Error Distribution\n")

    # Compute relative error for every run with nonzero expected
    all_errors: list[tuple[dict, float]] = []
    for r in runs:
        exp = r["expected"]
        pred = r["predicted"]
        if pred is None or exp == 0:
            continue
        rel_err = abs(pred - exp) / abs(exp)
        all_errors.append((r, rel_err))

    if not all_errors:
        print("No runs to analyze.")
        return

    # Precision of correct answers
    correct = [(r, e) for r, e in all_errors if r["correct"]]
    print("Precision of correct answers:")
    precision_bands = [
        ("Exact (0% error)", 0.0, 0.0),
        ("<=0.1%", 0.0, 0.001),
        ("<=1%", 0.0, 0.01),
        ("<=2%", 0.0, 0.02),
        ("<=5% (full tolerance)", 0.0, 0.05),
    ]
    print(f"  {'Band':<26} {'Baseline':>9} {'Tool':>9} {'Total':>9}")
    print("  " + "-" * 56)
    for label, lo, hi in precision_bands:
        b = sum(1 for r, e in correct if lo <= e <= hi and r["condition"] == "baseline")
        t = sum(1 for r, e in correct if lo <= e <= hi and r["condition"] == "tool")
        print(f"  {label:<26} {b:>9} {t:>9} {b + t:>9}")

    b_total = sum(1 for r, _ in correct if r["condition"] == "baseline")
    t_total = sum(1 for r, _ in correct if r["condition"] == "tool")
    print(f"  {'Total correct':<26} {b_total:>9} {t_total:>9} {len(correct):>9}")

    # Error buckets for incorrect answers
    incorrect = [(r, e) for r, e in all_errors if not r["correct"]]
    print("\nError magnitude of incorrect answers:")
    error_bands = [
        ("5-10% (near miss)", 0.05, 0.10),
        ("10-50%", 0.10, 0.50),
        ("50-100%", 0.50, 1.00),
        (">100% (order-of-mag)", 1.00, float("inf")),
    ]
    print(f"  {'Band':<26} {'Baseline':>9} {'Tool':>9} {'Total':>9}")
    print("  " + "-" * 56)
    for label, lo, hi in error_bands:
        b = sum(
            1 for r, e in incorrect if lo < e <= hi and r["condition"] == "baseline"
        )
        t = sum(1 for r, e in incorrect if lo < e <= hi and r["condition"] == "tool")
        print(f"  {label:<26} {b:>9} {t:>9} {b + t:>9}")


def section_sign_errors(runs: list[dict]) -> None:
    print("\n## 13. Sign Errors (opposite sign, often correct magnitude)\n")

    sign_errors: list[tuple[dict, float]] = []
    for r in runs:
        if r["correct"]:
            continue
        exp, pred = r["expected"], r["predicted"]
        if pred is None or exp == 0:
            continue
        if pred * exp >= 0:
            continue
        rel_err = abs(pred - exp) / abs(exp) * 100
        sign_errors.append((r, rel_err))

    total_incorrect = sum(1 for r in runs if not r["correct"] and r["expected"] != 0)
    print(f"Total sign errors: {len(sign_errors)} / {total_incorrect} incorrect")
    print(f"  ({len(sign_errors) / total_incorrect * 100:.0f}% of all failures)")

    if not sign_errors:
        return

    # Where do sign errors cluster?
    bands = [
        ("~100% (tiny pred, large exp)", 100, 105),
        ("105-190%", 105, 190),
        ("~200% (pure sign flip)", 190, 210),
        (">210%", 210, float("inf")),
    ]
    print(f"\n  {'Error band':<34} {'Count':>6}")
    print("  " + "-" * 42)
    for label, lo, hi in bands:
        n = sum(1 for _, e in sign_errors if lo <= e < hi)
        print(f"  {label:<34} {n:>6}")

    # Which problems are most affected?
    by_problem: dict[str, int] = defaultdict(int)
    for r, _ in sign_errors:
        by_problem[r["problem_id"]] += 1

    print(f"\n  {'Problem':<20} {'Sign errors':>12} {'Baseline':>9} {'Tool':>9}")
    print("  " + "-" * 54)
    for pid, count in sorted(by_problem.items(), key=lambda x: -x[1]):
        b = sum(
            1
            for r, _ in sign_errors
            if r["problem_id"] == pid and r["condition"] == "baseline"
        )
        t = count - b
        print(f"  {pid:<20} {count:>12} {b:>9} {t:>9}")

    # Does the tool help or hurt sign errors?
    b_total = sum(1 for _, e in sign_errors if _["condition"] == "baseline")
    t_total = len(sign_errors) - b_total
    print(f"\n  Baseline sign errors: {b_total}")
    print(f"  Tool sign errors:    {t_total}")


def section_perfect_rescues(runs: list[dict]) -> None:
    print("\n## 14. Perfect Rescues (tool fixed every failing model)\n")
    paired = _build_paired(runs)

    # Per problem: track which models failed baseline, which tool fixed
    base_fails: dict[str, list[str]] = defaultdict(list)
    tool_fixes: dict[str, list[str]] = defaultdict(list)

    for conds in paired.values():
        if "baseline" not in conds or "tool" not in conds:
            continue
        pid = conds["baseline"]["problem_id"]
        model = conds["baseline"]["model"]
        if not conds["baseline"]["correct"]:
            base_fails[pid].append(model)
            if conds["tool"]["correct"]:
                tool_fixes[pid].append(model)

    # Perfect rescue: every model that failed baseline was fixed by tool
    perfect = {
        pid: models
        for pid, models in base_fails.items()
        if len(models) > 0 and set(models) == set(tool_fixes.get(pid, []))
    }

    print(f"Total: {len(perfect)}")
    print(f"\n{'Problem':<20} {'Fails Fixed':>12} {'Models rescued'}")
    print("-" * 70)
    for pid in sorted(perfect, key=lambda p: -len(perfect[p])):
        models = perfect[pid]
        names = ", ".join(
            m.replace("claude-", "")
            .replace("-20240307", "")
            .replace("-20241022", "")
            .replace("-20250219", "")
            for m in sorted(models)
        )
        print(f"{pid:<20} {len(models):>12} {names}")


def section_completeness(runs: list[dict]) -> None:
    print("\n## 15. Eval Completeness\n")
    grid: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in runs:
        grid[r["model"]][r["condition"]] += 1

    print(f"{'Model':<35} {'Baseline':>10} {'Tool':>10}")
    print("-" * 58)
    for model in sorted(grid):
        print(f"{model:<35} {grid[model]['baseline']:>10} {grid[model]['tool']:>10}")
    print(f"\nTotal runs: {len(runs)}")


def section_token_usage(runs: list[dict]) -> None:
    print("\n## 16. Token Usage (baseline vs tool)\n")
    usage: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for r in runs:
        usage[r["condition"]]["input"].append(r.get("input_tokens", 0))
        usage[r["condition"]]["output"].append(r.get("output_tokens", 0))

    for cond in ["baseline", "tool"]:
        inp = usage[cond]["input"]
        out = usage[cond]["output"]
        if not inp:
            continue
        print(f"  {cond}:")
        inp_mean = sum(inp) / len(inp)
        inp_med = sorted(inp)[len(inp) // 2]
        out_mean = sum(out) / len(out)
        out_med = sorted(out)[len(out) // 2]
        total_mean = (sum(inp) + sum(out)) / len(inp)
        print(f"    Input tokens  — mean: {inp_mean:.0f}, median: {inp_med}")
        print(f"    Output tokens — mean: {out_mean:.0f}, median: {out_med}")
        print(f"    Total tokens  — mean: {total_mean:.0f}")


# ── main ─────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results",
        type=Path,
        default=Path(__file__).parent / "results.json",
        help="Path to results.json",
    )
    args = parser.parse_args()

    runs = load(args.results)
    print(f"# MCP-Units Eval Analysis — {len(runs)} runs")

    section_overall(runs)
    section_by_model(runs)
    section_oops(runs)
    section_conversion_errors(runs)
    section_tool_called_but_wrong(runs)
    section_regressions(runs)
    section_improvements(runs)
    section_magnitude_errors(runs)
    section_consistent_flips(runs)
    section_problem_difficulty(runs)
    section_tool_call_correlation(runs)
    section_error_distribution(runs)
    section_sign_errors(runs)
    section_perfect_rescues(runs)
    section_completeness(runs)
    section_token_usage(runs)

    print("\n---\nDone.")


if __name__ == "__main__":
    main()
