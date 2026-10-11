"""Reading route.

What this file does:
    Turns one saved profile into the final template reading.

What enters:
    POST /users/{user_id}/reading. The id is the number returned at confirmation.

What happens inside:
    reading_service loads the SQLite rows, calculates the chart locally, and
    fills the reading template. The request body is empty.

What it returns:
    The reading sections as JSON, or a 404/400 error the page can show.
"""

from fastapi import APIRouter, HTTPException

from app.schemas.reading import ReadingOut
from app.services.reading_service import ChartInputError, ProfileNotFound, build_reading

router = APIRouter(tags=["readings"])


@router.post("/users/{user_id}/reading", response_model=ReadingOut)
def create_reading(user_id: int) -> ReadingOut:
    try:
        return build_reading(user_id)
    except ProfileNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ChartInputError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="The chart could not be calculated from the saved profile.",
        ) from error
