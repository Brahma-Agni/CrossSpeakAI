"""Cross Speak AI - FastAPI REST Backend Server."""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.documents import Document
from pydantic import BaseModel, Field

_ROOT = Path(__file__).parent.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
load_dotenv(dotenv_path=_ROOT / ".env", override=False)

from core.api_manager import APIManager
from core.billing import (
    BillingError,
    RazorpayClient,
    validate_captured_payment,
    verify_payment_signature,
    verify_webhook_signature,
)
from core.content_guard import contains_abusive_language
from core.config import Settings, get_settings
from core.supabase_client import (
    FREE_TRANSLATION_LIMIT,
    SupabaseStore,
    create_admin_client,
    create_user_client,
)
from rag.knowledge_loader import load_knowledge_base
from rag.pipeline import RAGPipeline, TranslationResult
from rag.prompt_builder import PromptBuilder
from rag.retriever import Retriever
from utils.language_detector import LanguageDetector
from utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Cross Speak AI API",
    description="REST backend for Corporate English and Gen Z translator",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_settings: Settings = get_settings()
_retriever_instance: Optional[Retriever] = None


# ── Local In-Memory Fallback Authentication & Persistence Store ─────────────

class LocalUser:
    def __init__(self, user_id: str, email: str, user_mode: str = "corporate", role: str = "user", plan: str = "free"):
        self.id = user_id
        self.email = email
        self.user_metadata = {"user_mode": user_mode}
        self.role = role
        self.plan = plan


class LocalSession:
    def __init__(self, access_token: str):
        self.access_token = access_token


class LocalAuthResponse:
    def __init__(self, user: LocalUser, session: Optional[LocalSession]):
        self.user = user
        self.session = session


