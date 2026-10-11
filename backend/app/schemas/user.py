"""JSON returned by GET /users/{user_id}."""

from datetime import datetime

from pydantic import BaseModel


class LifeEventOut(BaseModel):
    id: int
    user_id: int
    event_type: str
    event_date: str
    description: str
    created_at: datetime


class UserProfileOut(BaseModel):
    id: int
    birth_date: str
    birth_time: str
    birth_city: str
    current_city: str
    created_at: datetime
    life_events: list[LifeEventOut]
