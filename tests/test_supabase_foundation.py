"""Small regression checks for the disabled-by-default Supabase foundation."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core.config import get_settings
from core.supabase_client import create_user_client
from streamlit.testing.v1 import AppTest


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

    def test_streamlit_secrets_enable_integration(self) -> None:
        fake_streamlit = SimpleNamespace(
            secrets={
                "SUPABASE_ENABLED": True,
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_PUBLISHABLE_KEY": "publishable-key",
                "DYNAMIC_KB_ENABLED": True,
            }
        )
        with patch.dict(
            os.environ, self._without_supabase_environment(), clear=True
        ), patch.dict(sys.modules, {"streamlit": fake_streamlit}):
            settings = get_settings()

        self.assertTrue(settings.supabase_enabled)
        self.assertTrue(settings.dynamic_kb_enabled)
        self.assertEqual(settings.supabase_url, "https://example.supabase.co")

    def test_enabled_integration_blocks_anonymous_app_access(self) -> None:
        environment = self._without_supabase_environment()
        environment["SUPABASE_ENABLED"] = "true"
        with patch.dict(os.environ, environment, clear=True):
            app = AppTest.from_file("app.py").run(timeout=10)

        self.assertEqual(len(app.tabs), 0)
        self.assertIn("Sign in or register", app.caption[0].value)


if __name__ == "__main__":
    unittest.main()
