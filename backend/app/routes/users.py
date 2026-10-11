"""Saved-profile route.

What this file does:
    Lets you check that a confirmed chat was written to SQLite.

What enters:
    GET /users/{user_id}. The id is the number returned when the user says yes.

What happens inside:
    The route asks profile_service for that id. No conversation text is logged.

What it returns:
    The profile and its three life events, or a 404 when the id does not exist.
"""

from fastapi import APIRouter, HTTPException

from app.schemas.user import UserProfileOut
from app.services.profile_service import get_user

router = APIRouter(tags=["users"])


@router.get("/users/{user_id}", response_model=UserProfileOut)
def read_user(user_id: int) -> UserProfileOut:
    profile = get_user(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No saved profile with id {user_id}.")
    return profile
