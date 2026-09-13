"""Cross Speak AI - Corporate English and Gen Z translator."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from langchain_core.documents import Document

_ROOT = Path(__file__).parent.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
load_dotenv(dotenv_path=_ROOT / ".env", override=False)

from core.api_manager import APIManager
from core.config import Settings, get_settings
from core.supabase_client import SupabaseStore, create_user_client
from rag.knowledge_loader import load_knowledge_base
from rag.pipeline import RAGPipeline, TranslationResult
from rag.prompt_builder import PromptBuilder
from rag.retriever import Retriever
from utils.language_detector import LanguageDetector
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="Cross Speak AI",
    page_icon="🔀",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner="Loading semantic search index...")
def _load_retriever(
    embedding_model: str,
    persist_path: str,
    max_docs: int,
    kb_path: str,
) -> Retriever:
    try:
        return Retriever.load(
            embedding_model=embedding_model,
            persist_path=persist_path,
            max_docs=max_docs,
        )
    except Exception:
        documents = load_knowledge_base(kb_path)
        return Retriever.build(
            documents=documents,
            embedding_model=embedding_model,
            persist_path=persist_path,
            max_docs=max_docs,
        )


_SESSION_DEFAULTS: dict[str, Any] = {
    "history": [],
    "custom_api_key": "",
    "input_text": "",
    "supabase_store": None,
    "supabase_store_key": None,
    "auth_user": None,
    "user_role": "user",
    "conversation_id": None,
}
for _key, _default in _SESSION_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default


def main() -> None:
    settings = get_settings()
    retriever = _load_retriever(
        embedding_model=settings.embedding_model,
        persist_path=settings.vectorstore_path,
        max_docs=settings.max_retrieved_docs,
        kb_path=settings.knowledge_base_path,
    )
    store, supabase_error = _get_store(settings)

    with st.sidebar:
        st.title("🔀 Cross Speak AI")
        st.caption("RAG-Powered Dialect Translator")
        if settings.supabase_enabled:
            _render_account(store, supabase_error)
        st.divider()

        st.subheader("⚙️ Settings")
        mode_options = {
            "🤖 Auto-Detect Style": "auto",
            "🏢 Corporate → Gen Z Slang": "corporate_to_genz",
            "✌️ Gen Z Slang → Corporate": "genz_to_corporate",
        }
        selected_mode_label = st.radio(
            "Translation Mode", options=list(mode_options), index=0
        )
        translation_mode = mode_options[selected_mode_label]

        st.divider()
        st.subheader("🔑 API Key Setup")
        if settings.gemini_api_keys:
            st.success(
                f"✅ {len(settings.gemini_api_keys)} key(s) loaded from "
                "Secrets/Environment"
            )
        else:
            st.info("ℹ️ No default key found in Secrets or .env")
        user_key = st.text_input(
            "Gemini API Key (Public / Custom)",
            type="password",
            value=st.session_state.custom_api_key,
            help="Enter your Gemini API key here to use the public app",
            key="user_key_input",
        )
        if user_key != st.session_state.custom_api_key:
            st.session_state.custom_api_key = user_key
            st.rerun()

        st.divider()
        st.subheader("📊 Session")
        st.metric("Translations Done", len(st.session_state.history))
        if st.button("Clear Session History", use_container_width=True):
            st.session_state.history = []
            st.rerun()
        if st.session_state.auth_user is not None and store is not None:
            if st.button("New Conversation", use_container_width=True):
                try:
                    st.session_state.conversation_id = store.create_conversation(
                        str(st.session_state.auth_user.id)
                    )
                    st.session_state.history = []
                    st.rerun()
                except Exception as exc:
                    st.error(_friendly_error(exc))
        st.caption("Ready for Streamlit Cloud Deployment")

    active_keys: list[str] = []
    if st.session_state.custom_api_key.strip():
        active_keys.append(st.session_state.custom_api_key.strip())
    for key in settings.gemini_api_keys:
        if key not in active_keys:
            active_keys.append(key)

    pipeline: Optional[RAGPipeline] = None
    if active_keys:
        active_settings = Settings(
            gemini_api_keys=active_keys,
            embedding_model=settings.embedding_model,
            gemini_model=settings.gemini_model,
            knowledge_base_path=settings.knowledge_base_path,
            vectorstore_path=settings.vectorstore_path,
            max_retrieved_docs=settings.max_retrieved_docs,
            retriever_score_threshold=settings.retriever_score_threshold,
        )
        pipeline = RAGPipeline(
            detector=LanguageDetector(),
            retriever=retriever,
            prompt_builder=PromptBuilder(
                max_context_docs=settings.max_retrieved_docs
            ),
            api_manager=APIManager(settings=active_settings),
            extra_retriever=_remote_retriever(settings, store, retriever),
        )

    st.title("🔀 Corporate ↔ Gen Z AI Translator")
    st.markdown(
        "Bridge the communication gap between executive business speak and "
        "Gen Z slang using Retrieval-Augmented Generation (RAG)."
    )
    st.divider()

    labels = ["✨ Translate", "📜 History", "📚 Knowledge Base"]
    if settings.supabase_enabled:
        labels.append("💡 Suggest Slang")
        if (
            st.session_state.auth_user is not None
            and st.session_state.user_role == "admin"
        ):
            labels.append("🛡️ Admin Review")
    tabs = st.tabs(labels)

    with tabs[0]:
        _render_translate(pipeline, translation_mode, settings, store)
    with tabs[1]:
        _render_history(store)
    with tabs[2]:
        _render_knowledge_base(settings, store)
    if settings.supabase_enabled:
        with tabs[3]:
            _render_suggestion_form(store)
    if len(tabs) == 5:
        with tabs[4]:
            _render_admin_review(store, retriever)


def _get_store(settings: Settings) -> tuple[Optional[SupabaseStore], Optional[str]]:
    if not settings.supabase_enabled:
        return None, None
    store_key = (settings.supabase_url, settings.supabase_publishable_key)
    if st.session_state.supabase_store_key != store_key:
        try:
            st.session_state.supabase_store = SupabaseStore(
                create_user_client(settings)
            )
            st.session_state.supabase_store_key = store_key
        except Exception as exc:
            logger.error("Supabase setup failed: %s", exc)
            return None, _friendly_error(exc)
    return st.session_state.supabase_store, None


def _render_account(
    store: Optional[SupabaseStore], supabase_error: Optional[str]
) -> None:
    st.subheader("👤 Account")
    if supabase_error or store is None:
        st.warning(supabase_error or "Account service is unavailable.")
        return
    user = st.session_state.auth_user
    if user is not None:
        st.success(str(user.email or "Signed in"))
        st.caption(f"Role: {st.session_state.user_role.title()}")
        if st.button("Sign Out", use_container_width=True):
            try:
                store.sign_out()
            finally:
                _clear_auth_state()
                st.rerun()
        return

    auth_mode = st.radio(
        "Account action",
        ["Sign in", "Register"],
        horizontal=True,
        label_visibility="collapsed",
    )
    with st.form("account_form", clear_on_submit=False):
        email = st.text_input("Email").strip().lower()
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button(
            auth_mode, use_container_width=True, type="primary"
        )
    if submitted:
        if not email or "@" not in email or len(password) < 6:
            st.error("Enter a valid email and a password of at least 6 characters.")
            return
        try:
            response = (
                store.sign_in(email, password)
                if auth_mode == "Sign in"
                else store.sign_up(email, password)
            )
            if response.session is None:
                st.success("Registration received. Check your email to confirm it.")
            else:
                _complete_sign_in(store, response.user)
                st.rerun()
        except Exception as exc:
            st.error(_friendly_error(exc))


def _complete_sign_in(store: SupabaseStore, user: Any) -> None:
    st.session_state.auth_user = user
    user_id = str(user.id)
    st.session_state.user_role = store.get_role(user_id)
    st.session_state.conversation_id = store.get_or_create_conversation(user_id)


def _clear_auth_state() -> None:
    st.session_state.auth_user = None
    st.session_state.user_role = "user"
    st.session_state.conversation_id = None
    st.session_state.history = []


def _remote_retriever(
    settings: Settings,
    store: Optional[SupabaseStore],
    retriever: Retriever,
) -> Any:
    if not settings.dynamic_kb_enabled or store is None:
        return None

    def retrieve(query: str) -> list[Document]:
        try:
            embedding = retriever.embed_text(query)
            return [
                _approved_term_document(record)
                for record in store.search_approved_terms(embedding)
            ]
        except Exception as exc:
            logger.warning("Remote knowledge retrieval failed: %s", exc)
            return []

    return retrieve


def _render_translate(
    pipeline: Optional[RAGPipeline],
    translation_mode: str,
    settings: Settings,
    store: Optional[SupabaseStore],
) -> None:
    if pipeline is None:
        st.warning(
            "🔑 **API Key Required**: Enter a Gemini API Key in the sidebar "
            "or configure one in Streamlit Secrets."
        )
    col_in, col_out = st.columns(2)
    with col_in:
        st.subheader("Input Text")
        st.caption("Quick sample presets:")
        ex_col1, ex_col2, ex_col3 = st.columns(3)
        if ex_col1.button("🏢 Corporate", use_container_width=True):
            st.session_state.input_text = (
                "Let's leverage our core competencies to move the needle on "
                "this deliverable."
            )
            st.rerun()
        if ex_col2.button("✌️ Gen Z", use_container_width=True):
            st.session_state.input_text = (
                "No cap that proposal slapped fr, she ate and left no crumbs."
            )
            st.rerun()
        if ex_col3.button("🔀 Mixed", use_container_width=True):
            st.session_state.input_text = (
                "We need to circle back on this lowkey sus action item by EOD."
            )
            st.rerun()
        sample_text = st.text_area(
            "Text to translate",
            value=st.session_state.input_text,
            placeholder="Enter Corporate English or Gen Z slang...",
            height=180,
            key="user_text_area",
            label_visibility="collapsed",
        )
        st.session_state.input_text = sample_text
        translate = st.button(
            "🚀 Translate Now",
            type="primary",
            disabled=(pipeline is None or not sample_text.strip()),
            use_container_width=True,
        )

    with col_out:
        st.subheader("Translation Output")
        if translate and pipeline is not None:
            context: list[dict[str, str]] = []
            user = st.session_state.auth_user
            if user is not None and store is not None:
                try:
                    if st.session_state.conversation_id is None:
                        st.session_state.conversation_id = (
                            store.get_or_create_conversation(str(user.id))
                        )
                    context = store.get_conversation_context(
                        st.session_state.conversation_id,
                        settings.conversation_memory_turns,
                    )
                except Exception as exc:
                    logger.warning("Conversation memory unavailable: %s", exc)
            with st.spinner("Processing RAG retrieval & translation..."):
                result = pipeline.translate(
                    user_input=sample_text.strip(),
                    translation_mode=translation_mode,
                    score_threshold=settings.retriever_score_threshold,
                    conversation_context=context,
                )
            if result.error:
                st.error(f"Translation Error: {result.error}")
            else:
                st.session_state.history.append(result)
                _display_result(result)
                if user is not None and store is not None:
                    try:
                        store.save_translation(
                            str(user.id),
                            st.session_state.conversation_id,
                            sample_text.strip(),
                            result,
                        )
                        st.caption("Saved to your account history.")
                    except Exception as exc:
                        st.warning(
                            "Translation completed, but account history could "
                            f"not be saved: {_friendly_error(exc)}"
                        )
        elif st.session_state.history:
            _display_result(st.session_state.history[-1])
        else:
            st.info("Enter text on the left and click **Translate Now**.")


def _render_history(store: Optional[SupabaseStore]) -> None:
    st.subheader("Translation History")
    user = st.session_state.auth_user
    if user is not None and store is not None:
        try:
            rows = store.get_history()
            if not rows:
                st.info("Your account has no saved translations yet.")
                return
            for index, row in enumerate(rows, 1):
                with st.expander(
                    f"#{index}: {row['translation_direction']} "
                    f"({row['detected_style']})",
                    expanded=(index == 1),
                ):
                    st.caption(row.get("created_at", ""))
                    st.markdown(f"**Input:** {row['input_text']}")
                    st.markdown(f"**Result:** {row['output_text']}")
            return
        except Exception as exc:
            st.warning(
                "Saved history is temporarily unavailable; showing this "
                f"session instead. {_friendly_error(exc)}"
            )
    if not st.session_state.history:
        st.info(
            "Sign in to keep history across sessions."
            if store is not None
            else "No translations performed in this session yet."
        )
        return
    for index, result in enumerate(reversed(st.session_state.history), 1):
        with st.expander(
            f"#{index}: {result.translation_direction} ({result.detected_style})",
            expanded=(index == 1),
        ):
            st.markdown(f"**Result:** {result.translation}")


def _render_knowledge_base(
    settings: Settings, store: Optional[SupabaseStore]
) -> None:
    st.subheader("Knowledge Base Terminology")
    try:
        dataframe = pd.read_csv(settings.knowledge_base_path)
        if settings.dynamic_kb_enabled and store is not None:
            try:
                approved = pd.DataFrame(store.get_approved_terms())
                if not approved.empty:
                    approved = approved.rename(columns={"example": "examples"})
                    dataframe = pd.concat([dataframe, approved], ignore_index=True)
            except Exception as exc:
                logger.warning("Approved-term listing failed: %s", exc)
        col_search, col_cat = st.columns([3, 1])
        with col_search:
            query = st.text_input(
                "Search terms", placeholder="Search term, meaning, or translation..."
            )
        with col_cat:
            category = st.selectbox(
                "Filter Category", ["All", "Corporate", "Gen Z"]
            )
        if category != "All":
            dataframe = dataframe[dataframe["category"] == category]
        if query.strip():
            mask = dataframe.apply(
                lambda row: query.lower()
                in " ".join(str(value) for value in row.values).lower(),
                axis=1,
            )
            dataframe = dataframe[mask]
        st.dataframe(
            dataframe[
                ["term", "category", "meaning", "translation", "examples"]
            ],
            use_container_width=True,
            hide_index=True,
        )
    except Exception as exc:
        st.error(f"Error loading knowledge base: {_friendly_error(exc)}")


def _render_suggestion_form(store: Optional[SupabaseStore]) -> None:
    st.subheader("Recommend New Slang")
    user = st.session_state.auth_user
    if user is None or store is None:
        st.info("Sign in to submit and track slang recommendations.")
        return
    with st.form("suggestion_form", clear_on_submit=True):
        term = st.text_input("Term or phrase", max_chars=100)
        category = st.selectbox("Category", ["Gen Z", "Corporate"])
        meaning = st.text_area("Meaning", max_chars=1000)
        translation = st.text_area("Opposite-style translation", max_chars=1000)
        example = st.text_area("Example", max_chars=2000)
        context = st.text_area("Context", max_chars=2000)
        submitted = st.form_submit_button(
            "Submit for Review", type="primary", use_container_width=True
        )
    if submitted:
        if not all(value.strip() for value in (term, meaning, translation)):
            st.error("Term, meaning, and translation are required.")
        else:
            try:
                store.submit_suggestion(
                    str(user.id),
                    term.strip(),
                    category,
                    meaning.strip(),
                    translation.strip(),
                    example.strip(),
                    context.strip(),
                )
                st.success("Suggestion submitted for admin review.")
            except Exception as exc:
                st.error(_friendly_error(exc))
    try:
        rows = [
            row
            for row in store.get_suggestions()
            if row.get("user_id") == str(user.id)
        ]
        if rows:
            st.markdown("#### Your submissions")
            st.dataframe(
                pd.DataFrame(rows)[["term", "category", "status", "created_at"]],
                use_container_width=True,
                hide_index=True,
            )
    except Exception as exc:
        logger.warning("Suggestion history unavailable: %s", exc)


def _render_admin_review(
    store: Optional[SupabaseStore], retriever: Retriever
) -> None:
    st.subheader("Admin Review")
    if store is None or st.session_state.user_role != "admin":
        st.error("Admin access required.")
        return
    try:
        suggestions = store.get_suggestions(pending_only=True)
    except Exception as exc:
        st.error(_friendly_error(exc))
        return
    if not suggestions:
        st.info("No pending suggestions.")
        return
    for suggestion in suggestions:
        item_id = suggestion["id"]
        with st.expander(str(suggestion["term"]), expanded=False):
            term = st.text_input(
                "Term", value=suggestion["term"], key=f"term_{item_id}"
            )
            category = st.selectbox(
                "Category",
                ["Gen Z", "Corporate"],
                index=0 if suggestion["category"] == "Gen Z" else 1,
                key=f"category_{item_id}",
            )
            meaning = st.text_area(
                "Meaning", value=suggestion["meaning"], key=f"meaning_{item_id}"
            )
            translation = st.text_area(
                "Translation",
                value=suggestion["translation"],
                key=f"translation_{item_id}",
            )
            example = st.text_area(
                "Example",
                value=suggestion.get("example", ""),
                key=f"example_{item_id}",
            )
            context = st.text_area(
                "Context",
                value=suggestion.get("context", ""),
                key=f"context_{item_id}",
            )
            reason = st.text_input(
                "Rejection reason", key=f"reason_{item_id}"
            )
            approve_col, reject_col = st.columns(2)
            if approve_col.button(
                "Approve", type="primary", key=f"approve_{item_id}"
            ):
                edited = {
                    **suggestion,
                    "term": term.strip(),
                    "category": category,
                    "meaning": meaning.strip(),
                    "translation": translation.strip(),
                    "example": example.strip(),
                    "context": context.strip(),
                }
                if not all(
                    edited[field] for field in ("term", "meaning", "translation")
                ):
                    st.error("Term, meaning, and translation are required.")
                else:
                    try:
                        document = _approved_term_document(edited)
                        store.approve_suggestion(
                            edited,
                            retriever.embed_text(document.page_content),
                        )
                        st.success("Suggestion approved and added to RAG.")
                        st.rerun()
                    except Exception as exc:
                        st.error(_friendly_error(exc))
            if reject_col.button("Reject", key=f"reject_{item_id}"):
                try:
                    store.reject_suggestion(item_id, reason.strip())
                    st.success("Suggestion rejected.")
                    st.rerun()
                except Exception as exc:
                    st.error(_friendly_error(exc))


def _approved_term_document(record: dict[str, Any]) -> Document:
    metadata = {
        "term": str(record.get("term", "")).strip(),
        "category": str(record.get("category", "")).strip(),
        "meaning": str(record.get("meaning", "")).strip(),
        "translation": str(record.get("translation", "")).strip(),
        "examples": str(record.get("example", "")).strip(),
        "notes": str(record.get("context", "")).strip(),
        "source": "approved_suggestion",
    }
    parts = [
        f"Term: {metadata['term']}",
        f"Category: {metadata['category']}",
        f"Meaning: {metadata['meaning']}",
        f"Translation: {metadata['translation']}",
    ]
    if metadata["examples"]:
        parts.append(f"Example: {metadata['examples']}")
    if metadata["notes"]:
        parts.append(f"Notes: {metadata['notes']}")
    return Document(page_content="\n".join(parts), metadata=metadata)


def _display_result(result: TranslationResult) -> None:
    st.success(f"**{result.translation_direction}** ({result.detected_style})")
    st.markdown(f"### {result.translation}")
    if result.terms_used:
        with st.expander("📖 Glossary & Grounded Terms", expanded=True):
            columns = st.columns(
                len(result.terms_used) if len(result.terms_used) <= 3 else 3
            )
            for index, term in enumerate(result.terms_used):
                with columns[index % len(columns)]:
                    st.markdown(
                        f"**{term.get('original')}**  \n"
                        f"↳ *{term.get('translated')}*"
                    )
    if result.retrieved_docs:
        with st.expander(
            f"🔍 RAG Retrieved Context ({len(result.retrieved_docs)} items)",
            expanded=False,
        ):
            for document in result.retrieved_docs:
                st.markdown(
                    f"- **{document.metadata.get('term', 'Term')}** "
                    f"({document.metadata.get('category')}): "
                    f"{document.metadata.get('meaning')}"
                )


def _friendly_error(exc: Exception) -> str:
    message = str(exc).strip()
    return message[:300] if message else type(exc).__name__


if __name__ == "__main__":
    main()
