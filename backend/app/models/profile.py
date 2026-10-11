"""SQLite tables for a saved profile and its three life events.

What this file does:
    Describes the two tables SQLAlchemy creates.

What enters:
    Field values from a confirmed conversation. The chat does not write here
    directly. profile_service.py creates the rows.

What happens inside:
    Each UserProfile row is one confirmed person. Each LifeEvent row points
    back to that profile with user_id.

What it returns:
    Nothing by itself. Reading a profile returns these objects to the route.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    birth_date: Mapped[str] = mapped_column(String(80))
    birth_time: Mapped[str] = mapped_column(String(80))
    birth_city: Mapped[str] = mapped_column(String(80))
    current_city: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    life_events: Mapped[list[LifeEvent]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="LifeEvent.id",
    )


class LifeEvent(Base):
    __tablename__ = "life_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    event_type: Mapped[str] = mapped_column(String(120))
    event_date: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    profile: Mapped[UserProfile] = relationship(back_populates="life_events")
