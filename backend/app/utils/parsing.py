"""Local parsers for dates, times, cities, and life-event categories.

These functions use fixed rules. They do not call an external service.
If a value is incomplete or could mean two different dates, the caller
asks a follow-up instead of choosing one.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date

MONTHS: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

# Longer names come first so "sept" does not steal the start of "september".
_MONTH = (
    r"january|february|march|april|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec|may"
)
_SEASON = r"spring|summer|autumn|fall|winter"
_YEAR = r"19\d{2}|20\d{2}"
_DAY = r"\d{1,2}(?:st|nd|rd|th)?"

# "may" is also a verb, so a bare "may" is only a month when the whole answer is "May".
_MONTH_ONLY = (
    r"january|february|march|april|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec"
)

_CATEGORY_PHRASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "loss",
        ("passed away", "passed on", "died", "death", "funeral", "widow", "widower"),
    ),
    (
        "career",
        (
            "job",
            "jobs",
            "career",
            "careers",
            "hired",
            "fired",
            "laid off",
            "layoff",
            "promotion",
            "promoted",
            "resigned",
            "resign",
            "retired",
            "retirement",
            "employer",
            "quit",
        ),
    ),
    (
        "relocation",
        (
            "moved",
            "moving",
            "relocated",
            "relocation",
            "immigrated",
            "immigration",
            "emigrated",
        ),
    ),
    (
        "education",
        (
            "school",
            "schools",
            "college",
            "university",
            "graduated",
            "graduation",
            "degree",
            "student",
            "studied",
            "campus",
            "phd",
            "semester",
        ),
    ),
    (
        "relationship",
        (
            "married",
            "marriage",
            "divorce",
            "divorced",
            "boyfriend",
            "girlfriend",
            "partner",
            "broke up",
            "breakup",
            "engaged",
            "engagement",
            "wedding",
            "spouse",
            "husband",
            "wife",
            "relationship",
        ),
    ),
    (
        "family",
        (
            "family",
            "mother",
            "father",
            "mom",
            "dad",
            "parent",
            "parents",
            "baby",
            "son",
            "daughter",
            "brother",
            "sister",
            "grandfather",
            "grandmother",
            "grandpa",
            "grandma",
            "uncle",
            "aunt",
        ),
    ),
    (
        "financial",
        (
            "financial",
            "mortgage",
            "debt",
            "bankrupt",
            "bankruptcy",
            "inheritance",
            "inherited",
            "salary",
            "bought a house",
            "bought a home",
        ),
    ),
    (
        "health",
        (
            "hospital",
            "surgery",
            "diagnosed",
            "diagnosis",
            "illness",
            "injury",
            "injured",
            "cancer",
            "pregnant",
            "pregnancy",
            "therapy",
            "health",
        ),
    ),
    ("personal", ("came out", "sobriety", "got sober")),
)

CATEGORY_LABELS = {
    "career": "Career",
    "relocation": "Relocation",
    "relationship": "Relationship",
    "family": "Family",
    "loss": "Loss",
    "education": "Education",
    "financial": "Financial",
    "health": "Health",
    "personal": "Personal",
    "other": "Other",
}

_CITY_REJECT = {
    "yes",
    "no",
    "y",
    "n",
    "ok",
    "okay",
    "hi",
    "hello",
    "idk",
    "unknown",
    "n/a",
    "none",
    "sure",
}


@dataclass(frozen=True)
class DateMention:
    start: int
    end: int
    year: int | None
    month: int | None
    day: int | None
    season: str | None
    ambiguous: bool
    invalid: bool
    specificity: int


@dataclass
class DateProgress:
    year: int | None = None
    month: int | None = None
    day: int | None = None
    season: str | None = None


@dataclass(frozen=True)
class DateRead:
    """Result of reading one user message as a date."""

    status: str
    label: str = ""
    precision: str = ""
    progress: DateProgress | None = None
    question: str = ""


@dataclass(frozen=True)
class TimeRead:
    status: str
    label: str = ""
    hour24: str = ""
    pending_hour: int | None = None
    pending_minute: int | None = None
    approximate: bool = False


def classify_event(text: str) -> list[str]:
    """Return one or more category keys. Unclear text becomes ['other']."""

    lowered = text.lower()
    found: list[str] = []
    for name, phrases in _CATEGORY_PHRASES:
        if any(_contains_phrase(lowered, phrase) for phrase in phrases):
            found.append(name)

    if _contains_phrase(lowered, "lost my job") or _contains_phrase(lowered, "lost my career"):
        found = [name for name in found if name != "loss"]

    return found or ["other"]


def format_categories(categories: list[str]) -> str:
    return " / ".join(CATEGORY_LABELS.get(name, name.title()) for name in categories)


def parse_city(text: str) -> str | None:
    """Return a city name, or None when the answer is not a place."""

    cleaned = " ".join(text.strip().split())
    if not cleaned or len(cleaned) > 80:
        return None

    match = re.search(
        r"(?:born|live|living)\s+in\s+([A-Za-z][A-Za-z .,'-]{1,60})$",
        cleaned,
        re.IGNORECASE,
    )
    if not match:
        match = re.match(r"in\s+([A-Za-z][A-Za-z .,'-]{1,60})$", cleaned, re.IGNORECASE)

    candidate = match.group(1).strip(" .") if match else cleaned
    if any(character.isdigit() for character in candidate):
        return None
    if candidate.lower().strip(".") in _CITY_REJECT:
        return None
    if not re.search(r"[A-Za-z]", candidate):
        return None
    if match is None and len(candidate.split()) > 5:
        return None
    return candidate


def parse_time(
    text: str,
    pending_hour: int | None = None,
    pending_minute: int | None = None,
) -> TimeRead:
    """Read a birth time. Status is complete, unknown, need_period, invalid, or missing."""

    cleaned = " ".join(text.strip().lower().replace(".", "").split())
    approximate = bool(re.search(r"\b(around|about|approximately|approx|roughly)\b", cleaned))

    has_clock = re.search(r"\d", cleaned) is not None
    if re.search(r"\b(dont know|don't know|do not know|unknown|not sure|no idea|cant remember|can't remember)\b", text.lower()) and not has_clock:
        return TimeRead(status="unknown", label="Unknown")

    if re.search(r"\bmidnight\b", cleaned):
        return _complete_time(0, 0, approximate)
    if re.search(r"\bnoon\b", cleaned):
        return _complete_time(12, 0, approximate)

    clock = re.search(rf"\b([01]?\d|2[0-3]):([0-5]\d)\b", cleaned)
    period = _period_from_text(cleaned)
    hour_match = re.search(rf"\b(\d{{1,2}})(?::([0-5]\d))?\s*(am|pm)\b", cleaned)
    if hour_match:
        hour = int(hour_match.group(1))
        minute = int(hour_match.group(2) or 0)
        if hour < 1 or hour > 12:
            return TimeRead(status="invalid")
        hour24 = _to_24_hour(hour, hour_match.group(3))
        return _complete_time(hour24, minute, approximate)

    loose_hour = re.search(rf"\b(\d{{1,2}})(?::([0-5]\d))?\b", cleaned)
    if loose_hour and period:
        hour = int(loose_hour.group(1))
        minute = int(loose_hour.group(2) or 0)
        if hour < 1 or hour > 12:
            return TimeRead(status="invalid")
        return _complete_time(_to_24_hour(hour, period), minute, approximate)

    if clock and period is None and not re.search(r"\b(am|pm)\b", cleaned):
        hour24 = int(clock.group(1))
        minute = int(clock.group(2))
        # "9:30" is not a 24-hour time. Only hours above 12, or 00, are unambiguous.
        if hour24 == 0 or hour24 > 12:
            return _complete_time(hour24, minute, approximate)

    if loose_hour and not period:
        hour = int(loose_hour.group(1))
        minute = int(loose_hour.group(2) or 0)
        if 1 <= hour <= 12:
            return TimeRead(
                status="need_period",
                pending_hour=hour,
                pending_minute=minute,
                approximate=approximate,
            )
        return TimeRead(status="invalid")

    if period and pending_hour is not None:
        minute = pending_minute or 0
        return _complete_time(_to_24_hour(pending_hour, period), minute, approximate)

    return TimeRead(status="missing")


def find_date_mentions(text: str, *, include_partials: bool) -> list[DateMention]:
    """Find date phrases. Partials such as "March" are optional."""

    candidates: list[DateMention] = []
    patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(rf"\b({_YEAR})-(\d{{2}})-(\d{{2}})\b"), "iso"),
        (re.compile(rf"\b({_MONTH})\.?\s+({_DAY})(?:,)?\s+({_YEAR})\b", re.I), "month_day_year"),
        (re.compile(rf"\b({_DAY})\s+(?:of\s+)?({_MONTH})\.?,?\s+({_YEAR})\b", re.I), "day_month_year"),
        (re.compile(rf"\b({_MONTH})\.?\s+(?:of\s+)?({_YEAR})\b", re.I), "month_year"),
        (re.compile(rf"\b({_SEASON})\s+(?:of\s+)?({_YEAR})\b", re.I), "season_year"),
        (re.compile(rf"\b(\d{{1,2}})[/-](\d{{1,2}})[/-]({_YEAR})\b"), "numeric"),
        (re.compile(rf"\b({_MONTH})\.?\s+({_DAY})\b", re.I), "month_day"),
        (re.compile(rf"\b({_DAY})\s+(?:of\s+)?({_MONTH})\b", re.I), "day_month"),
        (re.compile(rf"\b({_MONTH_ONLY})\b", re.I), "month"),
        (re.compile(rf"\b({_SEASON})\b", re.I), "season"),
        (re.compile(rf"\b({_YEAR})\b"), "year"),
    ]

    for pattern, kind in patterns:
        for match in pattern.finditer(text):
            mention = _mention_from_match(match, kind)
            if mention is not None:
                candidates.append(mention)

    stripped = text.strip().lower().rstrip(".")
    if stripped in MONTHS and not candidates:
        month = MONTHS[stripped]
        candidates.append(
            DateMention(0, len(text), None, month, None, None, False, False, 2)
        )

    chosen = _select_nonoverlapping(candidates)
    if include_partials:
        return chosen
    return [mention for mention in chosen if mention.year is not None]


def interpret_date(
    text: str,
    progress: DateProgress,
    *,
    require_day: bool,
    include_partials: bool,
    today: date,
) -> DateRead:
    """Merge this message with any date parts already collected."""

    mentions = find_date_mentions(text, include_partials=include_partials)
    bare_day = _only_day(text) if include_partials and not mentions else None

    if len(mentions) > 1:
        return DateRead(status="multiple")

    if len(mentions) == 1 and mentions[0].ambiguous:
        return DateRead(status="ambiguous")
    if len(mentions) == 1 and mentions[0].invalid:
        return DateRead(status="invalid")

    merged = DateProgress(
        year=progress.year,
        month=progress.month,
        day=progress.day,
        season=progress.season,
    )
    if len(mentions) == 1:
        mention = mentions[0]
        # A month and year in this message replace any earlier partial date.
        # A year alone fills the missing year and keeps a month or day already given.
        if mention.year and (mention.month or mention.season or mention.day):
            merged = DateProgress(
                year=mention.year,
                month=mention.month,
                day=mention.day,
                season=mention.season,
            )
        else:
            if mention.year:
                merged.year = mention.year
            if mention.month:
                merged.month = mention.month
            if mention.day:
                merged.day = mention.day
            if mention.season:
                merged.season = mention.season
    elif bare_day is not None:
        merged.day = bare_day

    if merged.season and merged.month:
        return DateRead(status="ambiguous")
    if not any((merged.year, merged.month, merged.day, merged.season)):
        return DateRead(status="missing")

    if merged.year and merged.month and merged.day:
        if not _valid_day(merged.year, merged.month, merged.day):
            return DateRead(status="invalid")
        if merged.year < 1900:
            return DateRead(status="too_old")
        if date(merged.year, merged.month, merged.day) > today:
            return DateRead(status="future")
        return DateRead(
            status="complete",
            label=f"{MONTH_NAMES[merged.month - 1]} {merged.day}, {merged.year}",
            precision="day",
            progress=merged,
        )

    if not require_day and merged.year:
        if merged.year < 1900:
            return DateRead(status="too_old")
        if merged.season:
            if merged.year > today.year:
                return DateRead(status="future")
            return DateRead(
                status="complete",
                label=f"{merged.season.capitalize()} {merged.year}",
                precision="season",
                progress=merged,
            )
        if merged.month:
            if (merged.year, merged.month) > (today.year, today.month):
                return DateRead(status="future")
            return DateRead(
                status="complete",
                label=f"{MONTH_NAMES[merged.month - 1]} {merged.year}",
                precision="month",
                progress=merged,
            )
        if merged.year > today.year:
            return DateRead(status="future")
        return DateRead(
            status="complete",
            label=str(merged.year),
            precision="year",
            progress=merged,
        )

    return DateRead(status="partial", progress=merged, question=_partial_question(merged, require_day))


def meaningful_words(text: str, mentions: list[DateMention]) -> list[str]:
    """Words left after date phrases are removed. Used to spot a date-only answer."""

    characters = list(text)
    for mention in mentions:
        for index in range(mention.start, min(mention.end, len(characters))):
            characters[index] = " "
    fillers = {"in", "on", "around", "about", "the", "a", "an", "of", "during", "my", "to", "for"}
    words = []
    for word in "".join(characters).lower().split():
        token = re.sub(r"[^a-z']", "", word)
        if token and token not in fillers:
            words.append(token)
    return words


def _partial_question(progress: DateProgress, require_day: bool) -> str:
    month_name = MONTH_NAMES[progress.month - 1] if progress.month else None
    if require_day:
        if progress.year and progress.month:
            return f"What day in {month_name} {progress.year} were you born?"
        if progress.month and progress.day:
            return f"What year were you born? I have {month_name} {progress.day} so far."
        if progress.year:
            return f"What month and day in {progress.year} were you born?"
        if progress.month:
            return f"What day and year in {month_name} were you born?"
        if progress.day:
            return "I have the day. What month and year were you born?"
        return "I need the month, day, and year. For example, May 8, 1997."

    if progress.season and not progress.year:
        return f"Which year was that {progress.season}?"
    if progress.month and not progress.year:
        return f"Which year in {month_name}? For example, {month_name} 2022."
    if progress.day and not progress.year:
        return "Which month and year should I use?"
    return "I still need a date, such as March 2022, summer 2021, or 2019."


def _mention_from_match(match: re.Match[str], kind: str) -> DateMention | None:
    groups = match.groups()
    year: int | None = None
    month: int | None = None
    day: int | None = None
    season: str | None = None
    ambiguous = False
    invalid = False
    specificity = 1

    if kind == "iso":
        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
        specificity = 4
        invalid = not _valid_day(year, month, day)
    elif kind == "month_day_year":
        month = MONTHS[groups[0].lower()]
        day = _day_number(groups[1])
        year = int(groups[2])
        specificity = 4
        invalid = day is None or not _valid_day(year, month, day)
    elif kind == "day_month_year":
        day = _day_number(groups[0])
        month = MONTHS[groups[1].lower()]
        year = int(groups[2])
        specificity = 4
        invalid = day is None or not _valid_day(year, month, day)
    elif kind == "month_year":
        month = MONTHS[groups[0].lower()]
        year = int(groups[1])
        specificity = 3
    elif kind == "season_year":
        season = _normalize_season(groups[0])
        year = int(groups[1])
        specificity = 3
    elif kind == "numeric":
        first, second, year = int(groups[0]), int(groups[1]), int(groups[2])
        specificity = 4
        if first > 12 and second <= 12:
            day, month = first, second
        elif second > 12 and first <= 12:
            month, day = first, second
        elif first <= 12 and second <= 12:
            ambiguous = True
            month, day = first, second
        else:
            invalid = True
            month, day = first, second
        if not ambiguous and not invalid:
            invalid = not _valid_day(year, month, day)
    elif kind == "month_day":
        month = MONTHS[groups[0].lower()]
        day = _day_number(groups[1])
        specificity = 2
        invalid = day is None or day > calendar.monthrange(2024, month)[1]
    elif kind == "day_month":
        day = _day_number(groups[0])
        month = MONTHS[groups[1].lower()]
        specificity = 2
        invalid = day is None or day > calendar.monthrange(2024, month)[1]
    elif kind == "month":
        month = MONTHS[groups[0].lower()]
        specificity = 2
    elif kind == "season":
        season = _normalize_season(groups[0])
        specificity = 2
    elif kind == "year":
        year = int(groups[0])
        specificity = 1
    else:
        return None

    return DateMention(
        start=match.start(),
        end=match.end(),
        year=year,
        month=month,
        day=day,
        season=season,
        ambiguous=ambiguous,
        invalid=invalid,
        specificity=specificity,
    )


def _select_nonoverlapping(candidates: list[DateMention]) -> list[DateMention]:
    ordered = sorted(candidates, key=lambda item: (item.start, -(item.end - item.start), -item.specificity))
    chosen: list[DateMention] = []
    for mention in ordered:
        overlaps = any(mention.start < kept.end and kept.start < mention.end for kept in chosen)
        if not overlaps:
            chosen.append(mention)
    chosen.sort(key=lambda item: item.start)
    return chosen


def _only_day(text: str) -> int | None:
    match = re.fullmatch(r"(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?", text.strip(), re.IGNORECASE)
    if not match:
        return None
    day = int(match.group(1))
    if 1 <= day <= 31:
        return day
    return None


def _day_number(value: str) -> int | None:
    match = re.match(r"(\d{1,2})", value)
    if not match:
        return None
    day = int(match.group(1))
    if 1 <= day <= 31:
        return day
    return None


def _valid_day(year: int, month: int, day: int) -> bool:
    if month < 1 or month > 12:
        return False
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _normalize_season(value: str) -> str:
    lowered = value.lower()
    if lowered == "autumn":
        return "autumn"
    return lowered


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def _period_from_text(cleaned: str) -> str | None:
    if re.search(r"\b(am|morning)\b", cleaned):
        return "am"
    if re.search(r"\b(pm|evening|night)\b", cleaned):
        return "pm"
    return None


def _to_24_hour(hour12: int, period: str) -> int:
    period = period.lower()
    if period.startswith("a"):
        return 0 if hour12 == 12 else hour12
    return 12 if hour12 == 12 else hour12 + 12


def _complete_time(hour24: int, minute: int, approximate: bool) -> TimeRead:
    if hour24 < 0 or hour24 > 23 or minute < 0 or minute > 59:
        return TimeRead(status="invalid")
    hour12 = hour24 % 12 or 12
    suffix = "AM" if hour24 < 12 else "PM"
    label = f"{hour12}:{minute:02d} {suffix}"
    if approximate:
        label = f"around {label}"
    return TimeRead(
        status="complete",
        label=label,
        hour24=f"{hour24:02d}:{minute:02d}",
        approximate=approximate,
    )