class LocalAuthStore:
    """In-memory authentication and translation persistence store for local development."""

    def __init__(self):
        self.users: dict[str, LocalUser] = {}
        self.passwords: dict[str, str] = {}
        self.tokens: dict[str, LocalUser] = {}
        self.conversations: dict[str, list[dict[str, Any]]] = {}
        self.user_conversations: dict[str, str] = {}
        self.history: list[dict[str, Any]] = []
        self.suggestions: list[dict[str, Any]] = []
        self.approved_terms: list[dict[str, Any]] = []

    def sign_up(self, email: str, password: str, user_mode: str = "corporate") -> LocalAuthResponse:
        email_clean = email.strip().lower()
        for u in self.users.values():
            if u.email == email_clean:
                raise Exception("User already exists with this email")
        user_id = str(uuid.uuid4())
        role = "admin" if email_clean == "admin@csai.com" else "user"
        user = LocalUser(user_id=user_id, email=email_clean, user_mode=user_mode, role=role)
        self.users[user_id] = user
        self.passwords[email_clean] = password
        token = f"local_token_{uuid.uuid4()}"
        self.tokens[token] = user
        return LocalAuthResponse(user=user, session=LocalSession(access_token=token))

    def sign_in(self, email: str, password: str) -> LocalAuthResponse:
        email_clean = email.strip().lower()
        user_id = None
        for uid, u in self.users.items():
            if u.email == email_clean:
                user_id = uid
                break
        if not user_id or self.passwords.get(email_clean) != password:
            raise Exception("Invalid email or password")
        user = self.users[user_id]

        token = f"local_token_{uuid.uuid4()}"
        self.tokens[token] = user
        return LocalAuthResponse(user=user, session=LocalSession(access_token=token))

    def get_user_by_token(self, token: str) -> LocalUser:
        if token in self.tokens:
            return self.tokens[token]
        raise ValueError("Invalid or expired session")

    def get_role(self, user_id: str) -> str:
        if user_id in self.users:
            return self.users[user_id].role
        return "user"

    def get_user_mode(self, user_id: str, user_obj: Any = None) -> str:
        if user_id in self.users:
            return self.users[user_id].user_metadata.get("user_mode", "corporate")
        return "corporate"

    def get_plan(self, user_id: str) -> str:
        return self.users.get(user_id, LocalUser(user_id, "")).plan

    def get_usage(self, user_id: str) -> int:
        return sum(1 for item in self.history if item["user_id"] == user_id)

    def check_quota(self, user_id: str, plan: str) -> tuple[int, int, bool]:
        usage = self.get_usage(user_id)
        return (usage, -1, True) if plan == "paid" else (usage, FREE_TRANSLATION_LIMIT, usage < FREE_TRANSLATION_LIMIT)

    def get_or_create_conversation(self, user_id: str) -> str:
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = str(uuid.uuid4())
        return self.user_conversations[user_id]

    def create_conversation(self, user_id: str) -> str:
        conv_id = str(uuid.uuid4())
        self.user_conversations[user_id] = conv_id
        return conv_id

    def get_conversation_context(self, conversation_id: str, limit: int) -> list[dict[str, str]]:
        history = self.conversations.get(conversation_id, [])
        return history[-limit:]

    def save_translation(self, user_id: str, conversation_id: str, input_text: str, result: Any) -> None:
        rec = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "input_text": input_text,
            "output_text": result.translation,
            "detected_style": result.detected_style,
            "translation_direction": result.translation_direction,
            "terms_used": result.terms_used,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.history.insert(0, rec)
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        self.conversations[conversation_id].append({"input_text": input_text, "output_text": result.translation})

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.history[:limit]

    def submit_suggestion(self, user_id: str, term: str, category: str, meaning: str, translation: str, example: str, context: str) -> None:
        self.suggestions.append({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "term": term,
            "category": category,
            "meaning": meaning,
            "translation": translation,
            "example": example,
            "context": context,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    def get_suggestions(self, pending_only: bool = False) -> list[dict[str, Any]]:
        if pending_only:
            return [s for s in self.suggestions if s.get("status") == "pending"]
        return self.suggestions

    def approve_suggestion(self, suggestion: dict[str, Any], embedding: list[float]) -> None:
        for s in self.suggestions:
            if s["id"] == suggestion["id"]:
                s["status"] = "approved"
                s.update(suggestion)
        self.approved_terms.append(suggestion)

    def reject_suggestion(self, suggestion_id: str, reason: str) -> None:
        for s in self.suggestions:
            if s["id"] == suggestion_id:
                s["status"] = "rejected"
                s["rejection_reason"] = reason

    def get_approved_terms(self) -> list[dict[str, Any]]:
        return self.approved_terms

    def search_approved_terms(self, query_embedding: list[float]) -> list[dict[str, Any]]:
        return self.approved_terms


_local_store = LocalAuthStore()


def get_retriever() -> Retriever:
    global _retriever_instance
    if _retriever_instance is None:
        try:
            _retriever_instance = Retriever.load(
                embedding_model=_settings.embedding_model,
                persist_path=_settings.vectorstore_path,
                max_docs=_settings.max_retrieved_docs,
            )
        except Exception:
            documents = load_knowledge_base(_settings.knowledge_base_path)
            _retriever_instance = Retriever.build(
                documents=documents,
                embedding_model=_settings.embedding_model,
                persist_path=_settings.vectorstore_path,
                max_docs=_settings.max_retrieved_docs,
            )
    return _retriever_instance


def get_auth_store(access_token: Optional[str] = None) -> Any:
    if _settings.supabase_enabled:
        if not _settings.supabase_url or not _settings.supabase_publishable_key:
            raise HTTPException(
                status_code=503,
                detail="Supabase authentication is enabled but not fully configured.",
            )
        try:
            client = create_user_client(_settings)
            if access_token:
                client.postgrest.auth(access_token)
            return SupabaseStore(client)
        except Exception as exc:
            logger.error("Supabase client setup failed: %s", exc)
            raise HTTPException(status_code=503, detail="Authentication service unavailable.") from exc
    return _local_store


def get_billing_store() -> SupabaseStore:
    """Return the server-only store used after payment verification."""
    if not _settings.billing_ready:
        raise HTTPException(
            status_code=503,
            detail="Paid checkout is not configured yet.",
        )
    try:
        return SupabaseStore(create_admin_client(_settings))
    except Exception as exc:
        logger.error("Billing store setup failed: %s", exc)
        raise HTTPException(
            status_code=503, detail="Billing service is unavailable."
        ) from exc


def authenticated_user(
    authorization: Optional[str],
) -> tuple[Any, Any]:
    """Validate a bearer token and return its user-scoped store and user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    token = authorization.removeprefix("Bearer ").strip()
    store = get_auth_store(token)
    try:
        if isinstance(store, SupabaseStore):
            user = store.client.auth.get_user(token).user
        else:
            user = store.get_user_by_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=401, detail="Your session is invalid or expired."
        ) from exc
    if user is None:
        raise HTTPException(
            status_code=401, detail="Your session is invalid or expired."
        )
    return store, user


def razorpay_client() -> RazorpayClient:
    return RazorpayClient(
        key_id=_settings.razorpay_key_id,
        key_secret=_settings.razorpay_key_secret,
    )


def account_status(store: Any, user_id: str) -> dict[str, Any]:
    plan = store.get_plan(user_id)
    usage, limit, _ = store.check_quota(user_id, plan)
    return {"plan": plan, "usage_count": usage, "usage_limit": limit}


def approved_term_document(record: dict[str, Any]) -> Document:
    metadata = {
        "term": str(record.get("term", "")).strip(),
        "category": str(record.get("category", "")).strip(),
        "meaning": str(record.get("meaning", "")).strip(),
        "translation": str(record.get("translation", "")).strip(),
        "example": str(record.get("example", "")).strip(),
        "context": str(record.get("context", "")).strip(),
        "source": "approved_user_suggestion",
    }
    content_parts = [
        f"Term: {metadata['term']}",
        f"Category: {metadata['category']}",
        f"Meaning: {metadata['meaning']}",
        f"Translation: {metadata['translation']}",
    ]
    if metadata["example"]:
        content_parts.append(f"Example: {metadata['example']}")
    if metadata["context"]:
        content_parts.append(f"Context: {metadata['context']}")
    return Document(page_content="\n".join(content_parts), metadata=metadata)


def build_pipeline(
    custom_api_key: Optional[str] = None,
    store: Any = None,
) -> RAGPipeline:
    retriever = get_retriever()
    active_keys: list[str] = []
    if custom_api_key and custom_api_key.strip():
        active_keys.append(custom_api_key.strip())
    for key in _settings.gemini_api_keys:
        if key not in active_keys:
            active_keys.append(key)

    if not active_keys:
        raise HTTPException(
            status_code=400,
            detail="No Gemini API key is configured. Please enter a personal Gemini API key in the sidebar.",
        )

    active_settings = Settings(
        gemini_api_keys=active_keys,
        embedding_model=_settings.embedding_model,
        gemini_model=_settings.gemini_model,
        knowledge_base_path=_settings.knowledge_base_path,
        vectorstore_path=_settings.vectorstore_path,
        max_retrieved_docs=_settings.max_retrieved_docs,
        retriever_score_threshold=_settings.retriever_score_threshold,
    )

    extra_retriever = None
    if store is not None:

        def remote_retrieve(query: str) -> list[Document]:
            try:
                embedding = retriever.embed_text(query)
                return [
                    approved_term_document(rec)
                    for rec in store.search_approved_terms(embedding)
                ]
            except Exception as exc:
                logger.warning("Remote knowledge retrieval failed: %s", exc)
                return []

        extra_retriever = remote_retrieve

    return RAGPipeline(
        detector=LanguageDetector(),
        retriever=retriever,
        prompt_builder=PromptBuilder(max_context_docs=_settings.max_retrieved_docs),
        api_manager=APIManager(settings=active_settings),
        extra_retriever=extra_retriever,
    )


# ── Schemas ──────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    input_text: str = Field(..., min_length=1, max_length=10000)
    translation_mode: str = Field("auto")
    custom_api_key: Optional[str] = None
    conversation_id: Optional[str] = None


class AuthRequest(BaseModel):
    email: str
    password: str
    user_mode: Literal["corporate", "genz"] = "corporate"


class SuggestionRequest(BaseModel):
    term: str
    category: str
    meaning: str
    translation: str
    example: Optional[str] = ""
    context: Optional[str] = ""


class AdminApproveRequest(BaseModel):
    term: str
    category: str
    meaning: str
    translation: str
    example: Optional[str] = ""
    context: Optional[str] = ""


class AdminRejectRequest(BaseModel):
    reason: str = ""


class BillingVerifyRequest(BaseModel):
    razorpay_order_id: str = Field(..., min_length=1, max_length=100)
    razorpay_payment_id: str = Field(..., min_length=1, max_length=100)
    razorpay_signature: str = Field(..., min_length=1, max_length=256)


# ── API Routes ───────────────────────────────────────────────

@app.get("/api/config")
def get_config():
    return {
        "gemini_api_keys_count": len(_settings.gemini_api_keys),
        "supabase_enabled": _settings.supabase_enabled,
        "gemini_model": _settings.gemini_model,
        "embedding_model": _settings.embedding_model,
        "payments_enabled": _settings.billing_ready,
        "paid_plan_amount_subunits": _settings.paid_plan_amount_subunits,
        "paid_plan_currency": _settings.paid_plan_currency,
        "paid_plan_duration_days": _settings.paid_plan_duration_days,
        "translation_modes": [
            {"label": "Auto-detect style", "value": "auto"},
            {"label": "Corporate to Gen Z", "value": "corporate_to_genz"},
            {"label": "Gen Z to Corporate", "value": "genz_to_corporate"},
        ],
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/billing/order")
def create_billing_order(authorization: Optional[str] = Header(None)):
    """Create a provider order for the authenticated account."""
    _, user = authenticated_user(authorization)
    billing_store = get_billing_store()
    receipt = f"cs_{uuid.uuid4().hex[:24]}"
    try:
        order = razorpay_client().create_order(
            amount=_settings.paid_plan_amount_subunits,
            currency=_settings.paid_plan_currency,
            receipt=receipt,
        )
        order_id = str(order.get("id", ""))
        if (
            not order_id
            or int(order.get("amount", -1))
            != _settings.paid_plan_amount_subunits
            or str(order.get("currency", "")).upper()
            != _settings.paid_plan_currency
        ):
            raise BillingError("Payment provider returned an invalid order.")
        billing_store.create_billing_order(
            user_id=str(user.id),
            provider_order_id=order_id,
            amount=_settings.paid_plan_amount_subunits,
            currency=_settings.paid_plan_currency,
            plan_days=_settings.paid_plan_duration_days,
        )
        return {
            "key_id": _settings.razorpay_key_id,
            "order_id": order_id,
            "amount": _settings.paid_plan_amount_subunits,
            "currency": _settings.paid_plan_currency,
            "plan_days": _settings.paid_plan_duration_days,
            "name": "CrossSpeak AI",
            "description": (
                f"{_settings.paid_plan_duration_days}-day unlimited plan"
            ),
            "customer_email": str(user.email or ""),
        }
    except BillingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Billing order creation failed: %s", exc)
        raise HTTPException(
            status_code=503, detail="Could not start checkout. Please try again."
        ) from exc


@app.post("/api/billing/verify")
def verify_billing_payment(
    req: BillingVerifyRequest,
    authorization: Optional[str] = Header(None),
):
    """Verify Checkout's signature and provider status before activation."""
    _, user = authenticated_user(authorization)
    billing_store = get_billing_store()
    try:
        order = billing_store.get_billing_order(
            req.razorpay_order_id, user_id=str(user.id)
        )
        if not order:
            raise HTTPException(status_code=404, detail="Billing order not found.")
        stored_order_id = str(order["provider_order_id"])
        if not verify_payment_signature(
            stored_order_id,
            req.razorpay_payment_id,
            req.razorpay_signature,
            _settings.razorpay_key_secret,
        ):
            raise HTTPException(status_code=400, detail="Invalid payment signature.")

        payment = razorpay_client().fetch_payment(req.razorpay_payment_id)
        validate_captured_payment(
            payment,
            payment_id=req.razorpay_payment_id,
            order_id=stored_order_id,
            amount=int(order["amount"]),
            currency=str(order["currency"]),
        )
        activation = billing_store.activate_paid_plan(
            provider_order_id=stored_order_id,
            provider_payment_id=req.razorpay_payment_id,
        )
        return {
            "message": "Payment verified. Unlimited access is active.",
            "plan": activation["plan"],
            "plan_expires_at": activation["plan_expires_at"],
        }
    except HTTPException:
        raise
    except BillingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Payment verification failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Payment could not be verified. It will be retried automatically.",
        ) from exc


@app.post("/api/billing/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
    x_razorpay_event_id: Optional[str] = Header(None),
):
    """Activate paid access from a signed payment.captured webhook."""
    billing_store = get_billing_store()
    raw_body = await request.body()
    if not x_razorpay_signature or not verify_webhook_signature(
        raw_body,
        x_razorpay_signature,
        _settings.razorpay_webhook_secret,
    ):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")
    try:
        event = json.loads(raw_body)
        if event.get("event") != "payment.captured":
            return {"status": "ignored"}
        payment = event["payload"]["payment"]["entity"]
        order_id = str(payment.get("order_id", ""))
        order = billing_store.get_billing_order(order_id)
        if not order:
            return {"status": "ignored"}
        payment_id = str(payment.get("id", ""))
        validate_captured_payment(
            payment,
            payment_id=payment_id,
            order_id=order_id,
            amount=int(order["amount"]),
            currency=str(order["currency"]),
        )
        billing_store.activate_paid_plan(
            provider_order_id=order_id,
            provider_payment_id=payment_id,
            provider_event_id=x_razorpay_event_id,
        )
        return {"status": "processed"}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, BillingError) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload.") from exc
    except Exception as exc:
        logger.error("Billing webhook failed: %s", exc)
        raise HTTPException(status_code=503, detail="Webhook processing failed.") from exc


