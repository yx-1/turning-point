"""Save and load a confirmed profile.

What this file does:
    Writes one UserProfile and three LifeEvent rows, and reads them back.

What enters:
    The birth fields and three events from a confirmed in-memory session.

What happens inside:
    SQLAlchemy inserts the profile, then the three events that point at it,
    in one transaction. A failed insert rolls back, so a half-saved profile
    is not left behind.

What it returns:
    The new numeric user id, or the saved profile when a route asks for it.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.database import session_scope
from app.models.profile import LifeEvent, UserProfile
from app.schemas.user import LifeEventOut, UserProfileOut
from app.utils.parsing import format_categories


class ProfileSaveError(Exception):
    """The session does not have the fields required for a saved profile."""


def _require_bounded(value: str, limit: int, label: str) -> None:
    """Reject an oversized field without repeating its contents in the error."""

    if len(value) > limit:
        raise ProfileSaveError(f"{label} is too long, so nothing was saved.")


def save_confirmed_profile(
    *,
    birth_date: str | None,
    birth_time: str | None,
    birth_city: str | None,
    current_city: str | None,
    events: list[tuple[list[str], str, str]],
) -> int:
    """Insert one profile and exactly three events. Returns the new user id."""

    if not birth_date or not birth_time or not birth_city or not current_city:
        raise ProfileSaveError("Birth information is incomplete, so nothing was saved.")
    if len(events) != 3:
        raise ProfileSaveError("Exactly three life events are required, so nothing was saved.")
    _require_bounded(birth_date, 80, "Birth date")
    _require_bounded(birth_time, 80, "Birth time")
    _require_bounded(birth_city, 80, "Birth city")
    _require_bounded(current_city, 80, "Current city")
    for _categories, event_date, description in events:
        _require_bounded(event_date, 80, "Event date")
        _require_bounded(description, 1000, "Event description")

    try:
        with session_scope() as db:
            profile = UserProfile(
                birth_date=birth_date,
                birth_time=birth_time,
                birth_city=birth_city,
                current_city=current_city,
            )
            db.add(profile)
            db.flush()
            for categories, event_date, description in events:
                db.add(
                    LifeEvent(
                        user_id=profile.id,
                        event_type=format_categories(categories),
                        event_date=event_date,
                        description=description,
                    )
                )
            return profile.id
    except SQLAlchemyError as error:
        raise ProfileSaveError(
            "The profile could not be saved on this computer. Nothing was sent elsewhere."
        ) from error


def get_user(user_id: int) -> UserProfileOut | None:
    """Return one saved profile and its events, or None when the id is missing."""

    with session_scope() as db:
        profile = db.get(UserProfile, user_id)
        if profile is None:
            return None
        return UserProfileOut(
            id=profile.id,
            birth_date=profile.birth_date,
            birth_time=profile.birth_time,
            birth_city=profile.birth_city,
            current_city=profile.current_city,
            created_at=profile.created_at,
            life_events=[
                LifeEventOut(
                    id=event.id,
                    user_id=event.user_id,
                    event_type=event.event_type,
                    event_date=event.event_date,
                    description=event.description,
                    created_at=event.created_at,
                )
                for event in profile.life_events
            ],
        )


def count_profiles() -> int:
    """Count saved profiles. Used by tests to catch a second insert."""

    with session_scope() as db:
        total = db.scalar(select(func.count()).select_from(UserProfile))
        return int(total or 0)
