"""State-machine checks. These do not start the web server."""

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.database import close_db, init_db
from app.services.conversation_service import (
    handle_message,
    reset_for_tests,
    restart_session,
    start_session,
)
from app.services.profile_service import count_profiles, get_user

TODAY = date(2026, 10, 4)


class ConversationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["TURNING_POINT_DB"] = str(Path(self._tmp.name) / "test.db")
        init_db()
        reset_for_tests()

    def tearDown(self) -> None:
        close_db()
        self._tmp.cleanup()
        os.environ.pop("TURNING_POINT_DB", None)

    def test_full_conversation_with_dates_inside_events(self) -> None:
        session_id = start_session().session_id
        steps = [
            ("May 8, 1997", "collect_birth_time"),
            ("Around 9 PM", "collect_birth_city"),
            ("Seattle", "collect_current_city"),
            ("Austin", "collect_event_1"),
            (
                "I moved to the United States in August 2019 for school.",
                "collect_event_2",
            ),
            ("I started a new job in March 2022.", "collect_event_3"),
            ("My grandfather passed away in 2018.", "confirm_information"),
        ]
        replies: list[str] = []
        for text, expected_state in steps:
            result = handle_message(session_id, text, today=TODAY)
            self.assertEqual(result.state, expected_state, result.replies)
            replies.extend(result.replies)

        joined = "\n".join(replies)
        self.assertIn("Relocation / Education — August 2019", joined)
        self.assertIn("Career — March 2022", joined)
        self.assertIn("Loss / Family — 2018", joined)
        self.assertIn("around 9:00 PM", joined)
        self.assertIn("Reply yes", joined)

        confirmed = handle_message(session_id, "yes", today=TODAY)
        self.assertEqual(confirmed.state, "confirmed")
        self.assertIn("Click Analyze", confirmed.replies[0])
        self.assertIsNotNone(confirmed.user_id)
        saved = get_user(confirmed.user_id or 0)
        assert saved is not None
        self.assertEqual(saved.birth_city, "Seattle")
        self.assertEqual(len(saved.life_events), 3)
        self.assertEqual(saved.life_events[0].event_type, "Relocation / Education")
        self.assertEqual(saved.life_events[0].event_date, "August 2019")

    def test_event_without_a_date_asks_before_moving_on(self) -> None:
        session_id = self._reach_first_event()
        result = handle_message(session_id, "I started a new job", today=TODAY)
        self.assertEqual(result.state, "collect_event_1_date")
        self.assertIn("Career", result.replies[0])
        self.assertNotIn("collect_event_2", result.state)

        dated = handle_message(session_id, "summer 2021", today=TODAY)
        self.assertEqual(dated.state, "collect_event_2")
        self.assertIn("Summer 2021", dated.replies[0])

    def test_year_only_and_month_year_are_accepted_for_events(self) -> None:
        session_id = self._reach_first_event()
        handle_message(session_id, "I changed careers", today=TODAY)
        result = handle_message(session_id, "2019", today=TODAY)
        self.assertEqual(result.state, "collect_event_2")
        self.assertIn("2019", result.replies[0])

    def test_unclear_birth_date_asks_for_the_missing_day(self) -> None:
        session_id = start_session().session_id
        partial = handle_message(session_id, "March 1997", today=TODAY)
        self.assertEqual(partial.state, "collect_birth_date")
        self.assertIn("What day in March 1997", partial.replies[0])

        done = handle_message(session_id, "8", today=TODAY)
        self.assertEqual(done.state, "collect_birth_time")
        self.assertIn("March 8, 1997", done.replies[0])

    def test_ambiguous_numeric_date_is_not_guessed(self) -> None:
        session_id = start_session().session_id
        result = handle_message(session_id, "05/06/1997", today=TODAY)
        self.assertEqual(result.state, "collect_birth_date")
        self.assertIn("two ways", result.replies[0])

    def test_unknown_birth_time_moves_forward(self) -> None:
        session_id = start_session().session_id
        handle_message(session_id, "May 8, 1997", today=TODAY)
        result = handle_message(session_id, "I don't know", today=TODAY)
        self.assertEqual(result.state, "collect_birth_city")
        self.assertIn("without a birth time", result.replies[0])

    def test_time_without_am_pm_asks_a_follow_up(self) -> None:
        session_id = start_session().session_id
        handle_message(session_id, "May 8, 1997", today=TODAY)
        partial = handle_message(session_id, "around 9", today=TODAY)
        self.assertEqual(partial.state, "collect_birth_time")
        self.assertIn("morning or the evening", partial.replies[0])
        done = handle_message(session_id, "evening", today=TODAY)
        self.assertEqual(done.state, "collect_birth_city")
        self.assertIn("around 9:00 PM", done.replies[0])

    def test_yes_is_not_accepted_as_a_city(self) -> None:
        session_id = start_session().session_id
        handle_message(session_id, "May 8, 1997", today=TODAY)
        handle_message(session_id, "9 PM", today=TODAY)
        result = handle_message(session_id, "yes", today=TODAY)
        self.assertEqual(result.state, "collect_birth_city")

    def test_may_as_a_verb_is_not_treated_as_a_month(self) -> None:
        session_id = self._reach_first_event()
        result = handle_message(
            session_id,
            "I may have changed jobs in 2019",
            today=TODAY,
        )
        self.assertEqual(result.state, "collect_event_2")
        self.assertIn("Career — 2019", result.replies[0])
        self.assertNotIn("May", result.replies[0])

    def test_two_dates_ask_which_one_to_use(self) -> None:
        session_id = self._reach_first_event()
        result = handle_message(
            session_id,
            "I left my job in 2018 and moved in 2019.",
            today=TODAY,
        )
        self.assertEqual(result.state, "collect_event_1_date")
        self.assertIn("more than one date", result.replies[0])
        chosen = handle_message(session_id, "2019", today=TODAY)
        self.assertEqual(chosen.state, "collect_event_2")
        self.assertIn("2019", chosen.replies[0])

    def test_future_event_date_is_rejected(self) -> None:
        session_id = self._reach_first_event()
        handle_message(session_id, "I moved to Chicago", today=TODAY)
        result = handle_message(session_id, "November 2026", today=TODAY)
        self.assertEqual(result.state, "collect_event_1_date")
        self.assertIn("future", result.replies[0])

    def test_no_on_the_summary_starts_over(self) -> None:
        session_id = self._finish_events()
        result = handle_message(session_id, "no", today=TODAY)
        self.assertEqual(result.state, "collect_birth_date")
        self.assertIn("start over", result.replies[0])

    def test_yes_twice_saves_one_profile(self) -> None:
        session_id = self._finish_events()
        first = handle_message(session_id, "yes", today=TODAY)
        second = handle_message(session_id, "yes", today=TODAY)
        self.assertEqual(first.user_id, second.user_id)
        self.assertEqual(count_profiles(), 1)
        self.assertIn("already saved", second.replies[0])

    def test_restart_keeps_the_saved_profile(self) -> None:
        session_id = self._finish_events()
        saved = handle_message(session_id, "yes", today=TODAY)
        restart_session(session_id)
        profile = get_user(saved.user_id or 0)
        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertEqual(len(profile.life_events), 3)

    def test_restart_returns_a_new_session(self) -> None:
        first = start_session()
        handle_message(first.session_id, "May 8, 1997", today=TODAY)
        restarted = restart_session(first.session_id)
        self.assertNotEqual(first.session_id, restarted.session_id)
        self.assertEqual(restarted.state, "collect_birth_date")
        self.assertIn("date of birth", restarted.replies[-1])

    def _reach_first_event(self) -> str:
        started = start_session()
        session_id = started.session_id
        handle_message(session_id, "May 8, 1997", today=TODAY)
        handle_message(session_id, "9 PM", today=TODAY)
        handle_message(session_id, "Seattle", today=TODAY)
        current = handle_message(session_id, "Austin", today=TODAY)
        self.assertEqual(current.state, "collect_event_1")
        return session_id

    def _finish_events(self) -> str:
        session_id = self._reach_first_event()
        handle_message(session_id, "I moved to Texas in 2019", today=TODAY)
        handle_message(session_id, "I graduated from college", today=TODAY)
        handle_message(session_id, "2020", today=TODAY)
        result = handle_message(session_id, "I got married in summer 2021", today=TODAY)
        self.assertEqual(result.state, "confirm_information")
        return session_id


if __name__ == "__main__":
    unittest.main()
