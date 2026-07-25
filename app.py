"""
app.py

Cross Speak AI — Corporate ↔ Gen Z AI Translator
Lightweight & Streamlit Cloud Ready Single-Page Application.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

# Ensure root directory is on sys.path
_ROOT = Path(__file__).parent.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Load .env if present
load_dotenv(dotenv_path=_ROOT / ".env", override=False)

from core.api_manager import APIManager
from core.config import Settings, get_settings
from rag.knowledge_loader import load_knowledge_base
from rag.pipeline import RAGPipeline, TranslationResult
from rag.prompt_builder import PromptBuilder
from rag.retriever import Retriever
from utils.language_detector import LanguageDetector, LanguageStyle
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cross Speak AI",
    page_icon="🔀",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Resource Caching ──────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading semantic search index...")
def _load_retriever(embedding_model: str, persist_path: str, max_docs: int, kb_path: str) -> Retriever:
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


# ── Session State ─────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "custom_api_key" not in st.session_state:
    st.session_state.custom_api_key = ""


# ── Main Application ──────────────────────────────────────────────────────────
def main() -> None:
    settings = get_settings()
    retriever = _load_retriever(
        embedding_model=settings.embedding_model,
        persist_path=settings.vectorstore_path,
        max_docs=settings.max_retrieved_docs,
        kb_path=settings.knowledge_base_path,
    )

    # ── Sidebar Controls ──
    with st.sidebar:
        st.title("🔀 Cross Speak AI")
        st.caption("RAG-Powered Dialect Translator")
        st.divider()

        st.subheader("⚙️ Settings")
        mode_options = {
            "🤖 Auto-Detect Style": "auto",
            "🏢 Corporate → Gen Z Slang": "corporate_to_genz",
            "✌️ Gen Z Slang → Corporate": "genz_to_corporate",
        }
        selected_mode_label = st.radio(
            "Translation Mode",
            options=list(mode_options.keys()),
            index=0,
        )
        translation_mode = mode_options[selected_mode_label]

        st.divider()
        st.subheader("🔑 API Key Setup")

        env_keys_count = len(settings.gemini_api_keys)
        if env_keys_count > 0:
            st.success(f"✅ {env_keys_count} key(s) loaded from Secrets/Environment")
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
        if st.button("Clear History", use_container_width=True):
            st.session_state.history = []
            st.rerun()

        st.caption("Ready for Streamlit Cloud Deployment")

    # Assemble active keys pool (custom user key first, followed by environment/secrets keys)
    active_keys: list[str] = []
    if st.session_state.custom_api_key.strip():
        active_keys.append(st.session_state.custom_api_key.strip())
    for k in settings.gemini_api_keys:
        if k not in active_keys:
            active_keys.append(k)

    # Instantiate pipeline dynamically with current active keys
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
        api_manager = APIManager(settings=active_settings)
        pipeline = RAGPipeline(
            detector=LanguageDetector(),
            retriever=retriever,
            prompt_builder=PromptBuilder(max_context_docs=settings.max_retrieved_docs),
            api_manager=api_manager,
        )
    else:
        pipeline = None

    # ── Header ──
    st.title("🔀 Corporate ↔ Gen Z AI Translator")
    st.markdown(
        "Bridge the communication gap between executive business speak and Gen Z slang using Retrieval-Augmented Generation (RAG)."
    )
    st.divider()

    # ── Tabs ──
    tab_translate, tab_history, tab_kb = st.tabs(
        ["✨ Translate", "📜 History", "📚 Knowledge Base"]
    )

    # Initialise text state
    if "input_text" not in st.session_state:
        st.session_state.input_text = ""

    # ── Tab 1: Translate ──
    with tab_translate:
        if pipeline is None:
            st.warning(
                "🔑 **API Key Required**: Please enter your Gemini API Key in the sidebar or configure `GEMINI_API_KEY_1` in `.env` / Streamlit Secrets."
            )

        col_in, col_out = st.columns(2)

        with col_in:
            st.subheader("Input Text")

            # Quick Example Buttons (placed above or below text area, handling state cleanly)
            st.caption("Quick sample presets:")
            ex_col1, ex_col2, ex_col3 = st.columns(3)
            if ex_col1.button("🏢 Corporate", use_container_width=True):
                st.session_state.input_text = (
                    "Let's leverage our core competencies to move the needle on this deliverable."
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
                placeholder="e.g., Let's leverage our bandwidth to circle back on deliverables.\nOR: No cap that presentation slapped, fr periodt.",
                height=180,
                key="user_text_area",
                label_visibility="collapsed",
            )
            st.session_state.input_text = sample_text

            btn_translate = st.button(
                "🚀 Translate Now",
                type="primary",
                disabled=(pipeline is None or not sample_text.strip()),
                use_container_width=True,
            )

        with col_out:
            st.subheader("Translation Output")

            if btn_translate and pipeline is not None and sample_text.strip():
                with st.spinner("Processing RAG retrieval & translation..."):
                    result: TranslationResult = pipeline.translate(
                        user_input=sample_text.strip(),
                        translation_mode=translation_mode,
                        score_threshold=settings.retriever_score_threshold,
                    )

                if result.error:
                    st.error(f"Translation Error: {result.error}")
                else:
                    st.session_state.history.append(result)
                    _display_result(result)

            elif st.session_state.history:
                # Show latest result
                _display_result(st.session_state.history[-1])
            else:
                st.info("Enter text on the left and click **Translate Now** to view the output.")

    # ── Tab 2: History ──
    with tab_history:
        st.subheader("Translation History")
        if not st.session_state.history:
            st.info("No translations performed in this session yet.")
        else:
            for idx, res in enumerate(reversed(st.session_state.history), 1):
                with st.expander(
                    f"#{len(st.session_state.history) - idx + 1}: {res.translation_direction} ({res.detected_style})",
                    expanded=(idx == 1),
                ):
                    st.markdown(f"**Result:** {res.translation}")
                    if res.terms_used:
                        st.caption("Terms Glossary:")
                        for item in res.terms_used:
                            st.write(
                                f"- **{item.get('original')}** → *{item.get('translated')}* (Confidence: {item.get('confidence', 'high')})"
                            )

    # ── Tab 3: Knowledge Base ──
    with tab_kb:
        st.subheader("Knowledge Base Terminology")
        import pandas as pd

        try:
            df = pd.read_csv(settings.knowledge_base_path)
            col_search, col_cat = st.columns([3, 1])
            with col_search:
                q = st.text_input("Search terms", placeholder="Search term, meaning, or translation...")
            with col_cat:
                cat = st.selectbox("Filter Category", ["All", "Corporate", "Gen Z"])

            filtered_df = df.copy()
            if cat != "All":
                filtered_df = filtered_df[filtered_df["category"] == cat]
            if q.strip():
                mask = filtered_df.apply(
                    lambda r: q.lower() in " ".join(str(v) for v in r.values).lower(),
                    axis=1,
                )
                filtered_df = filtered_df[mask]

            st.dataframe(
                filtered_df[["term", "category", "meaning", "translation", "examples"]],
                use_container_width=True,
                hide_index=True,
            )
        except Exception as e:
            st.error(f"Error loading knowledge base: {e}")


def _display_result(result: TranslationResult) -> None:
    """Helper to render translation result card cleanly."""
    st.success(f"**{result.translation_direction}** ({result.detected_style})")
    st.markdown(f"### {result.translation}")

    if result.terms_used:
        with st.expander("📖 Glossary & Grounded Terms", expanded=True):
            cols = st.columns(len(result.terms_used) if len(result.terms_used) <= 3 else 3)
            for i, t in enumerate(result.terms_used):
                col = cols[i % len(cols)]
                with col:
                    st.markdown(
                        f"**{t.get('original')}**  \n↳ *{t.get('translated')}*"
                    )

    if result.retrieved_docs:
        with st.expander(f"🔍 RAG Retrieved Context ({len(result.retrieved_docs)} items)", expanded=False):
            for doc in result.retrieved_docs:
                st.markdown(f"- **{doc.metadata.get('term', 'Term')}** ({doc.metadata.get('category')}): {doc.metadata.get('meaning')}")


if __name__ == "__main__":
    main()
