"""Replicate API wrapper with prompt rendering and response caching."""
from __future__ import annotations

import hashlib
import json
import logging
import time
from difflib import get_close_matches
from pathlib import Path

import replicate
from jinja2 import Environment, FileSystemLoader, select_autoescape

from llmsurvey.models.participant import SyntheticParticipant
from llmsurvey.models.results import RawResponse, RawResponses
from llmsurvey.models.survey import Question, Survey

logger = logging.getLogger(__name__)

CACHE_DIR = Path(".cache")


def _cache_key(model_id: str, prompt: str) -> str:
    return hashlib.sha256(f"{model_id}\n{prompt}".encode()).hexdigest()


def _read_cache(key: str) -> str | None:
    path = CACHE_DIR / f"{key}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def _write_cache(key: str, text: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.txt").write_text(text, encoding="utf-8")


class ReplicateClient:
    def __init__(self, model_id: str, temperature: float = 0.7, max_tokens: int = 32) -> None:
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens

    def complete(self, prompt: str, use_cache: bool = True) -> str:
        key = _cache_key(self.model_id, prompt)
        if use_cache:
            cached = _read_cache(key)
            if cached is not None:
                logger.debug("Cache hit for model=%s key=%s", self.model_id, key[:8])
                return cached

        output = self._call_with_backoff(prompt)
        if use_cache:
            _write_cache(key, output)
        return output

    def _call_with_backoff(self, prompt: str, max_retries: int = 4) -> str:
        delay = 2.0
        for attempt in range(max_retries):
            try:
                result = replicate.run(
                    self.model_id,
                    input={
                        "prompt": prompt,
                        "temperature": self.temperature,
                        "max_new_tokens": self.max_tokens,
                    },
                )
                # Replicate returns an iterator of string chunks
                return "".join(result).strip()
            except Exception as exc:
                if attempt == max_retries - 1:
                    raise
                logger.warning("Replicate error (attempt %d): %s — retrying in %.1fs", attempt + 1, exc, delay)
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable")


def render_prompt(template_path: Path, participant: SyntheticParticipant, question: Question) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape([]),
    )
    tmpl = env.get_template(template_path.name)
    return tmpl.render(p=participant, question=question)


def parse_response(raw_text: str, question: Question) -> str | None:
    """Fuzzy-match raw LLM output to a valid option. Returns None on failure."""
    stripped = raw_text.strip().strip('"').strip("'")
    # Exact match first
    for opt in question.options:
        if stripped.lower() == opt.lower():
            return opt
    # Fuzzy match
    matches = get_close_matches(stripped, question.options, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    # Substring match (e.g. model returns "Dissatisfied." or "Dissatisfied\n")
    for opt in question.options:
        if opt.lower() in stripped.lower():
            return opt
    return None


def run_survey(
    survey: Survey,
    participants: list[SyntheticParticipant],
    model_ids: list[str],
    template_path: Path,
    run_id: str,
    use_cache: bool = True,
) -> RawResponses:
    responses: list[RawResponse] = []
    parse_failures = 0
    total = 0

    for model_id in model_ids:
        client = ReplicateClient(model_id)
        for question in survey.questions:
            for participant in participants:
                prompt = render_prompt(template_path, participant, question)
                raw = client.complete(prompt, use_cache=use_cache)
                parsed = parse_response(raw, question)
                total += 1
                if parsed is None:
                    parse_failures += 1
                    logger.warning(
                        "Parse failure: model=%s q=%s p=%s raw=%r",
                        model_id, question.id, participant.id, raw,
                    )
                responses.append(
                    RawResponse(
                        participant_id=participant.id,
                        model=model_id,
                        question_id=question.id,
                        raw=raw,
                        parsed=parsed,
                    )
                )

    if total:
        failure_pct = parse_failures / total * 100
        if failure_pct > 5:
            logger.warning("High parse failure rate: %.1f%%", failure_pct)

    return RawResponses(
        run_id=run_id,
        models=model_ids,
        participants=[p.model_dump() for p in participants],
        responses=responses,
    )