@app.post("/api/translate")
def translate(
    req: TranslateRequest,
    authorization: Optional[str] = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in to translate.")
    token = authorization.removeprefix("Bearer ").strip()
    store = get_auth_store(token)

    user = None
    if token:
        try:
            if isinstance(store, SupabaseStore):
                user_resp = store.client.auth.get_user(token)
                user = user_resp.user
            elif isinstance(store, LocalAuthStore):
                user = store.get_user_by_token(token)
        except Exception as exc:
            logger.warning("Token verification failed: %s", exc)

    if user is None:
        raise HTTPException(status_code=401, detail="Your session is invalid or expired.")

    clean_input = req.input_text.strip()
    if contains_abusive_language(clean_input):
        raise HTTPException(
            status_code=422,
            detail="Abusive language is not allowed. Please revise the text and try again.",
        )

    user_id = str(user.id)
    plan = store.get_plan(user_id)
    usage_count, usage_limit, allowed = store.check_quota(user_id, plan)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Free plan limit reached ({FREE_TRANSLATION_LIMIT} translations). Upgrade to Paid for unlimited access.",
        )

    pipeline = build_pipeline(custom_api_key=req.custom_api_key, store=store)

    context: list[dict[str, str]] = []
    conversation_id = req.conversation_id
    if user and store:
        try:
            if not conversation_id:
                conversation_id = store.get_or_create_conversation(user_id)
            context = store.get_conversation_context(
                conversation_id, _settings.conversation_memory_turns
            )
        except Exception as exc:
            logger.warning("Conversation context fetch failed: %s", exc)

    result: TranslationResult = pipeline.translate(
        user_input=clean_input,
        translation_mode=req.translation_mode,
        score_threshold=_settings.retriever_score_threshold,
        conversation_context=context,
    )

    if result.error:
        raise HTTPException(status_code=500, detail=result.error)

    if contains_abusive_language(result.translation) or contains_abusive_language(result.normal_english):
        logger.warning("Blocked an abusive model response for user %s", user_id)
        raise HTTPException(
            status_code=422,
            detail="The generated translation was blocked by the language safety policy.",
        )

    saved_to_history = False
    if user and store and conversation_id:
        try:
            store.save_translation(
                user_id,
                conversation_id,
                clean_input,
                result,
            )
            saved_to_history = True
        except Exception as exc:
            logger.error("Failed to save translation history: %s", exc)
            raise HTTPException(status_code=503, detail="Could not record usage. Please try again.")

    retrieved_docs_formatted = [
        {
            "page_content": doc.page_content,
            "metadata": doc.metadata,
        }
        for doc in result.retrieved_docs
    ]

    return {
        "translation": result.translation,
        "normal_english": result.normal_english,
        "terms_used": result.terms_used,
        "detected_style": result.detected_style,
        "translation_direction": result.translation_direction,
        "retrieved_docs": retrieved_docs_formatted,
        "conversation_id": conversation_id,
        "saved_to_history": saved_to_history,
        "plan": plan,
        "usage_count": usage_count + 1,
        "usage_limit": usage_limit,
    }


