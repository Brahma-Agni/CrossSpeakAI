"""Regression checks for registration persona validation."""

import unittest

from pydantic import ValidationError

from server import AuthRequest


class RegistrationPersonaTests(unittest.TestCase):
    def test_registration_accepts_only_supported_personas(self) -> None:
        self.assertEqual(AuthRequest(email="a@example.com", password="secret", user_mode="genz").user_mode, "genz")
        with self.assertRaises(ValidationError):
            AuthRequest(email="a@example.com", password="secret", user_mode="other")


if __name__ == "__main__":
    unittest.main()
