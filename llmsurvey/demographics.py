"""Census API client and stratified participant sampler."""
from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import requests
import yaml

from llmsurvey.models.participant import SyntheticParticipant


class CensusClient:
    BASE_URL = "https://api.census.gov/data"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    def query(self, dataset: str, year: int, geography: str, variables: list[str]) -> list[dict]:
        url = f"{self.BASE_URL}/{year}/{dataset}"
        params: dict[str, Any] = {
            "get": ",".join(variables),
            "for": geography,
        }
        if self.api_key:
            params["key"] = self.api_key
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        rows = resp.json()
        headers = rows[0]
        return [dict(zip(headers, row)) for row in rows[1:]]


def _weighted_choice(rng: random.Random, choices: dict[str, float]) -> str:
    keys = list(choices.keys())
    weights = [choices[k] for k in keys]
    return rng.choices(keys, weights=weights, k=1)[0]


_AGE_RANGES: dict[str, tuple[int, int]] = {
    "age_18_29": (18, 29),
    "age_30_44": (30, 44),
    "age_45_64": (45, 64),
    "age_65_plus": (65, 85),
}

_INCOME_LABELS: dict[str, str] = {
    "income_under_50k": "Under $50,000",
    "income_50_100k": "$50,000–$100,000",
    "income_over_100k": "Over $100,000",
}

_PARTY_LABELS: dict[str, str] = {
    "party_democrat": "Democrat",
    "party_republican": "Republican",
    "party_independent": "Independent",
}

_RACE_LABELS: dict[str, str] = {
    "white": "White",
    "black": "Black or African American",
    "hispanic": "Hispanic or Latino",
    "other": "Other",
}

_EDUCATION_LABELS: dict[str, str] = {
    "college_grad": "College graduate",
    "no_college": "No college degree",
}

_US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
]


def _extract_group(dist: dict[str, float], prefix_map: dict[str, str]) -> dict[str, float]:
    result = {}
    for key, label in prefix_map.items():
        if key in dist:
            result[label] = dist[key]
    # Normalise in case weights don't sum to 1
    total = sum(result.values())
    if total > 0:
        return {k: v / total for k, v in result.items()}
    return result


def sample_participants(
    demographic_yaml_path: Path,
    n: int,
    seed: int = 42,
) -> list[SyntheticParticipant]:
    """Stratified random sampling from a demographic YAML distribution."""
    with open(demographic_yaml_path) as f:
        demo = yaml.safe_load(f)

    dist: dict[str, float] = demo.get("manual_distribution", {})
    rng = random.Random(seed)

    age_dist = _extract_group(dist, {k: k for k in _AGE_RANGES})
    gender_dist = _extract_group(dist, {"male": "Male", "female": "Female"})
    race_dist = _extract_group(dist, _RACE_LABELS)
    education_dist = _extract_group(dist, _EDUCATION_LABELS)
    income_dist = _extract_group(dist, _INCOME_LABELS)
    party_dist = _extract_group(dist, _PARTY_LABELS)

    participants = []
    for i in range(n):
        pid = f"p{i+1:04d}"

        age_bucket = _weighted_choice(rng, age_dist)
        lo, hi = _AGE_RANGES[age_bucket]
        age = rng.randint(lo, hi)

        gender = _weighted_choice(rng, gender_dist)
        race = _weighted_choice(rng, race_dist)
        education = _weighted_choice(rng, education_dist)
        income = _weighted_choice(rng, income_dist)
        party = _weighted_choice(rng, party_dist)
        state = rng.choice(_US_STATES)

        participants.append(
            SyntheticParticipant(
                id=pid,
                age=age,
                gender=gender,
                race=race,
                education=education,
                state=state,
                income_bracket=income,
                political_party=party,
            )
        )

    return participants
