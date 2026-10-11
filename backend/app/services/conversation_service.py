"""Conversation state machine.

What this file does:
    Remembers one chat session and decides the next question.

What enters:
    A session id and the user's latest message. The first call creates a session
    with no personal data.

What happens inside:
    The current state says which fact is expected. A local parser checks the
    message. A clear answer is stored and the state moves forward. An unclear
    answer stays in the same state and produces a follow-up question.

What it returns:
    The session id, the new state name, and one or more assistant replies.
    Saying yes also returns user_id after the profile is written to SQLite.
    The active session still lives in memory and disappears when the API
    process restarts. Saved profiles stay in the database file.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import date

from app.schemas.conversation import ConversationResponse
from app.services.profile_service import save_confirmed_profile
from app.utils.parsing import (
    DateProgress,
    DateRead,
    classify_event,
    find_date_mentions,
    format_categories,
    interpret_date,
    meaningful_words,
    parse_city,
    parse_time,
)

WELCOME = (
    "Welcome to Turning Point. This chat is for entertainment and self-reflection. "
    "Your answers stay on this computer for this session."
)
BIRTH_DATE_QUESTION = "Let's start with your birth information. What is your date of birth?"
BIRTH_TIME_QUESTION = "Do you know your approximate birth time?"
BIRTH_CITY_QUESTION = "Which city were you born in?"
CURRENT_CITY_QUESTION = "Which city do you live in now?"
EVENT_DATE_HINT = "When did that happen? A month and year is enough, such as March 2022, summer 2021, or 2019."

COLLECT_BIRTH_DATE = "collect_birth_date"
COLLECT_BIRTH_TIME = "collect_birth_time"
COLLECT_BIRTH_CITY = "collect_birth_city"
COLLECT_CURRENT_CITY = "collect_current_city"
CONFIRM = "confirm_information"
CONFIRMED = "confirmed"


class SessionNotFound(Exception):
    """The browser sent a session id this process does not have."""


class EmptyMessage(Exception):
    """The user tried to send a blank message."""


@dataclass
class LifeEvent:
    description: str
    categories: list[str]
    date_label: str
    date_precision: str


@dataclass
class Session:
    id: str
    state: str = COLLECT_BIRTH_DATE
    birth_date_label: str | None = None
    birth_time_label: str | None = None
    birth_time_24h: str | None = None
    birth_city: str | None = None
    current_city: str | None = None
    events: list[LifeEvent] = field(default_factory=list)
    pending_description: str | None = None
    pending_categories: list[str] = field(default_factory=list)
    date_progress: DateProgress = field(default_factory=DateProgress)
    time_hour: int | None = None
    time_minute: int | None = None
    time_approximate: bool = False
    saved_user_id: int | None = None


_sessions: dict[str, Session] = {}
_lock = threading.Lock()


def start_session() -> ConversationResponse:
    session = Session(id=str(uuid.uuid4()))
    with _lock:
        _sessions[session.id] = session
    return _response(session, [WELCOME, BIRTH_DATE_QUESTION])


def restart_session(session_id: str | None) -> ConversationResponse:
    with _lock:
        if session_id and session_id in _sessions:
            del _sessions[session_id]
    return start_session()


def handle_message(session_id: str, text: str, today: date | None = None) -> ConversationResponse:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        raise EmptyMessage("Type a message before sending.")

    clock = today or date.today()
    with _lock:
        session = _sessions.get(session_id)
        if session is None:
            raise SessionNotFound(
                "This session was cleared because the API restarted. Use Restart to begin again."
            )
        replies = _advance(session, cleaned, clock)
        return _response(session, replies)


def reset_for_tests() -> None:
    with _lock:
        _sessions.clear()


def _advance(session: Session, text: str, today: date) -> list[str]:
    if session.state == COLLECT_BIRTH_DATE:
        return _birth_date(session, text, today)
    if session.state == COLLECT_BIRTH_TIME:
        return _birth_time(session, text)
    if session.state == COLLECT_BIRTH_CITY:
        return _city(session, text, field_name="birth")
    if session.state == COLLECT_CURRENT_CITY:
        return _city(session, text, field_name="current")
    if session.state.startswith("collect_event_") and session.state.endswith("_date"):
        number = int(session.state.removeprefix("collect_event_").removesuffix("_date"))
        return _event_date(session, text, number, today)
    if session.state.startswith("collect_event_"):
        number = int(session.state.removeprefix("collect_event_"))
        return _event(session, text, number, today)
    if session.state == CONFIRM:
        return _confirm(session, text)
    if session.state == CONFIRMED:
        if session.saved_user_id is not None and _is_yes(text):
            return [
                f"This session was already saved as user {session.saved_user_id}. "
                "Use Restart to begin again."
            ]
        return ["Your information is already confirmed. Use Restart to begin again."]
    return ["I lost my place in the conversation. Use Restart to begin again."]


def _birth_date(session: Session, text: str, today: date) -> list[str]:
    reading = interpret_date(
        text,
        session.date_progress,
        require_day=True,
        include_partials=True,
        today=today,
    )
    if reading.status == "complete":
        session.birth_date_label = reading.label
        session.date_progress = DateProgress()
        session.state = COLLECT_BIRTH_TIME
        return [f"Thanks — {reading.label}. {BIRTH_TIME_QUESTION}"]
    return [_date_follow_up(session, reading, "I need a full birth date, such as May 8, 1997.")]


def _birth_time(session: Session, text: str) -> list[str]:
    reading = parse_time(text, session.time_hour, session.time_minute)
    if reading.approximate:
        session.time_approximate = True
    if reading.status == "need_period":
        session.time_hour = reading.pending_hour
        session.time_minute = reading.pending_minute
        return ["Was that in the morning or the evening?"]
    if reading.status == "complete":
        label = reading.label
        if session.time_approximate and not label.startswith("around "):
            label = f"around {label}"
        session.birth_time_label = label
        session.birth_time_24h = reading.hour24
        session.time_hour = None
        session.time_minute = None
        session.state = COLLECT_BIRTH_CITY
        return [f"Thanks — {label}. {BIRTH_CITY_QUESTION}"]
    if reading.status == "unknown":
        session.birth_time_label = "Unknown"
        session.birth_time_24h = None
        session.state = COLLECT_BIRTH_CITY
        return [f"That's okay. I'll continue without a birth time. {BIRTH_CITY_QUESTION}"]
    if reading.status == "invalid":
        return ["I couldn't read that time. Try something like 9:30 PM, or say that you don't know."]
    return ["I need an approximate birth time, such as 9 PM. If you don't know it, say so."]


def _city(session: Session, text: str, field_name: str) -> list[str]:
    city = parse_city(text)
    if city is None:
        if field_name == "birth":
            return ["I need the city name. Which city were you born in?"]
        return ["I need the city name. Which city do you live in now?"]

    if field_name == "birth":
        session.birth_city = city
        session.state = COLLECT_CURRENT_CITY
        return [f"Born in {city}. {CURRENT_CITY_QUESTION}"]

    session.current_city = city
    session.state = "collect_event_1"
    return [
        f"You live in {city} now.",
        "Now tell me about one major event that changed your life.",
    ]


def _event(session: Session, text: str, number: int, today: date) -> list[str]:
    mentions = find_date_mentions(text, include_partials=False)
    words = meaningful_words(text, mentions)
    if not words:
        if len(mentions) == 1 and not mentions[0].ambiguous and not mentions[0].invalid:
            reading = interpret_date(
                text,
                DateProgress(),
                require_day=False,
                include_partials=False,
                today=today,
            )
            if reading.status == "complete":
                session.date_progress = reading.progress or DateProgress()
                return [f"I can use {reading.label}. What happened then?"]
        return ["Please describe one major life event in a sentence."]

    categories = classify_event(text)
    if categories == ["other"] and len(words) < 3:
        return ["Tell me a little more about what happened."]

    if len(mentions) > 1:
        _hold_event(session, text, categories, number)
        return ["I found more than one date. Which date should I use for this event?"]

    if len(mentions) == 1 and (mentions[0].ambiguous or mentions[0].invalid):
        _hold_event(session, text, categories, number)
        return ["I am not sure how to read that date. Please write it as March 2022 or May 8, 2019."]

    reading = interpret_date(
        text,
        session.date_progress,
        require_day=False,
        include_partials=False,
        today=today,
    )
    if reading.status == "complete":
        session.date_progress = DateProgress()
        return _save_event(session, number, text, categories, reading.label, reading.precision)
    if reading.status == "future":
        _hold_event(session, text, categories, number)
        return ["That date is still in the future. When did this past event happen?"]
    if reading.status in {"ambiguous", "invalid", "multiple"}:
        _hold_event(session, text, categories, number)
        return ["I am not sure how to read that date. Please write it as March 2022 or May 8, 2019."]

    _hold_event(session, text, categories, number)
    label = format_categories(categories)
    return [f"Got it: {label}. {EVENT_DATE_HINT}"]


def _event_date(session: Session, text: str, number: int, today: date) -> list[str]:
    reading = interpret_date(
        text,
        session.date_progress,
        require_day=False,
        include_partials=True,
        today=today,
    )
    if reading.status == "complete":
        description = session.pending_description or text
        categories = session.pending_categories or classify_event(description)
        session.date_progress = DateProgress()
        return _save_event(session, number, description, categories, reading.label, reading.precision)

    follow_up = _date_follow_up(
        session,
        reading,
        "I could not find a date. Try March 2022, summer 2021, or 2019.",
    )
    return [follow_up]


def _confirm(session: Session, text: str) -> list[str]:
    if _is_yes(text):
        if session.saved_user_id is None:
            session.saved_user_id = save_confirmed_profile(
                birth_date=session.birth_date_label,
                birth_time=session.birth_time_label,
                birth_city=session.birth_city,
                current_city=session.current_city,
                events=[
                    (event.categories, event.date_label, event.description) for event in session.events
                ],
            )
        session.state = CONFIRMED
        return [
            f"Thanks. I saved this profile on this computer as user {session.saved_user_id}. "
            "Click Analyze when you want the local chart reading."
        ]
    if _is_no(text):
        _clear_profile(session)
        session.state = COLLECT_BIRTH_DATE
        return ["Okay, let's start over. What is your date of birth?"]
    return ["Reply yes if this looks right, or no to start over."]


def _save_event(
    session: Session,
    number: int,
    description: str,
    categories: list[str],
    date_label: str,
    precision: str,
) -> list[str]:
    session.events.append(
        LifeEvent(
            description=description.strip(),
            categories=categories,
            date_label=date_label,
            date_precision=precision,
        )
    )
    session.pending_description = None
    session.pending_categories = []
    session.date_progress = DateProgress()
    ack = f"Got it: {format_categories(categories)} — {date_label}."
    if number < 3:
        session.state = f"collect_event_{number + 1}"
        if number == 1:
            return [f"{ack} Let's add another important event."]
        return [f"{ack} One more. What is a third major life event?"]

    session.state = CONFIRM
    return [ack, _summary(session)]


def _hold_event(session: Session, description: str, categories: list[str], number: int) -> None:
    session.pending_description = description.strip()
    session.pending_categories = categories
    session.date_progress = DateProgress()
    session.state = f"collect_event_{number}_date"


def _clear_profile(session: Session) -> None:
    session.birth_date_label = None
    session.birth_time_label = None
    session.birth_time_24h = None
    session.birth_city = None
    session.current_city = None
    session.events = []
    session.pending_description = None
    session.pending_categories = []
    session.date_progress = DateProgress()
    session.time_hour = None
    session.time_minute = None
    session.time_approximate = False
    session.saved_user_id = None


def _date_follow_up(session: Session, reading: DateRead, fallback: str) -> str:
    if reading.status == "partial" and reading.progress is not None:
        session.date_progress = reading.progress
        return reading.question or fallback
    if reading.status == "ambiguous":
        return "That date could be read two ways. Please write the month name, such as May 8, 1997."
    if reading.status == "multiple":
        return "I found more than one date. Please send just one."
    if reading.status == "invalid":
        return "That doesn't look like a real calendar date. Please try again."
    if reading.status == "future":
        return "That date is in the future. Please use a past date."
    if reading.status == "too_old":
        return "Please use a year from 1900 onward."
    return fallback


def _summary(session: Session) -> str:
    lines = [
        "Here is what I have so far.",
        "",
        f"Birth date: {session.birth_date_label}",
        f"Birth time: {session.birth_time_label}",
        f"Birth city: {session.birth_city}",
        f"Current city: {session.current_city}",
        "",
        "Life events:",
    ]
    for index, event in enumerate(session.events, start=1):
        lines.append(f"{index}. {format_categories(event.categories)} — {event.date_label}")
        lines.append(f"   {event.description}")
    lines.append("")
    lines.append("Does this look right? Reply yes to continue, or no to start over.")
    return "\n".join(lines)


def _is_yes(text: str) -> bool:
    normalized = _normalize(text)
    if normalized in {"yes", "y", "yeah", "yep", "correct", "confirm", "ok", "okay", "sure"}:
        return True
    return normalized.startswith("yes") or "looks right" in normalized or "looks good" in normalized


def _is_no(text: str) -> bool:
    normalized = _normalize(text)
    if normalized in {"no", "n", "nope", "restart", "incorrect", "wrong"}:
        return True
    return normalized.startswith("no") or "start over" in normalized


def _normalize(text: str) -> str:
    return " ".join(text.lower().replace("'", "").split())


def _response(session: Session, replies: list[str]) -> ConversationResponse:
    return ConversationResponse(
        session_id=session.id,
        state=session.state,
        replies=replies,
        user_id=session.saved_user_id,
    )
