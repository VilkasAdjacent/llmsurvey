from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RealDistribution(BaseModel):
    overall: dict[str, float]
    by_party: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_age: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_education: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_race: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_gender: dict[str, dict[str, float]] = Field(default_factory=dict)


class Question(BaseModel):
    id: str
    text: str
    type: Literal["single_choice"] = "single_choice"
    options: list[str]
    real_distribution: RealDistribution


class Survey(BaseModel):
    name: str
    source: str
    source_url: str = ""
    questions: list[Question]

    def get_question(self, question_id: str) -> Question:
        for q in self.questions:
            if q.id == question_id:
                return q
        raise KeyError(f"Question {question_id!r} not found in survey")
