"""Supabase client construction for optional account features."""

from __future__ import annotations

from supabase import Client, create_client

from core.config import Settings


def create_user_client(settings: Settings) -> Client:
    """Create a user-scoped client; never cache this across Streamlit sessions."""
    if not settings.supabase_enabled:
        raise RuntimeError("Supabase integration is disabled.")
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are required when "
            "SUPABASE_ENABLED is true."
        )
    return create_client(
        settings.supabase_url,
        settings.supabase_publishable_key,
    )
