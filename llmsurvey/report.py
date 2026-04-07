"""LLM-generated narrative summary of a survey run."""
from __future__ import annotations

import json
import logging

import replicate

from llmsurvey.models.results import RunResults, RunStats

logger = logging.getLogger(__name__)

_SUMMARY_MODEL = "meta/llama-4-scout"

_PROMPT_TEMPLATE = """\
You are a research assistant summarizing results from an LLM survey simulation study.

Below are the statistical results comparing LLM-generated response distributions to real survey data.

Results (JSON):
{results_json}

Stats (JSON):
{stats_json}

Write a concise 2-3 paragraph narrative summary that:
1. Describes how well each model matched the real survey distributions overall
2. Highlights any notable biases or divergences (questions where KL/JS divergence was highest)
3. Notes any models that performed notably better or worse

Be specific, cite question IDs and model names. Use plain prose, no bullet points.
"""


def generate_summary(
    results: RunResults,
    stats: RunStats,
    model_id: str = _SUMMARY_MODEL,
) -> str:
    results_json = json.dumps(
        {qid: {"real": qr.real, "models": qr.models} for qid, qr in results.questions.items()},
        indent=2,
    )
    stats_json = json.dumps(
        {
            qid: {
                mid: s.model_dump()
                for mid, s in model_stats.items()
            }
            for qid, model_stats in stats.questions.items()
        },
        indent=2,
    )
    prompt = _PROMPT_TEMPLATE.format(results_json=results_json, stats_json=stats_json)

    try:
        output = replicate.run(
            model_id,
            input={"prompt": prompt, "max_new_tokens": 512, "temperature": 0.3},
        )
        return "".join(output).strip()
    except Exception as exc:
        logger.error("Failed to generate summary: %s", exc)
        return f"[Summary generation failed: {exc}]"
