"""Conversation routes.

What this file does:
    Accepts chat messages from React and passes them to the state machine.

What enters:
    POST /conversation/start with an empty body.
    POST /conversation/message with a session id and the user's text.
    POST /conversation/restart with the current session id.

What happens inside:
    The route checks that the JSON matches the expected shape, then calls
    conversation_service. The service decides the next question.

What it returns:
    JSON with session_id, state, and replies. The browser appends replies
    to the chat. Personal text is not written to the server log.
"""

from fastapi import APIRouter, HTTPException

from app.schemas.conversation import ConversationResponse, MessageRequest, RestartRequest
from app.services.conversation_service import (
    EmptyMessage,
    SessionNotFound,
    handle_message,
    restart_session,
    start_session,
)
from app.services.profile_service import ProfileSaveError

router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.post("/start", response_model=ConversationResponse)
def start() -> ConversationResponse:
    return start_session()


@router.post("/message", response_model=ConversationResponse)
def message(body: MessageRequest) -> ConversationResponse:
    try:
        return handle_message(body.session_id, body.text)
    except EmptyMessage as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except SessionNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ProfileSaveError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/restart", response_model=ConversationResponse)
def restart(body: RestartRequest) -> ConversationResponse:
    return restart_session(body.session_id)
