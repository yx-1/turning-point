"""Pattern scoring and one full local reading. No network calls."""

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.database import close_db, init_db
from app.services.astrology_service import TransitHit, major_aspect
from app.services.pattern_service import repeated_patterns
from app.services.profile_service import save_confirmed_profile
from app.services.reading_service import ChartInputError, build_reading

TODAY = date(2026, 10, 4)


class PatternTests(unittest.TestCase):
    def test_repeated_pair_scores_higher_than_a_one_time_hit(self) -> None:
        events = [
            [TransitHit("Saturn", "square", "Sun", 1.2)],
            [TransitHit("Saturn", "square", "Sun", 2.0), TransitHit("Jupiter", "conjunction", "Moon", 0.4)],
            [TransitHit("Uranus", "opposition", "Mars", 3.0)],
        ]
        patterns = repeated_patterns(events)
        self.assertEqual(patterns[0].label, "Saturn square natal Sun")
        self.assertEqual(patterns[0].event_indexes, (0, 1))

    def test_major_aspect_ignores_a_wide_gap(self) -> None:
        self.assertEqual(major_aspect(10, 10)[0], "conjunction")
        self.assertEqual(major_aspect(0, 90)[0], "square")
        self.assertEqual(major_aspect(0, 180)[0], "opposition")
        self.assertIsNone(major_aspect(0, 30))


class ReadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["TURNING_POINT_DB"] = str(Path(self._tmp.name) / "test.db")
        init_db()

    def tearDown(self) -> None:
        close_db()
        self._tmp.cleanup()
        os.environ.pop("TURNING_POINT_DB", None)

    def test_saved_profile_produces_one_window(self) -> None:
        user_id = save_confirmed_profile(
            birth_date="May 8, 1997",
            birth_time="around 9:00 PM",
            birth_city="Seattle",
            current_city="Austin",
            events=[
                (["relocation", "education"], "August 2019", "I moved to the United States for school."),
                (["career"], "March 2022", "I started a new job."),
                (["loss", "family"], "2018", "My grandfather passed away."),
            ],
        )
        reading = build_reading(user_id, today=TODAY)
        self.assertEqual(reading.user_id, user_id)
        self.assertIn("Sun in", reading.natal_summary)
        self.assertTrue(reading.future_window)
        self.assertGreaterEqual(len(reading.themes), 2)
        self.assertIn("entertainment and self-reflection", reading.disclaimer)
        self.assertNotIn("placeholder", reading.why.lower())
        self.assertNotIn("you will", reading.why.lower())
        self.assertNotIn("you will", reading.past_pattern.lower())
        self.assertNotIn("No close repeat turned up", reading.future_window)

    def test_unknown_city_is_rejected(self) -> None:
        user_id = save_confirmed_profile(
            birth_date="May 8, 1997",
            birth_time="9:00 PM",
            birth_city="Smallville",
            current_city="Austin",
            events=[
                (["career"], "2019", "Started a job."),
                (["career"], "2020", "Changed jobs."),
                (["family"], "2021", "A family change."),
            ],
        )
        with self.assertRaises(ChartInputError):
            build_reading(user_id, today=TODAY)


if __name__ == "__main__":
    unittest.main()
