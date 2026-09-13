# Cross Speak AI 🔀

> **Translate between Corporate English and Gen Z Slang** using a production-grade RAG pipeline powered by Google Gemini — deployable on Streamlit Cloud in minutes.

[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?logo=langchain)](https://langchain.com)
[![FAISS](https://img.shields.io/badge/FAISS-CPU-blue)](https://faiss.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

| Feature | Detail |
|---|---|
| 🔀 **Bidirectional Translation** | Corporate → Gen Z and Gen Z → Corporate |
| 🧠 **RAG Pipeline** | FAISS + Sentence Transformers for grounded, accurate translations |
| 🔑 **API Failover** | Up to 5 Gemini API keys with automatic rotation on rate limits |
| 🕵️ **Auto Detection** | Heuristic language style classifier (Corporate / Gen Z / Mixed / General) |
| 📚 **Knowledge Base** | 50+ curated term pairs with meanings, aliases, examples, and notes |
| ⚡ **Streamlit Cloud Ready** | Zero-config deployment — secrets injected via Streamlit Secrets |
| 🎨 **SaaS-grade UI** | Dark-purple glassmorphism design with smooth animations |
| 🛡️ **Secure** | No secrets in source; full `.gitignore` and `.env.example` provided |

---

## 🏗️ Architecture

```
User Input
    │
    ▼
LanguageDetector          ← heuristic style classification
    │
    ▼
FAISS Retriever           ← sentence-transformer embeddings → top-k docs
    │
    ▼
PromptBuilder             ← Role + Objective + Context + Constraints + Format
    │
    ▼
APIManager                ← Gemini LLM with 5-key failover
    │
    ▼
TranslationResult         ← structured JSON → Streamlit UI
```

### Module Map

```
crossspeakai/
├── app.py                   # Streamlit entry point — UI + resource wiring
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── .streamlit/
│   └── config.toml          # Dark theme + security settings
├── core/
│   ├── config.py            # Settings dataclass (env vars + Streamlit Secrets)
│   └── api_manager.py       # Multi-key Gemini API manager with failover
├── rag/
│   ├── knowledge_loader.py  # CSV → LangChain Documents
│   ├── retriever.py         # FAISS build / load / retrieve
│   ├── prompt_builder.py    # Structured prompt construction
│   └── pipeline.py          # End-to-end RAG orchestration
├── utils/
│   ├── logger.py            # Centralised structured logging
│   └── language_detector.py # Heuristic style classifier
├── data/
│   └── knowledge_base.csv   # 50+ Corporate ↔ Gen Z term pairs
└── vectorstore/
    └── faiss_index/         # Auto-generated on first run (gitignored)
```

---

## 🚀 Quick Start

### 1. Clone

```bash
git clone https://github.com/yourname/crossspeakai.git
cd crossspeakai
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API keys

```bash
cp .env.example .env
# Edit .env and fill in at least GEMINI_API_KEY_1
```

### 4. Run locally

```bash
streamlit run app.py
```

The FAISS index is built automatically on first run and cached for subsequent starts.

---

## ☁️ Streamlit Cloud Deployment

1. Push your repository to GitHub (**do not commit `.env`**).
2. Go to [share.streamlit.io](https://share.streamlit.io) and create a new app.
3. Set **Main file path** to `app.py`.
4. Open **Advanced settings → Secrets** and add:

```toml
GEMINI_API_KEY = "your-primary-gemini-key"

# Optional failover keys:
GEMINI_API_KEY_1 = "your-key-1"
GEMINI_API_KEY_2 = "your-key-2"
# … up to GEMINI_API_KEY_5
```

5. Deploy — no other configuration required.

> **Note:** The FAISS index is rebuilt on each cold start (takes ~30 seconds on Streamlit Cloud free tier). This is expected and only happens once per deployment.

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY_1` … `_5` | — | Gemini API keys (at least 1 required) |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model identifier |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace embedding model |
| `KNOWLEDGE_BASE_PATH` | `data/knowledge_base.csv` | Path to the knowledge base CSV |
| `VECTORSTORE_PATH` | `vectorstore/faiss_index` | FAISS index persistence directory |
| `MAX_RETRIEVED_DOCS` | `6` | Max documents per retrieval call |
| `RETRIEVER_SCORE_THRESHOLD` | `0.3` | FAISS L2 similarity threshold |
| `SUPABASE_ENABLED` | `false` | Enables the optional Supabase foundation |
| `SUPABASE_URL` | — | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | — | RLS-constrained Supabase publishable key |
| `DYNAMIC_KB_ENABLED` | `false` | Includes approved Supabase terms in RAG |
| `CONVERSATION_MEMORY_TURNS` | `4` | Recent saved turns included in prompts |

### Supabase foundation

The integration is disabled by default, so the existing public translator does
not make any Supabase requests. To prepare an environment:

1. Apply the numbered SQL files in `supabase/migrations/` in order.
2. Add `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` to Streamlit Secrets.
3. Set `SUPABASE_ENABLED=true` to enable accounts, history, and suggestions.
4. Set `DYNAMIC_KB_ENABLED=true` after migration 002 is applied.

Never add a Supabase secret key to this application. Authenticated clients must
be created per Streamlit user session and must not be globally cached.

---

## 📖 Knowledge Base Format

The CSV at `data/knowledge_base.csv` must contain these columns:

| Column | Required | Description |
|---|---|---|
| `term` | ✅ | The word or phrase |
| `category` | ✅ | `Corporate` or `Gen Z` |
| `meaning` | ✅ | Plain-English definition |
| `translation` | ✅ | Equivalent in the opposite dialect |
| `aliases` | — | Semicolon-separated synonyms |
| `examples` | — | Usage example sentence |
| `notes` | — | Origin or contextual notes |

Add new rows to extend the knowledge base — the index rebuilds automatically.

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| `No Gemini API keys found` | Add keys to `.env` or Streamlit Secrets |
| `FAISS index not found` | Delete `vectorstore/faiss_index/` and restart |
| `429 / quota exceeded` | Add more API keys (up to 5 supported) |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Slow first load | Expected — embeddings download once then cache |

---

## 📜 License

MIT © 2024 Cross Speak AI
