"""Natal positions and major transits.

What this file does:
    Asks Kerykeion for real planetary longitudes, then checks a short list
    of major aspects.

What enters:
    A birth date, birth time, and city coordinates, plus the dates to compare.

What happens inside:
    Kerykeion reads the local ephemeris. No city name is sent to a geocoding
    service. This file then looks only at Jupiter, Saturn, Uranus, and Pluto,
    and only at conjunctions, squares, and oppositions within 7 degrees.

What it returns:
    Planet signs for the natal chart, and the major transit hits on a date.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from kerykeion import AstrologicalSubjectFactory

from app.data.cities import CityLocation

TRANSIT_PLANETS = ("Jupiter", "Saturn", "Uranus", "Pluto")
NATAL_TARGETS = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
ACTIVE_POINTS = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
]
ASPECT_ANGLES = (("conjunction", 0), ("square", 90), ("opposition", 180))
ORB_DEGREES = 7.0

SIGN_NAMES = {
    "Ari": "Aries",
    "Tau": "Taurus",
    "Gem": "Gemini",
    "Can": "Cancer",
    "Leo": "Leo",
    "Vir": "Virgo",
    "Lib": "Libra",
    "Sco": "Scorpio",
    "Sag": "Sagittarius",
    "Cap": "Capricorn",
    "Aqu": "Aquarius",
    "Pis": "Pisces",
}


@dataclass(frozen=True)
class PlanetPosition:
    name: str
    sign: str
    degree: float
    longitude: float


@dataclass(frozen=True)
class TransitHit:
    transit_planet: str
    aspect: str
    natal_planet: str
    orb: float


@dataclass(frozen=True)
class NatalChart:
    planets: dict[str, PlanetPosition]
    ascendant_sign: str | None
    time_note: str


def planet_positions(moment: date, hour: int, minute: int, city: CityLocation) -> dict[str, PlanetPosition]:
    """Calculate planet positions for one local date and time."""

    subject = AstrologicalSubjectFactory.from_birth_data(
        "Chart",
        moment.year,
        moment.month,
        moment.day,
        hour,
        minute,
        lng=city.longitude,
        lat=city.latitude,
        tz_str=city.timezone,
        online=False,
        active_points=ACTIVE_POINTS,
    )
    positions: dict[str, PlanetPosition] = {}
    for name in ACTIVE_POINTS:
        point = getattr(subject, name.lower())
        positions[name] = PlanetPosition(
            name=name,
            sign=SIGN_NAMES.get(point.sign, point.sign),
            degree=round(point.position, 1),
            longitude=point.abs_pos,
        )
    return positions


def natal_chart(
    birth_day: date,
    hour: int,
    minute: int,
    city: CityLocation,
    *,
    time_unknown: bool,
    time_approximate: bool,
) -> NatalChart:
    """Calculate the birth chart. Unknown times use noon and skip the Moon later."""

    positions = planet_positions(birth_day, hour, minute, city)
    ascendant = _ascendant_sign(birth_day, hour, minute, city) if not time_unknown else None
    if time_unknown:
        note = "The birth time was unknown, so this chart uses noon. The Moon and Ascendant are not used."
    elif time_approximate:
        note = "The birth time was approximate, so the Moon and Ascendant are less certain than the Sun."
    else:
        note = ""
    return NatalChart(planets=positions, ascendant_sign=ascendant, time_note=note)


def transit_hits(
    natal: dict[str, PlanetPosition],
    transit_positions: dict[str, PlanetPosition],
    *,
    include_moon: bool,
) -> list[TransitHit]:
    """Major aspects from Jupiter, Saturn, Uranus, and Pluto to the natal planets."""

    hits: list[TransitHit] = []
    targets = NATAL_TARGETS if include_moon else tuple(name for name in NATAL_TARGETS if name != "Moon")
    for transit_name in TRANSIT_PLANETS:
        transit_longitude = transit_positions[transit_name].longitude
        for natal_name in targets:
            aspect = major_aspect(transit_longitude, natal[natal_name].longitude)
            if aspect is None:
                continue
            aspect_name, orb = aspect
            hits.append(
                TransitHit(
                    transit_planet=transit_name,
                    aspect=aspect_name,
                    natal_planet=natal_name,
                    orb=round(orb, 2),
                )
            )
    hits.sort(key=lambda hit: hit.orb)
    return hits


def major_aspect(transit_longitude: float, natal_longitude: float) -> tuple[str, float] | None:
    """Return the closest major aspect inside the orb, or None."""

    separation = abs(transit_longitude - natal_longitude) % 360
    if separation > 180:
        separation = 360 - separation
    best: tuple[str, float] | None = None
    for name, angle in ASPECT_ANGLES:
        gap = abs(separation - angle)
        if gap <= ORB_DEGREES and (best is None or gap < best[1]):
            best = (name, gap)
    return best


def _ascendant_sign(moment: date, hour: int, minute: int, city: CityLocation) -> str | None:
    subject = AstrologicalSubjectFactory.from_birth_data(
        "Chart",
        moment.year,
        moment.month,
        moment.day,
        hour,
        minute,
        lng=city.longitude,
        lat=city.latitude,
        tz_str=city.timezone,
        online=False,
        active_points=ACTIVE_POINTS,
    )
    ascendant = getattr(subject, "ascendant", None)
    if ascendant is None or not getattr(ascendant, "sign", None):
        return None
    return SIGN_NAMES.get(ascendant.sign, ascendant.sign)


def clock_from_label(label: str) -> tuple[int, int]:
    """Turn a saved birth-time label such as 'around 9:00 PM' into hour and minute."""

    from app.utils.parsing import parse_time

    parsed = parse_time(label)
    if parsed.status != "complete" or not parsed.hour24:
        raise ValueError(label)
    hour_text, minute_text = parsed.hour24.split(":")
    return int(hour_text), int(minute_text)


def is_unknown_time(label: str) -> bool:
    return label.strip().lower() == "unknown"


def is_approximate_time(label: str) -> bool:
    return label.strip().lower().startswith("around ")
