"""Small regression checks for the disabled-by-default Supabase foundation."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from core.config import get_settings
from core.supabase_client import create_user_client


class SupabaseFoundationTests(unittest.TestCase):
    @staticmethod
    def _without_supabase_environment() -> dict[str, str]:
        return {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("SUPABASE_")
        }

    def test_integration_is_disabled_by_default(self) -> None:
        with patch.dict(
            os.environ, self._without_supabase_environment(), clear=True
        ):
            settings = get_settings()

        self.assertFalse(settings.supabase_enabled)
        self.assertEqual(settings.supabase_url, "")
        self.assertEqual(settings.supabase_publishable_key, "")

    def test_disabled_integration_never_creates_a_client(self) -> None:
        with patch.dict(
            os.environ, self._without_supabase_environment(), clear=True
        ):
            settings = get_settings()
        with self.assertRaisesRegex(RuntimeError, "disabled"):
            create_user_client(settings)


if __name__ == "__main__":
    unittest.main()
