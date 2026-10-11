"""Checks for the local data-handling fixes. No network calls."""

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.exceptions import RequestValidationError

from app.database import close_db, init_db
from app.main import public_validation_errors
from app.services.profile_service import ProfileSaveError, count_profiles, get_user, save_confirmed_profile


class SecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "test.db"
        os.environ["TURNING_POINT_DB"] = str(self.db_path)
        init_db()

    def tearDown(self) -> None:
        close_db()
        self._tmp.cleanup()
        os.environ.pop("TURNING_POINT_DB", None)

    def test_database_file_is_private_to_this_user(self) -> None:
        mode = self.db_path.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_sql_metacharacters_are_stored_as_text(self) -> None:
        payload = "I left'; DROP TABLE user_profiles; --"
        user_id = save_confirmed_profile(
            birth_date="May 8, 1997",
            birth_time="Unknown",
            birth_city="Seattle",
            current_city="Austin",
            events=[
                (["career"], "2019", payload),
                (["education"], "2020", "Finished school."),
                (["family"], "2018", "A family change."),
            ],
        )
        saved = get_user(user_id)
        assert saved is not None
        self.assertEqual(saved.life_events[0].description, payload)
        self.assertEqual(count_profiles(), 1)

    def test_oversized_event_is_rejected_without_echoing_it(self) -> None:
        secret = "private event " * 200
        with self.assertRaises(ProfileSaveError) as caught:
            save_confirmed_profile(
                birth_date="May 8, 1997",
                birth_time="Unknown",
                birth_city="Seattle",
                current_city="Austin",
                events=[
                    (["career"], "2019", secret),
                    (["education"], "2020", "Finished school."),
                    (["family"], "2018", "A family change."),
                ],
            )
        self.assertNotIn("private event", str(caught.exception))
        self.assertEqual(count_profiles(), 0)

    def test_validation_error_omits_the_submitted_text(self) -> None:
        personal = "My grandfather passed away in 2018"
        exc = RequestValidationError(
            [
                {
                    "type": "string_too_long",
                    "loc": ("body", "text"),
                    "msg": "String should have at most 1000 characters",
                    "input": personal,
                }
            ]
        )
        rendered = str(public_validation_errors(exc))
        self.assertIn(personal, str(exc.errors()))
        self.assertNotIn(personal, rendered)


if __name__ == "__main__":
    unittest.main()
