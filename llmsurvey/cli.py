"""Click CLI entrypoint for llmsurvey."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("llmsurvey")


def _load_survey(survey_dir: Path):
    from llmsurvey.models.survey import Survey
    survey_yaml = survey_dir / "survey.yaml"
    with open(survey_yaml) as f:
        data = yaml.safe_load(f)
    return Survey.model_validate(data)


def _make_run_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


@click.group()
def cli():
    """llmsurvey — LLM vs Real Survey Comparison Tool."""


@cli.command()
@click.argument("survey_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--models", default="meta/llama-4-scout", show_default=True,
              help="Comma-separated Replicate model IDs")
@click.option("--n", default=50, show_default=True, help="Number of synthetic participants")
@click.option("--seed", default=42, show_default=True, help="RNG seed")
@click.option("--no-cache", is_flag=True, default=False, help="Disable response caching")
@click.option("--no-report", is_flag=True, default=False, help="Skip LLM summary generation")
@click.option("--template", default=None, type=click.Path(path_type=Path),
              help="Path to custom Jinja2 prompt template (default: templates/survey_prompt.j2)")
def run(survey_dir: Path, models: str, n: int, seed: int, no_cache: bool, no_report: bool, template: Path | None):
    """Run a survey simulation."""
    from llmsurvey.compare import aggregate_results, compute_stats
    from llmsurvey.demographics import sample_participants
    from llmsurvey.llm import run_survey
    from llmsurvey.viz import generate_all_charts

    survey = _load_survey(survey_dir)
    model_ids = [m.strip() for m in models.split(",")]

    if template is None:
        template = Path("templates/survey_prompt.j2")
    if not template.exists():
        click.echo(f"Template not found: {template}", err=True)
        sys.exit(1)

    demographic_yaml = survey_dir / "demographic.yaml"
    if not demographic_yaml.exists():
        click.echo(f"demographic.yaml not found in {survey_dir}", err=True)
        sys.exit(1)

    run_id = _make_run_id()
    run_dir = survey_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    charts_dir = run_dir / "charts"

    click.echo(f"Run ID: {run_id}")
    click.echo(f"Survey: {survey.name}")
    click.echo(f"Models: {', '.join(model_ids)}")
    click.echo(f"Participants: {n}  Seed: {seed}")

    click.echo("Sampling participants...")
    participants = sample_participants(demographic_yaml, n, seed)
    click.echo(f"  {len(participants)} participants sampled")

    click.echo("Running LLM survey...")
    raw = run_survey(survey, participants, model_ids, template, run_id, use_cache=not no_cache)

    responses_path = run_dir / "responses.json"
    responses_path.write_text(raw.model_dump_json(indent=2), encoding="utf-8")
    click.echo(f"  Saved responses → {responses_path}")

    click.echo("Aggregating results...")
    results = aggregate_results(raw, survey)
    results_path = run_dir / "results.json"
    results_path.write_text(results.model_dump_json(indent=2), encoding="utf-8")
    click.echo(f"  Saved results → {results_path}")

    click.echo("Computing statistics...")
    run_stats = compute_stats(results, raw, survey)
    stats_path = run_dir / "stats.json"
    stats_path.write_text(run_stats.model_dump_json(indent=2), encoding="utf-8")
    click.echo(f"  Saved stats → {stats_path}")

    click.echo("Generating charts...")
    chart_paths = generate_all_charts(survey, results, run_stats, charts_dir)
    click.echo(f"  {len(chart_paths)} chart(s) saved to {charts_dir}")

    if not no_report:
        click.echo("Generating narrative summary...")
        from llmsurvey.report import generate_summary
        summary_text = generate_summary(results, run_stats)
        summary_path = run_dir / "summary.json"
        summary_path.write_text(json.dumps({"summary": summary_text}, indent=2), encoding="utf-8")
        click.echo(f"  Saved summary → {summary_path}")

    click.echo(f"\nDone. Run directory: {run_dir}")


@cli.command()
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def stats(run_dir: Path):
    """Recompute stats from an existing responses.json."""
    from llmsurvey.compare import aggregate_results, compute_stats
    from llmsurvey.models.results import RawResponses

    # Find the survey directory (two levels up from run_dir)
    survey_dir = run_dir.parent.parent
    survey = _load_survey(survey_dir)

    responses_path = run_dir / "responses.json"
    raw = RawResponses.model_validate_json(responses_path.read_text())

    results = aggregate_results(raw, survey)
    run_stats = compute_stats(results, raw, survey)

    (run_dir / "results.json").write_text(results.model_dump_json(indent=2), encoding="utf-8")
    (run_dir / "stats.json").write_text(run_stats.model_dump_json(indent=2), encoding="utf-8")
    click.echo("Stats recomputed and saved.")


@cli.command()
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--no-summary", is_flag=True, default=False)
def report(run_dir: Path, no_summary: bool):
    """Regenerate summary and charts from an existing run."""
    from llmsurvey.models.results import RawResponses, RunResults, RunStats
    from llmsurvey.viz import generate_all_charts

    survey_dir = run_dir.parent.parent
    survey = _load_survey(survey_dir)

    raw = RawResponses.model_validate_json((run_dir / "responses.json").read_text())
    results = RunResults.model_validate_json((run_dir / "results.json").read_text())
    run_stats = RunStats.model_validate_json((run_dir / "stats.json").read_text())

    charts_dir = run_dir / "charts"
    chart_paths = generate_all_charts(survey, results, run_stats, charts_dir)
    click.echo(f"{len(chart_paths)} chart(s) regenerated.")

    if not no_summary:
        from llmsurvey.report import generate_summary
        summary_text = generate_summary(results, run_stats)
        summary_path = run_dir / "summary.json"
        summary_path.write_text(json.dumps({"summary": summary_text}, indent=2), encoding="utf-8")
        click.echo(f"Summary saved → {summary_path}")


@cli.command()
@click.argument("name")
def new(name: str):
    """Scaffold a new survey directory with template YAML files."""
    survey_dir = Path("surveys") / name
    if survey_dir.exists():
        click.echo(f"Survey directory already exists: {survey_dir}", err=True)
        sys.exit(1)

    survey_dir.mkdir(parents=True)
    (survey_dir / "runs").mkdir()

    survey_yaml = survey_dir / "survey.yaml"
    survey_yaml.write_text(
        f"""\
