"""Matplotlib/Seaborn chart generation."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from llmsurvey.models.results import RunResults, RunStats
from llmsurvey.models.survey import Survey


def plot_question(
    question_id: str,
    survey: Survey,
    results: RunResults,
    out_dir: Path,
) -> Path:
    """Grouped bar chart: real distribution vs each model, for one question."""
    question = survey.get_question(question_id)
    q_result = results.questions[question_id]

    options = question.options
    model_ids = list(q_result.models.keys())
    all_series = {"Real": [q_result.real.get(opt, 0.0) for opt in options]}
    for mid in model_ids:
        short = mid.split("/")[-1]
        all_series[short] = [q_result.models[mid].get(opt, 0.0) for opt in options]

    x = np.arange(len(options))
    n_groups = len(all_series)
    width = 0.8 / n_groups

    fig, ax = plt.subplots(figsize=(max(8, len(options) * 2), 5))
    for i, (label, values) in enumerate(all_series.items()):
        offset = (i - n_groups / 2 + 0.5) * width
        bars = ax.bar(x + offset, values, width, label=label)

    ax.set_xticks(x)
    ax.set_xticklabels(options, rotation=15, ha="right")
    ax.set_ylabel("Proportion")
    ax.set_ylim(0, 1)
    ax.set_title(f"{question_id}: {question.text[:80]}")
    ax.legend()
    fig.tight_layout()

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{question_id}_all_models.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def plot_heatmap(
    survey: Survey,
    stats: RunStats,
    out_dir: Path,
    metric: str = "js_divergence",
) -> Path:
    """Model × question heatmap of a divergence metric."""
    question_ids = list(stats.questions.keys())
    model_ids: list[str] = []
    for qid in question_ids:
        for mid in stats.questions[qid]:
            if mid not in model_ids:
                model_ids.append(mid)

    if not model_ids:
        raise ValueError("No model stats to plot")

    matrix = []
    for mid in model_ids:
        row = []
        for qid in question_ids:
            q_stats = stats.questions.get(qid, {}).get(mid)
            row.append(getattr(q_stats, metric, 0.0) if q_stats else 0.0)
        matrix.append(row)

    short_models = [m.split("/")[-1] for m in model_ids]
    fig, ax = plt.subplots(figsize=(max(6, len(question_ids) * 1.5), max(4, len(model_ids) * 0.8)))
    sns.heatmap(
        matrix,
        xticklabels=question_ids,
        yticklabels=short_models,
        annot=True,
        fmt=".3f",
        cmap="YlOrRd",
        ax=ax,
    )
    ax.set_title(f"Model × Question — {metric}")
    fig.tight_layout()

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "overview_heatmap.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def generate_all_charts(survey: Survey, results: RunResults, stats: RunStats, out_dir: Path) -> list[Path]:
    paths = []
    for qid in results.questions:
        paths.append(plot_question(qid, survey, results, out_dir))
    if stats.questions:
        paths.append(plot_heatmap(survey, stats, out_dir))
    return paths
