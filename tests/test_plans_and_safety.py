"""Regression checks for plans and the language safety guard."""

from types import SimpleNamespace
import unittest

from core.content_guard import contains_abusive_language
from server import LocalAuthStore


class PlanAndSafetyTests(unittest.TestCase):
    def test_sign_in_requires_an_existing_account_and_valid_token(self) -> None:
        store = LocalAuthStore()
        with self.assertRaisesRegex(Exception, "Invalid email or password"):
            store.sign_in("missing@example.com", "secret")
        with self.assertRaisesRegex(ValueError, "Invalid or expired session"):
            store.get_user_by_token("made-up-token")

    def test_free_is_limited_to_three_and_paid_is_unlimited(self) -> None:
        store = LocalAuthStore()
        auth = store.sign_up("free@example.com", "secret")
        user_id = auth.user.id
        conversation_id = store.create_conversation(user_id)
        result = SimpleNamespace(
            translation="translated",
            detected_style="Corporate",
            translation_direction="corporate_to_genz",
            terms_used=[],
        )

        for _ in range(3):
            store.save_translation(user_id, conversation_id, "input", result)

        self.assertEqual(store.check_quota(user_id, "free"), (3, 3, False))
        self.assertEqual(store.check_quota(user_id, "paid"), (3, -1, True))

    def test_abusive_and_obfuscated_words_are_blocked(self) -> None:
        self.assertTrue(contains_abusive_language("This is fucking awful"))
        self.assertTrue(contains_abusive_language("What the f0ck"))
        self.assertTrue(contains_abusive_language("f.u.c.k"))
        self.assertFalse(contains_abusive_language("Please translate this project update"))


if __name__ == "__main__":
    unittest.main()
