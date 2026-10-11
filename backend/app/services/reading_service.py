"""Build one template reading from a saved profile.

What this file does:
    Loads a confirmed profile, compares the three past events, searches the
    next 18 months, and fills in a fixed reading template.

What enters:
    A user id that already exists in SQLite.

What happens inside:
    The birth city is converted with the built-in coordinate list. Kerykeion
    supplies planet positions. pattern_service scores repeated transits.
    The future search keeps the date where the strongest repeated pattern
    is closest to exact, then widens that date into a short window.

What it returns:
    The reading sections the result page displays. The wording stays
    suggestive. It does not say that an event will happen.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.data.cities import lookup_city
from app.schemas.reading import ReadingOut
from app.schemas.user import LifeEventOut, UserProfileOut
from app.services.astrology_service import (
    ORB_DEGREES,
    NatalChart,
    TransitHit,
    clock_from_label,
    is_approximate_time,
    is_unknown_time,
    natal_chart,
    planet_positions,
    transit_hits,
)
from app.services.pattern_service import RepeatedPattern, matching_hit, repeated_patterns, tightest_hit
from app.services.profile_service import get_user
from app.utils.parsing import DateProgress, find_date_mentions, interpret_date

DISCLAIMER = (
    "This application is intended for entertainment and self-reflection. "
    "Astrology is not scientifically established as a method of predicting future events. "
    "Do not use this application as a substitute for medical, financial, legal, or other professional advice."
)

SEARCH_DAYS = 548
SEARCH_STEP_DAYS = 14
SEASON_MONTHS = {"spring": 4, "summer": 7, "autumn": 10, "winter": 1}

PLANET_THEMES = {
    "Saturn": "responsibility and long-term structure",
    "Jupiter": "growth, learning, or a wider horizon",
    "Uranus": "change, independence, or a shift in direction",
    "Pluto": "transformation and letting go of an old pattern",
}
CATEGORY_THEMES = {
    "Career": "career direction",
    "Relocation": "home or relocation questions",
    "Education": "study or training",
    "Relationship": "relationship changes",
    "Family": "family responsibilities",
    "Loss": "grief or a major ending",
    "Financial": "money and commitments",
    "Health": "health routines",
    "Personal": "personal direction",
    "Other": "a personal turning point",
}
PREPARATION = {
    "Saturn": (
        "Review long-term commitments, keep some flexibility in your schedule, "
        "and give important decisions more than one conversation."
    ),
    "Jupiter": (
        "Look at one area you want to grow, and leave room to explore it "
        "without treating every opportunity as urgent."
    ),
    "Uranus": (
        "Leave room for a change of plan, and notice where you want more independence "
        "before making a sudden break."
    ),
    "Pluto": (
        "Use the period to finish something that already feels complete, "
        "and avoid forcing a dramatic decision on a deadline."
    ),
}


class ProfileNotFound(Exception):
    """No SQLite profile exists for this id."""


class ChartInputError(Exception):
    """The saved profile cannot be turned into a chart with the local data."""


@dataclass(frozen=True)
class _Focus:
    planet: str
    aspect: str
    natal: str
    event_indexes: tuple[int, ...]
    repeated: bool

    @property
    def label(self) -> str:
        return f"{self.planet} {self.aspect} natal {self.natal}"


def build_reading(user_id: int, today: date | None = None) -> ReadingOut:
    profile = get_user(user_id)
    if profile is None:
        raise ProfileNotFound(f"No saved profile with id {user_id}.")
    if len(profile.life_events) != 3:
        raise ChartInputError("A reading needs exactly three saved life events.")

    city = lookup_city(profile.birth_city)
    if city is None:
        raise ChartInputError(
            f"'{profile.birth_city}' is not in the built-in city list, so coordinates "
            "are not available. This prototype recognizes major cities such as Seattle, "
            "Austin, Chicago, and New York."
        )

    clock = today or date.today()
    birth_day = _birth_day(profile.birth_date, clock)
    hour, minute, time_unknown, time_approximate = _birth_clock(profile.birth_time)
    chart = natal_chart(
        birth_day,
        hour,
        minute,
        city,
        time_unknown=time_unknown,
        time_approximate=time_approximate,
    )

    event_dates = [_event_day(event.event_date, clock) for event in profile.life_events]
    event_hit_lists = [
        transit_hits(
            chart.planets,
            planet_positions(event_day, 12, 0, city),
            include_moon=not time_unknown,
        )
        for event_day in event_dates
    ]
    focus = _choose_focus(event_hit_lists)
    window = _future_window(chart, city, focus, clock, include_moon=not time_unknown)

    return ReadingOut(
        user_id=user_id,
        natal_summary=_natal_summary(chart),
        time_note=chart.time_note,
        past_pattern=_past_pattern(focus, profile.life_events),
        future_window=window.label,
        themes=_themes(focus, profile.life_events),
        why=_why(focus, window),
        similarities=_similarities(focus, profile.life_events),
        preparation=PREPARATION[focus.planet],
        disclaimer=DISCLAIMER,
    )


def _choose_focus(event_hit_lists: list[list[TransitHit]]) -> _Focus:
    patterns = repeated_patterns(event_hit_lists)
    if patterns:
        best: RepeatedPattern = patterns[0]
        return _Focus(
            planet=best.transit_planet,
            aspect=best.aspect,
            natal=best.natal_planet,
            event_indexes=best.event_indexes,
            repeated=True,
        )
    single = tightest_hit(event_hit_lists)
    if single is not None:
        index, hit = single
        return _Focus(
            planet=hit.transit_planet,
            aspect=hit.aspect,
            natal=hit.natal_planet,
            event_indexes=(index,),
            repeated=False,
        )
    return _Focus("Saturn", "conjunction", "Sun", (), False)


@dataclass(frozen=True)
class _Window:
    label: str
    peak: TransitHit | None


def _future_window(
    chart: NatalChart,
    city,
    focus: _Focus,
    today: date,
    *,
    include_moon: bool,
) -> _Window:
    """Search about 18 months for the closest repeat of the past pattern.

    An exact transit-to-natal repeat ranks first. If that pair stays outside
    the orb, the search keeps the tightest major aspect from the same planet.
    """

    samples: list[tuple[date, TransitHit, int]] = []
    for offset in range(0, SEARCH_DAYS + 1, SEARCH_STEP_DAYS):
        sample_day = today + timedelta(days=offset)
        hits = transit_hits(
            chart.planets,
            planet_positions(sample_day, 12, 0, city),
            include_moon=include_moon,
        )
        chosen = _best_similar_hit(focus, hits)
        if chosen is not None:
            hit, rank = chosen
            samples.append((sample_day, hit, rank))

    if not samples:
        return _Window("No close repeat turned up in the next 18 months", None)

    peak_day, peak_hit, peak_rank = max(samples, key=lambda item: (item[2], -item[1].orb, -item[0].toordinal()))
    cluster = [
        day
        for day, hit, rank in samples
        if rank == peak_rank
        and hit.aspect == peak_hit.aspect
        and hit.natal_planet == peak_hit.natal_planet
        and abs((day - peak_day).days) <= 60
        and hit.orb <= peak_hit.orb + 1
    ]
    start = min(cluster)
    end = max(cluster)
    if start.year == end.year and start.month == end.month:
        end = _month_end(start, 1)
    return _Window(_format_window(start, end), peak_hit)


def _best_similar_hit(focus: _Focus, hits: list[TransitHit]) -> tuple[TransitHit, int] | None:
    """Rank one date. 3 is an exact repeat, 2 is the same planet and aspect."""

    exact = matching_hit(focus.planet, focus.aspect, focus.natal, hits)
    if exact is not None:
        return exact, 3
    same_aspect = [
        hit for hit in hits if hit.transit_planet == focus.planet and hit.aspect == focus.aspect
    ]
    if same_aspect:
        return min(same_aspect, key=lambda hit: hit.orb), 2
    same_planet = [hit for hit in hits if hit.transit_planet == focus.planet]
    if same_planet:
        return min(same_planet, key=lambda hit: hit.orb), 1
    return None


def _birth_day(label: str, today: date) -> date:
    reading = interpret_date(label, DateProgress(), require_day=True, include_partials=True, today=today)
    if reading.status != "complete" or reading.progress is None:
        raise ChartInputError(f"The saved birth date '{label}' does not include a full day.")
    progress = reading.progress
    assert progress.year and progress.month and progress.day
    return date(progress.year, progress.month, progress.day)


def _birth_clock(label: str) -> tuple[int, int, bool, bool]:
    if is_unknown_time(label):
        return 12, 0, True, False
    try:
        hour, minute = clock_from_label(label)
    except ValueError as error:
        raise ChartInputError(f"The saved birth time '{label}' could not be read.") from error
    return hour, minute, False, is_approximate_time(label)


def _event_day(label: str, today: date) -> date:
    mentions = find_date_mentions(label, include_partials=True)
    if len(mentions) != 1 or mentions[0].ambiguous or mentions[0].invalid:
        raise ChartInputError(f"The saved event date '{label}' is not clear enough to calculate.")
    mention = mentions[0]
    if mention.year and mention.month and mention.day:
        resolved = date(mention.year, mention.month, mention.day)
    elif mention.year and mention.month:
        resolved = date(mention.year, mention.month, 15)
    elif mention.year and mention.season:
        resolved = date(mention.year, SEASON_MONTHS[mention.season], 15)
    elif mention.year:
        resolved = date(mention.year, 7, 1)
    else:
        raise ChartInputError(f"The saved event date '{label}' is not clear enough to calculate.")
    if resolved > today:
        raise ChartInputError(f"The saved event date '{label}' is still in the future.")
    return resolved


def _natal_summary(chart: NatalChart) -> str:
    sun = chart.planets["Sun"]
    parts = [f"Sun in {sun.sign} ({sun.degree:.0f}°)"]
    if "The birth time was unknown" not in chart.time_note:
        moon = chart.planets["Moon"]
        parts.append(f"Moon in {moon.sign} ({moon.degree:.0f}°)")
    if chart.ascendant_sign:
        parts.append(f"Ascendant in {chart.ascendant_sign}")
    return ". ".join(parts) + "."


def _past_pattern(focus: _Focus, events: list[LifeEventOut]) -> str:
    if focus.repeated:
        count = len(focus.event_indexes)
        return (
            f"The strongest repeated pattern is {focus.label}. "
            f"It showed up in {count} of your 3 saved life events."
        )
    if focus.event_indexes:
        event = events[focus.event_indexes[0]]
        return (
            "The three events did not share one repeated major transit. "
            f"The closest single pattern was {focus.label}, near the {event.event_date} event."
        )
    return (
        "None of the three events had a conjunction, square, or opposition "
        "from Jupiter, Saturn, Uranus, or Pluto within 7 degrees of the natal planets checked here."
    )


def _why(focus: _Focus, window: _Window) -> str:
    if window.peak is None:
        return (
            f"No close repeat of {focus.label} turned up in the next 18 months, "
            "so this reading does not highlight a future date."
        )
    found = f"{window.peak.transit_planet} {window.peak.aspect} natal {window.peak.natal_planet}"
    closeness = "fairly close" if window.peak.orb <= 3 else "within the same wide orb used for the past events"
    same = (
        window.peak.transit_planet == focus.planet
        and window.peak.aspect == focus.aspect
        and window.peak.natal_planet == focus.natal
    )
    if same and focus.repeated:
        return (
            f"This period may be associated with another {focus.label}. "
            f"Around {window.label}, that pattern is {closeness} to exact, "
            "which is why this window stands out from the other months searched."
        )
    if same:
        return (
            f"This period may be associated with {focus.label}. "
            "The past events did not repeat this pattern, so the similarity is limited to the closest single event."
        )
    return (
        f"This period may be associated with {found}. "
        f"The repeated past pattern, {focus.label}, does not come within {ORB_DEGREES:.0f} degrees "
        "during the next 18 months. "
        f"Around {window.label}, the closest similar pass is another {window.peak.transit_planet} {window.peak.aspect}, "
        "and that is the tightest one in the search."
    )


def _similarities(focus: _Focus, events: list[LifeEventOut]) -> str:
    if not focus.event_indexes:
        return "There is not a past event close enough to compare with this window."
    pieces = []
    for index in focus.event_indexes:
        event = events[index]
        pieces.append(f"{event.event_date} ({event.event_type}: {event.description})")
    joined = "; ".join(pieces)
    if focus.repeated:
        return f"This pattern is similar to the transits near: {joined}."
    return f"The only close past comparison in this chart is: {joined}."


def _themes(focus: _Focus, events: list[LifeEventOut]) -> list[str]:
    themes = [PLANET_THEMES[focus.planet]]
    for index in focus.event_indexes:
        for part in events[index].event_type.split(" / "):
            theme = CATEGORY_THEMES.get(part)
            if theme and theme not in themes:
                themes.append(theme)
        if len(themes) == 3:
            break
    if len(themes) < 2:
        themes.append("paying attention to timing before making a lasting choice")
    return themes[:3]


def _format_window(start: date, end: date) -> str:
    if start.year == end.year and start.month == end.month:
        return start.strftime("%B %Y")
    if start.year == end.year:
        return f"{start.strftime('%B')}–{end.strftime('%B')} {end.year}"
    return f"{start.strftime('%B %Y')}–{end.strftime('%B %Y')}"


def _month_end(start: date, months_ahead: int) -> date:
    month = start.month + months_ahead
    year = start.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, 1)
