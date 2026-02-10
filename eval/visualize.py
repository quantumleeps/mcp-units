"""Generate grouped bar chart from evaluation results."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from eval.results import load_results

FIGURES_DIR = Path(__file__).parent / "figures"

MODEL_LABELS = {
    "claude-3-haiku-20240307": "3-Haiku",
    "claude-3-5-haiku-20241022": "3.5-Haiku",
    "claude-haiku-4-5": "4.5-Haiku",
    "claude-3-7-sonnet-20250219": "3.7-Sonnet",
    "claude-sonnet-4-5": "4.5-Sonnet",
    "claude-opus-4-6": "4.6-Opus",
}

MODEL_ORDER = list(MODEL_LABELS.keys())


def load_eval_results() -> dict:
    return load_results()


def compute_accuracy(runs: list[dict]) -> dict[str, dict[str, float]]:
    """Compute accuracy per model per condition."""
    accuracy: dict[str, dict[str, float]] = {}
    for model in MODEL_ORDER:
        accuracy[model] = {}
        for condition in ["baseline", "tool"]:
            model_runs = [
                r for r in runs if r["model"] == model and r["condition"] == condition
            ]
            if not model_runs:
                continue
            correct = sum(1 for r in model_runs if r["correct"])
            accuracy[model][condition] = 100 * correct / len(model_runs)
    return accuracy


def plot_grouped_bar(accuracy: dict[str, dict[str, float]]) -> None:
    """Generate grouped bar chart comparing baseline vs tool-augmented."""
    models = [m for m in MODEL_ORDER if m in accuracy and accuracy[m]]
    labels = [MODEL_LABELS[m] for m in models]

    baseline_scores = [accuracy[m].get("baseline", 0) for m in models]
    tool_scores = [accuracy[m].get("tool", 0) for m in models]

    x = np.arange(len(models))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))

    bars_baseline = ax.bar(
        x - width / 2,
        baseline_scores,
        width,
        label="Baseline",
        color="#94a3b8",
        edgecolor="white",
    )
    bars_tool = ax.bar(
        x + width / 2,
        tool_scores,
        width,
        label="With mcp-units",
        color="#3b82f6",
        edgecolor="white",
    )

    ax.set_ylabel("Accuracy (%)", fontsize=10)
    ax.set_title(
        "SciBench Physics Accuracy: Baseline vs Tool-Augmented",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.legend(fontsize=11)
    ax.set_ylim(0, 100)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    for bar in bars_baseline:
        height = bar.get_height()
        if height > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 1,
                f"{height:.0f}%",
                ha="center",
                va="bottom",
                fontsize=9,
            )
    for bar in bars_tool:
        height = bar.get_height()
        if height > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 1,
                f"{height:.0f}%",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    plt.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURES_DIR / "tool_impact.png"
    fig.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output}")


def plot_error_histogram(runs: list[dict]) -> None:
    """Compare relative error distributions: baseline vs tool-augmented.

    Generates two plots:
      1. All correct answers — does the tool tighten precision?
      2. All answers (log scale) — full error landscape.
    """
    # Compute relative errors, split by condition
    baseline_correct_err: list[float] = []
    tool_correct_err: list[float] = []
    baseline_all_err: list[float] = []
    tool_all_err: list[float] = []

    for r in runs:
        exp = r["expected"]
        pred = r["predicted"]
        if pred is None or exp == 0:
            continue
        rel_err = abs(pred - exp) / abs(exp) * 100  # as percentage

        if r["condition"] == "baseline":
            baseline_all_err.append(rel_err)
            if r["correct"]:
                baseline_correct_err.append(rel_err)
        else:
            tool_all_err.append(rel_err)
            if r["correct"]:
                tool_correct_err.append(rel_err)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # --- Plot 1: Correct answers precision ---
    fig, ax = plt.subplots(figsize=(10, 5))
    bins = np.linspace(0, 5, 26).tolist()
    ax.hist(
        baseline_correct_err,
        bins=bins,
        alpha=0.6,
        label=f"Baseline (n={len(baseline_correct_err)})",
        color="#94a3b8",
        edgecolor="white",
    )
    ax.hist(
        tool_correct_err,
        bins=bins,
        alpha=0.6,
        label=f"With mcp-units (n={len(tool_correct_err)})",
        color="#3b82f6",
        edgecolor="white",
    )
    ax.set_xlabel("Relative Error (%)", fontsize=10)
    ax.set_ylabel("Count", fontsize=10)
    ax.set_title(
        "Precision of Correct Answers: Baseline vs Tool-Augmented",
        fontsize=14,
        fontweight="bold",
    )
    ax.legend(fontsize=11)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    # Add median lines
    if baseline_correct_err:
        med_b = np.median(baseline_correct_err)
        ax.axvline(med_b, color="#64748b", linestyle="--", linewidth=1.5)
        ax.text(
            med_b + 0.05,
            ax.get_ylim()[1] * 0.9,
            f"median {med_b:.2f}%",
            color="#64748b",
            fontsize=9,
        )
    if tool_correct_err:
        med_t = np.median(tool_correct_err)
        ax.axvline(med_t, color="#2563eb", linestyle="--", linewidth=1.5)
        ax.text(
            med_t + 0.05,
            ax.get_ylim()[1] * 0.8,
            f"median {med_t:.2f}%",
            color="#2563eb",
            fontsize=9,
        )

    plt.tight_layout()
    out1 = FIGURES_DIR / "error_precision.png"
    fig.savefig(out1, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out1}")

    # --- Plot 2: All answers, log scale ---
    fig, ax = plt.subplots(figsize=(10, 5))
    log_bins = np.logspace(-2, 4, 40).tolist()
    ax.hist(
        baseline_all_err,
        bins=log_bins,
        alpha=0.6,
        label=f"Baseline (n={len(baseline_all_err)})",
        color="#94a3b8",
        edgecolor="white",
    )
    ax.hist(
        tool_all_err,
        bins=log_bins,
        alpha=0.6,
        label=f"With mcp-units (n={len(tool_all_err)})",
        color="#3b82f6",
        edgecolor="white",
    )
    ax.set_xscale("log")
    ax.set_xlabel("Relative Error (%, log scale)", fontsize=10)
    ax.set_ylabel("Count", fontsize=10)
    ax.set_title(
        "Error Distribution: All Answers (Baseline vs Tool-Augmented)",
        fontsize=14,
        fontweight="bold",
    )
    ax.axvline(5, color="#ef4444", linestyle=":", linewidth=1.5, label="5% threshold")
    ax.legend(fontsize=11)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    plt.tight_layout()
    out2 = FIGURES_DIR / "error_distribution.png"
    fig.savefig(out2, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out2}")


def print_summary(runs: list[dict], accuracy: dict[str, dict[str, float]]) -> None:
    """Print a text summary table."""
    print("\n┌─────────────────────┬──────────┬──────────┬────────┐")
    print("│ Model               │ Baseline │ w/ Tool  │  Δ     │")
    print("├─────────────────────┼──────────┼──────────┼────────┤")
    for model in MODEL_ORDER:
        if model not in accuracy or not accuracy[model]:
            continue
        label = MODEL_LABELS[model]
        base = accuracy[model].get("baseline", 0)
        tool = accuracy[model].get("tool", 0)
        delta = tool - base
        sign = "+" if delta >= 0 else ""
        print(
            f"│ {label:<19} │ {base:>6.1f}%  │ {tool:>6.1f}%  │ {sign}{delta:>5.1f}% │"
        )
    print("└─────────────────────┴──────────┴──────────┴────────┘")

    total_input = sum(r["input_tokens"] for r in runs)
    total_output = sum(r["output_tokens"] for r in runs)
    print(f"\nTotal tokens: {total_input:,} input + {total_output:,} output")


def main() -> None:
    results = load_eval_results()
    runs = results["runs"]
    accuracy = compute_accuracy(runs)
    print_summary(runs, accuracy)
    plot_grouped_bar(accuracy)
    plot_error_histogram(runs)


if __name__ == "__main__":
    main()
