from __future__ import annotations

from pydantic import BaseModel


class SyntheticParticipant(BaseModel):
    id: str
    age: int
    gender: str
    race: str
    education: str
    state: str
    income_bracket: str
    political_party: str
