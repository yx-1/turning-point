"""Shapes of the JSON that the chat screen sends and receives."""

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=80)
    text: str = Field(max_length=1000)


class RestartRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=80)


class ConversationResponse(BaseModel):
    session_id: str
    state: str
    replies: list[str]
    user_id: int | None = None
