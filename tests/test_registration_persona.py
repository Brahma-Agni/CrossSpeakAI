"""Regression checks for registration persona validation."""

import unittest

from pydantic import ValidationError

from server import AuthRequest, LocalAuthStore, allowed_translation_mode


class RegistrationPersonaTests(unittest.TestCase):
    def test_registration_accepts_only_supported_personas(self) -> None:
        self.assertEqual(AuthRequest(email="a@example.com", password="secret", user_mode="genz").user_mode, "genz")
        with self.assertRaises(ValidationError):
            AuthRequest(email="a@example.com", password="secret", user_mode="other")

    def test_only_admin_can_choose_translation_direction(self) -> None:
        store = LocalAuthStore()
        user = store.sign_up("user@example.com", "secret", "genz").user
        admin = store.sign_up("admin@csai.com", "secret", "corporate").user
        other_admin = store.sign_up("other-admin@example.com", "secret", "corporate").user
        store.users[other_admin.id].role = "admin"

        self.assertEqual(
            allowed_translation_mode(store, user.id, user.email, "corporate_to_genz"),
            "genz_to_corporate",
        )
        self.assertEqual(
            allowed_translation_mode(store, admin.id, admin.email, "genz_to_corporate"),
            "genz_to_corporate",
        )
        self.assertEqual(
            allowed_translation_mode(
                store, other_admin.id, other_admin.email, "genz_to_corporate"
            ),
            "corporate_to_genz",
        )


if __name__ == "__main__":
    unittest.main()
