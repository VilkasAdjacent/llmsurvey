"""FastAPI server for llmsurvey web UI."""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException


def create_app(surveys_dir: Path, dist_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="llmsurvey")

    @app.get("/api/surveys")
    def list_surveys():
        surveys = []
        if not surveys_dir.exists():
            return surveys
        for survey_path in sorted(surveys_dir.iterdir()):
            yaml_file = survey_path / "survey.yaml"
            if not yaml_file.exists():
                continue
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            surveys.append({
                "id": survey_path.name,
                "name": data.get("name", survey_path.name),
                "source": data.get("source", ""),
                "question_count": len(data.get("questions", [])),
            })
        return surveys

    @app.get("/api/surveys/{survey_id}")
    def get_survey(survey_id: str):
        yaml_file = surveys_dir / survey_id / "survey.yaml"
        if not yaml_file.exists():
            raise HTTPException(status_code=404, detail="Survey not found")
        with open(yaml_file, encoding="utf-8") as f:
            return yaml.safe_load(f)

    @app.get("/api/surveys/{survey_id}/runs")
    def list_runs(survey_id: str):
        runs_dir = surveys_dir / survey_id / "runs"
        if not runs_dir.exists():
            raise HTTPException(status_code=404, detail="Survey not found")
        runs = []
        for run_path in sorted(runs_dir.iterdir(), reverse=True):
            if not run_path.is_dir():
                continue
            responses_file = run_path / "responses.json"
            if not responses_file.exists():
                continue
            with open(responses_file, encoding="utf-8") as f:
                resp = json.load(f)
            runs.append({
                "run_id": run_path.name,
                "models": resp.get("models", []),
                "participant_count": len(resp.get("participants", [])),
                "has_summary": (run_path / "summary.json").exists(),
            })
        return runs

    @app.get("/api/surveys/{survey_id}/runs/{run_id}")
    def get_run(survey_id: str, run_id: str):
        run_dir = surveys_dir / survey_id / "runs" / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail="Run not found")

        def read_json(name: str):
            p = run_dir / name
            if not p.exists():
                return None
            with open(p, encoding="utf-8") as f:
                return json.load(f)

        results = read_json("results.json")
        stats = read_json("stats.json")
        summary_data = read_json("summary.json")
        summary = summary_data.get("summary") if summary_data else None

        return {"results": results, "stats": stats, "summary": summary}

    if dist_dir is not None and dist_dir.exists():
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")

    return app
