"""Compare transit hits across the three life events.

What this file does:
    Scores repeated astrology patterns. It does not calculate planet positions.

What enters:
    The major transit hits already found for each past event.

What happens inside:
    A pattern such as "Saturn square natal Sun" gets a higher score when it
    shows up in more than one event, and a small bonus when the aspect is tighter.

What it returns:
    The repeated patterns, strongest first. A pattern must appear in at least
    two events before it counts as repeated.
"""

from dataclasses import dataclass

from app.services.astrology_service import ORB_DEGREES, TransitHit


@dataclass(frozen=True)
class RepeatedPattern:
    transit_planet: str
    aspect: str
    natal_planet: str
    event_indexes: tuple[int, ...]
    score: float

    @property
    def label(self) -> str:
        return f"{self.transit_planet} {self.aspect} natal {self.natal_planet}"


def repeated_patterns(event_hits: list[list[TransitHit]]) -> list[RepeatedPattern]:
    """Find transit-to-natal patterns that appear in at least two events."""

    grouped: dict[tuple[str, str, str], list[tuple[int, float]]] = {}
    for index, hits in enumerate(event_hits):
        seen: dict[tuple[str, str, str], float] = {}
        for hit in hits:
            key = (hit.transit_planet, hit.aspect, hit.natal_planet)
            seen[key] = min(hit.orb, seen.get(key, hit.orb))
        for key, orb in seen.items():
            grouped.setdefault(key, []).append((index, orb))

    patterns: list[RepeatedPattern] = []
    for (planet, aspect, natal), occurrences in grouped.items():
        if len(occurrences) < 2:
            continue
        tightness = sum(max(0.0, ORB_DEGREES - orb) for _, orb in occurrences)
        score = len(occurrences) * 10 + tightness
        patterns.append(
            RepeatedPattern(
                transit_planet=planet,
                aspect=aspect,
                natal_planet=natal,
                event_indexes=tuple(index for index, _ in occurrences),
                score=round(score, 2),
            )
        )
    patterns.sort(key=lambda pattern: (-pattern.score, -len(pattern.event_indexes), pattern.label))
    return patterns


def tightest_hit(event_hits: list[list[TransitHit]]) -> tuple[int, TransitHit] | None:
    """The single closest aspect in any event, used when nothing repeats."""

    best: tuple[int, TransitHit] | None = None
    for index, hits in enumerate(event_hits):
        for hit in hits:
            if best is None or hit.orb < best[1].orb:
                best = (index, hit)
    return best


def matching_hit(pattern_planet: str, pattern_aspect: str, pattern_natal: str, hits: list[TransitHit]) -> TransitHit | None:
    """The tightest hit on this date that matches one pattern."""

    matches = [
        hit
        for hit in hits
        if hit.transit_planet == pattern_planet
        and hit.aspect == pattern_aspect
        and hit.natal_planet == pattern_natal
    ]
    if not matches:
        return None
    return min(matches, key=lambda hit: hit.orb)
