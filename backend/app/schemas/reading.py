"""JSON for the final reading shown after analysis."""

from pydantic import BaseModel, Field


class ReadingOut(BaseModel):
    user_id: int
    natal_summary: str
    time_note: str
    past_pattern: str
    future_window: str
    themes: list[str] = Field(min_length=2, max_length=3)
    why: str
    similarities: str
    preparation: str
    disclaimer: str
