"""Statistical comparison between LLM and real survey distributions."""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

from llmsurvey.models.results import ModelQuestionStats, RawResponses, RunResults, RunStats
from llmsurvey.models.survey import Survey


def _kl_divergence(p: list[float], q: list[float], eps: float = 1e-10) -> float:
    """KL(p || q) — how much q differs from p (real distribution as reference)."""
    total = 0.0
    for pi, qi in zip(p, q):
        pi = max(pi, eps)
        qi = max(qi, eps)
        total += pi * math.log(pi / qi)
    return total


def _js_divergence(p: list[float], q: list[float]) -> float:
    """Jensen-Shannon divergence (symmetric, bounded [0, 1])."""
    m = [(pi + qi) / 2 for pi, qi in zip(p, q)]
    return (_kl_divergence(p, m) + _kl_divergence(q, m)) / 2


def _bias_direction(per_option_delta: dict[str, float]) -> str:
    """Heuristic: flag systematic lean based on net delta sign and magnitude."""
    positive_keys = [k for k, v in per_option_delta.items() if v > 0.05]
    if not positive_keys:
        return "neutral"
    # Crude heuristic: if model over-represents liberal-leaning options
    liberal_signals = {"Satisfied", "Support", "Approve", "Yes", "Agree", "Liberal", "Democrat"}
    conservative_signals = {"Dissatisfied", "Oppose", "Disapprove", "No", "Disagree", "Conservative", "Republican"}
    lib_delta = sum(per_option_delta.get(k, 0) for k in liberal_signals)
    con_delta = sum(per_option_delta.get(k, 0) for k in conservative_signals)
    if lib_delta > 0.05 and lib_delta > con_delta:
        return "slightly_liberal"
    if con_delta > 0.05 and con_delta > lib_delta:
        return "slightly_conservative"
    return "mixed"


def aggregate_results(raw: RawResponses, survey: Survey) -> RunResults:
    """Compute per-question, per-model response distributions from raw responses."""
    from llmsurvey.models.results import QuestionResult, RunResults

    results = RunResults()
    for question in survey.questions:
        qid = question.id
        real_dist = dict(question.real_distribution.overall)
        q_result = QuestionResult(real=real_dist)
        results.questions[qid] = q_result

        for model_id in raw.models:
            model_responses = [
                r for r in raw.responses
                if r.question_id == qid and r.model == model_id and r.parsed is not None
            ]
            if not model_responses:
                continue
            counts: dict[str, int] = {opt: 0 for opt in question.options}
            for r in model_responses:
                if r.parsed in counts:
                    counts[r.parsed] += 1
            total = sum(counts.values())
            q_result.models[model_id] = {k: v / total for k, v in counts.items()} if total else {}

    return results


def compute_stats(results: RunResults, raw: RawResponses, survey: Survey) -> RunStats:
    """Compute chi-square, KL, JS divergence and bias metrics."""
    run_stats = RunStats()

    for question in survey.questions:
        qid = question.id
        q_result = results.questions.get(qid)
        if not q_result:
            continue

        options = question.options
        real_vals = [q_result.real.get(opt, 0.0) for opt in options]
        run_stats.questions[qid] = {}

        for model_id in raw.models:
            model_dist = q_result.models.get(model_id)
            if not model_dist:
                continue

            llm_vals = [model_dist.get(opt, 0.0) for opt in options]

            # chi-square: need counts; approximate from number of parsed responses
            model_responses = [
                r for r in raw.responses
                if r.question_id == qid and r.model == model_id
            ]
            n_parsed = sum(1 for r in model_responses if r.parsed is not None)
            n_total = len(model_responses)
            parse_failure_rate = (n_total - n_parsed) / n_total if n_total else 0.0

            chi_p: float | None = None
            if n_parsed >= 5:
                expected = [r * n_parsed for r in real_vals]
                observed = [v * n_parsed for v in llm_vals]
                # Avoid zero expected
                if all(e > 0 for e in expected):
                    chi_stat, chi_p = stats.chisquare(f_obs=observed, f_exp=expected)

            kl = _kl_divergence(real_vals, llm_vals)
            js = _js_divergence(real_vals, llm_vals)

            per_option_delta = {
                opt: llm_vals[i] - real_vals[i]
                for i, opt in enumerate(options)
            }
            bias = _bias_direction(per_option_delta)

            run_stats.questions[qid][model_id] = ModelQuestionStats(
                chi_square_p=chi_p,
                kl_divergence=kl,
                js_divergence=js,
                bias_direction=bias,
                per_option_delta=per_option_delta,
                parse_failure_rate=parse_failure_rate,
            )

    return run_stats