name: "{name}"
source: "Source Name, Year"
source_url: ""
questions:
  - id: q1
    text: "Your question text here?"
    type: single_choice
    options:
      - "Option A"
      - "Option B"
      - "Option C"
    real_distribution:
      overall:
        "Option A": 0.40
        "Option B": 0.45
        "Option C": 0.15
""",
        encoding="utf-8",
    )

    demo_yaml = survey_dir / "demographic.yaml"
    demo_yaml.write_text(
        """\
label: "US Adult Population (Census 2023 ACS)"
manual_distribution:
  age_18_29: 0.21
  age_30_44: 0.25
  age_45_64: 0.30
  age_65_plus: 0.24
  male: 0.49
  female: 0.51
  white: 0.60
  black: 0.13
  hispanic: 0.19
  other: 0.08
  college_grad: 0.38
  no_college: 0.62
  party_democrat: 0.31
  party_republican: 0.27
  party_independent: 0.38
  income_under_50k: 0.33
  income_50_100k: 0.33
  income_over_100k: 0.34
""",
        encoding="utf-8",
    )

    click.echo(f"Created survey scaffold at {survey_dir}")
    click.echo(f"  Edit {survey_yaml.name} and {demo_yaml.name} then run:")
    click.echo(f"  llmsurvey run {survey_dir} --models meta/llama-4-scout --n 50")
