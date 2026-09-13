"""Small Supabase data layer for authentication and persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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


class SupabaseStore:
    """User-scoped access to Cross Speak AI's Supabase tables."""

    def __init__(self, client: Client) -> None:
        self.client = client

    def sign_up(self, email: str, password: str) -> Any:
        return self.client.auth.sign_up({"email": email, "password": password})

    def sign_in(self, email: str, password: str) -> Any:
        return self.client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )

    def sign_out(self) -> None:
        self.client.auth.sign_out({"scope": "local"})

    def get_role(self, user_id: str) -> str:
        response = (
            self.client.table("profiles")
            .select("role")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return str(response.data.get("role", "user"))

    def get_or_create_conversation(self, user_id: str) -> str:
        response = (
            self.client.table("conversations")
            .select("id")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            return str(response.data[0]["id"])
        return self.create_conversation(user_id)

    def create_conversation(self, user_id: str) -> str:
        response = (
            self.client.table("conversations")
            .insert({"user_id": user_id})
            .execute()
        )
        return str(response.data[0]["id"])

    def get_conversation_context(
        self, conversation_id: str, limit: int
    ) -> list[dict[str, str]]:
        response = (
            self.client.table("translation_history")
            .select("input_text,output_text")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(reversed(response.data or []))

    def save_translation(
        self,
        user_id: str,
        conversation_id: str,
        input_text: str,
        result: Any,
    ) -> None:
        self.client.table("translation_history").insert(
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "input_text": input_text,
                "output_text": result.translation,
                "detected_style": result.detected_style,
                "translation_direction": result.translation_direction,
                "terms_used": result.terms_used,
            }
        ).execute()
        self.client.table("conversations").update(
            {"updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", conversation_id).execute()

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        response = (
            self.client.table("translation_history")
            .select(
                "id,input_text,output_text,detected_style,"
                "translation_direction,terms_used,created_at"
            )
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def submit_suggestion(
        self,
        user_id: str,
        term: str,
        category: str,
        meaning: str,
        translation: str,
        example: str,
        context: str,
    ) -> None:
        self.client.table("slang_suggestions").insert(
            {
                "user_id": user_id,
                "term": term,
                "category": category,
                "meaning": meaning,
                "translation": translation,
                "example": example,
                "context": context,
            }
        ).execute()

    def get_suggestions(self, pending_only: bool = False) -> list[dict[str, Any]]:
        query = self.client.table("slang_suggestions").select("*")
        if pending_only:
            query = query.eq("status", "pending")
        response = query.order("created_at", desc=True).execute()
        return response.data or []

    def approve_suggestion(
        self, suggestion: dict[str, Any], embedding: list[float]
    ) -> None:
        self.client.rpc(
            "approve_slang_suggestion",
            {
                "p_suggestion_id": suggestion["id"],
                "p_edited_term": suggestion["term"],
                "p_edited_category": suggestion["category"],
                "p_edited_meaning": suggestion["meaning"],
                "p_edited_translation": suggestion["translation"],
                "p_edited_example": suggestion.get("example", ""),
                "p_edited_context": suggestion.get("context", ""),
                "p_new_embedding": embedding,
            },
        ).execute()

    def reject_suggestion(self, suggestion_id: str, reason: str) -> None:
        self.client.rpc(
            "reject_slang_suggestion",
            {"p_suggestion_id": suggestion_id, "p_reason": reason},
        ).execute()

    def search_approved_terms(
        self,
        query_embedding: list[float],
        threshold: float = 0.45,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        response = self.client.rpc(
            "match_approved_terms",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": limit,
            },
        ).execute()
        return response.data or []

    def get_approved_terms(self) -> list[dict[str, Any]]:
        response = (
            self.client.table("approved_terms")
            .select("term,category,meaning,translation,example,context")
            .eq("active", True)
            .order("approved_at", desc=True)
            .execute()
        )
        return response.data or []