@app.post("/api/auth/sign-in")
def sign_in(req: AuthRequest):
    store = get_auth_store()
    try:
        res = store.sign_in(req.email, req.password)
        if not res.session:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        role = store.get_role(str(res.user.id))
        user_mode = store.get_user_mode(str(res.user.id), res.user)
        user_id = str(res.user.id)
        conv_id = store.get_or_create_conversation(user_id)
        return {
            "access_token": res.session.access_token,
            "user": {"id": res.user.id, "email": res.user.email, "user_mode": user_mode},
            "role": role,
            "user_mode": user_mode,
            "conversation_id": conv_id,
            **account_status(store, user_id),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/auth/sign-up")
def sign_up(req: AuthRequest):
    store = get_auth_store()
    try:
        mode = req.user_mode or "corporate"
        res = store.sign_up(req.email, req.password, user_mode=mode)
        if res.session:
            role = store.get_role(str(res.user.id))
            user_mode = store.get_user_mode(str(res.user.id), res.user)
            user_id = str(res.user.id)
            conv_id = store.get_or_create_conversation(user_id)
            return {
                "access_token": res.session.access_token,
                "user": {"id": res.user.id, "email": res.user.email, "user_mode": user_mode},
                "role": role,
                "user_mode": user_mode,
                "conversation_id": conv_id,
                **account_status(store, user_id),
                "confirmed": True,
            }
        return {"message": "Registration received. Check your email to confirm.", "confirmed": False}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/auth/me")
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    store = get_auth_store(token)
    try:
        if isinstance(store, SupabaseStore):
            user_resp = store.client.auth.get_user(token)
            user = user_resp.user
        else:
            user = store.get_user_by_token(token)
        role = store.get_role(str(user.id))
        user_mode = store.get_user_mode(str(user.id), user)
        user_id = str(user.id)
        conv_id = store.get_or_create_conversation(user_id)
        return {
            "user": {"id": user.id, "email": user.email, "user_mode": user_mode},
            "role": role,
            "user_mode": user_mode,
            "conversation_id": conv_id,
            **account_status(store, user_id),
        }
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@app.get("/api/history")
def get_history(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    store = get_auth_store(token)
    try:
        return store.get_history()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/conversations/new")
def new_conversation(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    store = get_auth_store(token)
    try:
        if isinstance(store, SupabaseStore):
            user_resp = store.client.auth.get_user(token)
            user_id = str(user_resp.user.id)
        else:
            user_id = str(store.get_user_by_token(token).id)
        conv_id = store.create_conversation(user_id)
        return {"conversation_id": conv_id}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/knowledge-base")
def get_knowledge_base(
    query: Optional[str] = Query(None),
    category: Optional[str] = Query("All"),
    authorization: Optional[str] = Header(None),
):
    try:
        df = pd.read_csv(_settings.knowledge_base_path)
        token = authorization.replace("Bearer ", "") if authorization else None
        store = get_auth_store(token)
        if store:
            try:
                approved = pd.DataFrame(store.get_approved_terms())
                if not approved.empty:
                    approved = approved.rename(columns={"example": "examples"})
                    df = pd.concat([df, approved], ignore_index=True)
            except Exception as exc:
                logger.warning("Approved terms list error: %s", exc)

        if category and category != "All":
            df = df[df["category"] == category]

        if query and query.strip():
            mask = df.apply(
                lambda row: query.lower()
                in " ".join(str(val) for val in row.values).lower(),
                axis=1,
            )
            df = df[mask]

        records = df[["term", "category", "meaning", "translation", "examples"]].fillna("").to_dict(orient="records")
        return {"terms": records, "count": len(records)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/suggestions")
def get_suggestions(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    store = get_auth_store(token)
    try:
        if isinstance(store, SupabaseStore):
            user_resp = store.client.auth.get_user(token)
            user_id = str(user_resp.user.id)
        else:
            user_id = str(store.get_user_by_token(token).id)
        all_sug = store.get_suggestions()
        user_sug = [s for s in all_sug if s.get("user_id") == user_id]
        return user_sug
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/suggestions")
def submit_suggestion(
    req: SuggestionRequest,
    authorization: Optional[str] = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    store = get_auth_store(token)
    try:
        if isinstance(store, SupabaseStore):
            user_resp = store.client.auth.get_user(token)
            user_id = str(user_resp.user.id)
        else:
            user_id = str(store.get_user_by_token(token).id)

        store.submit_suggestion(
            user_id=user_id,
            term=req.term.strip(),
            category=req.category,
            meaning=req.meaning.strip(),
            translation=req.translation.strip(),
            example=(req.example or "").strip(),
            context=(req.context or "").strip(),
        )
        return {"message": "Suggestion submitted successfully."}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/admin/suggestions")
def get_admin_suggestions(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    store = get_auth_store(token)
    try:
        if isinstance(store, SupabaseStore):
            user_resp = store.client.auth.get_user(token)
            user_id = str(user_resp.user.id)
        else:
            user_id = str(store.get_user_by_token(token).id)

        role = store.get_role(user_id)
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")
        return store.get_suggestions(pending_only=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/admin/suggestions/{suggestion_id}/approve")
def approve_suggestion(
    suggestion_id: str,
    req: AdminApproveRequest,
    authorization: Optional[str] = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    store = get_auth_store(token)
    try:
        if isinstance(store, SupabaseStore):
            user_resp = store.client.auth.get_user(token)
            user_id = str(user_resp.user.id)
        else:
            user_id = str(store.get_user_by_token(token).id)

        role = store.get_role(user_id)
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")

        retriever = get_retriever()
        suggestion_data = {
            "id": suggestion_id,
            "term": req.term.strip(),
            "category": req.category,
            "meaning": req.meaning.strip(),
            "translation": req.translation.strip(),
            "example": (req.example or "").strip(),
            "context": (req.context or "").strip(),
        }
        doc = approved_term_document(suggestion_data)
        embedding = retriever.embed_text(doc.page_content)
        store.approve_suggestion(suggestion_data, embedding)
        return {"message": "Suggestion approved and indexed into RAG."}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/admin/suggestions/{suggestion_id}/reject")
def reject_suggestion(
    suggestion_id: str,
    req: AdminRejectRequest,
    authorization: Optional[str] = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    store = get_auth_store(token)
    try:
        if isinstance(store, SupabaseStore):
            user_resp = store.client.auth.get_user(token)
            user_id = str(user_resp.user.id)
        else:
            user_id = str(store.get_user_by_token(token).id)

        role = store.get_role(user_id)
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")

        store.reject_suggestion(suggestion_id, req.reason.strip())
        return {"message": "Suggestion rejected."}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8008, reload=True)
