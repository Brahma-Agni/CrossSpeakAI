"""Small Supabase data layer for authentication and persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from core.config import Settings

FREE_TRANSLATION_LIMIT = 3


def create_user_client(settings: Settings) -> Client:
    """Create a user-scoped Supabase client."""
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


def create_admin_client(settings: Settings) -> Client:
    """Create a server-only client for verified billing writes."""
    if not settings.supabase_enabled:
        raise RuntimeError("Supabase integration is disabled.")
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SECRET_KEY are required for billing."
        )
    return create_client(settings.supabase_url, settings.supabase_secret_key)


class SupabaseStore:
    """User-scoped access to Cross Speak AI's Supabase tables."""

    def __init__(self, client: Client) -> None:
        self.client = client

    def sign_up(self, email: str, password: str, user_mode: str = "corporate") -> Any:
        return self.client.auth.sign_up(
            {"email": email, "password": password, "options": {"data": {"user_mode": user_mode}}}
        )

    def sign_in(self, email: str, password: str) -> Any:
        return self.client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )

    def sign_out(self) -> None:
        self.client.auth.sign_out({"scope": "local"})

    # ── Profile helpers ────────────────────────────────────────────────────────

    def get_role(self, user_id: str) -> str:
        try:
            response = (
                self.client.table("profiles")
                .select("role")
                .eq("id", user_id)
                .single()
                .execute()
            )
            return str(response.data.get("role", "user"))
        except Exception:
            return "user"

    def get_plan(self, user_id: str) -> str:
        """Return 'free' or 'paid'."""
        try:
            response = (
                self.client.table("profiles")
                .select("plan,plan_expires_at")
                .eq("id", user_id)
                .single()
                .execute()
            )
            plan = str(response.data.get("plan", "free"))
            expires_at = response.data.get("plan_expires_at")
            if plan == "paid" and expires_at:
                expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                if expiry <= datetime.now(timezone.utc):
                    return "free"
            return plan
        except Exception:
            return "free"

    def get_user_mode(self, user_id: str, user_obj: Any = None) -> str:
        if user_obj and hasattr(user_obj, "user_metadata") and isinstance(user_obj.user_metadata, dict):
            if "user_mode" in user_obj.user_metadata:
                return str(user_obj.user_metadata["user_mode"])
        try:
            response = (
                self.client.table("profiles")
                .select("user_mode")
                .eq("id", user_id)
                .single()
                .execute()
            )
            return str(response.data.get("user_mode", "corporate"))
        except Exception:
            return "corporate"

    def ensure_user_mode_persisted(self, user_id: str, user_mode: str) -> None:
        """Write user_mode to profiles if not already set correctly."""
        try:
            self.client.table("profiles").upsert(
                {"id": user_id, "user_mode": user_mode},
                on_conflict="id",
            ).execute()
        except Exception:
            pass

    # ── Quota / Usage ─────────────────────────────────────────────────────────

    def get_usage(self, user_id: str) -> int:
        """Count all translations used by this account."""
        try:
            response = self.client.rpc(
                "get_translation_usage", {"p_user_id": user_id}
            ).execute()
            return int(response.data or 0)
        except Exception:
            # Fallback: count directly if the latest RPC is not yet applied.
            try:
                response = (
                    self.client.table("translation_history")
                    .select("id", count="exact")
                    .eq("user_id", user_id)
                    .execute()
                )
                return response.count or 0
            except Exception:
                return 0

    def check_quota(self, user_id: str, plan: str) -> tuple[int, int, bool]:
        """Return (usage_count, limit, is_allowed).
        Paid users always allowed. Free users allowed below the free-plan limit.
        """
        if plan == "paid":
            usage = self.get_usage(user_id)
            return usage, -1, True  # -1 = unlimited
        usage = self.get_usage(user_id)
        return usage, FREE_TRANSLATION_LIMIT, usage < FREE_TRANSLATION_LIMIT

    # ── Billing ───────────────────────────────────────────────────────────────

    def create_billing_order(
        self,
        *,
        user_id: str,
        provider_order_id: str,
        amount: int,
        currency: str,
        plan_days: int,
    ) -> dict[str, Any]:
        response = self.client.table("billing_orders").insert(
            {
                "user_id": user_id,
                "provider_order_id": provider_order_id,
                "amount": amount,
                "currency": currency,
                "plan_days": plan_days,
            }
        ).execute()
        return response.data[0]

    def get_billing_order(
        self, provider_order_id: str, user_id: str | None = None
    ) -> dict[str, Any] | None:
        query = (
            self.client.table("billing_orders")
            .select("*")
            .eq("provider_order_id", provider_order_id)
        )
        if user_id:
            query = query.eq("user_id", user_id)
        response = query.limit(1).execute()
        return response.data[0] if response.data else None

    def activate_paid_plan(
        self,
        *,
        provider_order_id: str,
        provider_payment_id: str,
        provider_event_id: str | None = None,
    ) -> dict[str, Any]:
        response = self.client.rpc(
            "activate_paid_plan",
            {
                "p_provider_order_id": provider_order_id,
                "p_provider_payment_id": provider_payment_id,
                "p_provider_event_id": provider_event_id,
            },
        ).execute()
        if not response.data:
            raise RuntimeError("Paid-plan activation returned no result.")
        return response.data[0] if isinstance(response.data, list) else response.data

    # ── Conversations ─────────────────────────────────────────────────────────

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

    def get_conversations(self, user_id: str) -> list[dict[str, Any]]:
        """Return all conversations for a user with metadata, newest first."""
        try:
            response = self.client.rpc(
                "get_conversations_with_preview", {"p_user_id": user_id}
            ).execute()
            return response.data or []
        except Exception:
            # Fallback without preview
            response = (
                self.client.table("conversations")
                .select("id,title,created_at,updated_at")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .execute()
            )
            return response.data or []

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

    # ── Translation History ───────────────────────────────────────────────────

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

    def get_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return flat history ordered newest-first."""
        response = (
            self.client.table("translation_history")
            .select(
                "id,conversation_id,input_text,output_text,detected_style,"
                "translation_direction,terms_used,created_at"
            )
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def get_history_by_conversation(
        self, conversation_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Return history for a specific conversation, chronological order."""
        response = (
            self.client.table("translation_history")
            .select(
                "id,conversation_id,input_text,output_text,detected_style,"
                "translation_direction,terms_used,created_at"
            )
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return response.data or []

    # ── Slang Suggestions ─────────────────────────────────────────────────────

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
