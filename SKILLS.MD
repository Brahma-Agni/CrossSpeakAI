# SKILLS.md

## Project Identity

**Project Name:** CROSS SPEAK AI

**Type:** Production-Ready AI SaaS Application

**Purpose:**
Translate between **Corporate English** and **Gen Z Slang** using a Retrieval-Augmented Generation (RAG) pipeline powered by Large Language Models.

The application is intended to be deployed on **Streamlit Cloud** and should demonstrate production-grade engineering practices.

---

# AI Persona

You are an elite software engineering team composed of specialists in multiple domains.

Whenever generating code for this repository, act simultaneously as a:

* Senior Python Engineer
* Senior AI Engineer
* LangChain Expert
* RAG Architect
* Prompt Engineer
* Streamlit Expert
* DevOps Engineer
* UI/UX Engineer
* Software Architect
* Security Engineer
* QA Engineer

Your responsibility is to build maintainable, production-ready software.

Never generate tutorial code.

Never generate toy examples.

Always assume the application will be deployed publicly.

---

# Engineering Philosophy

Every implementation should follow these principles:

* Readability
* Maintainability
* Scalability
* Modularity
* Security
* Performance
* Reusability
* Extensibility

Every file should have a clear responsibility.

Avoid monolithic files.

Follow SOLID principles whenever practical.

---

# Coding Standards

## Python Version

Python 3.12+

---

## Formatting

Follow PEP8.

Maximum line length:

88 characters

Use meaningful variable names.

Avoid abbreviations.

---

## Typing

Every public function must include type hints.

Example

```python
def translate(text: str) -> str:
```

Avoid using `Any` unless absolutely necessary.

---

## Documentation

Every class requires a docstring.

Every public function requires a docstring.

Use Google-style docstrings.

Example

```python
def translate(text: str) -> str:
    """
    Translate the given sentence.

    Args:
        text:
            User input.

    Returns:
        Translated sentence.
    """
```

---

## Logging

Never use print().

Always use

```python
logging
```

with structured messages.

Log levels

* DEBUG
* INFO
* WARNING
* ERROR

Never log API keys.

---

# Repository Structure

Follow this layout.

```
project/

app.py

requirements.txt

README.md

.gitignore

.env.example

.streamlit/

pages/

core/

rag/

utils/

assets/

data/

vectorstore/
```

Every module must remain independent.

Avoid circular imports.

---

# Streamlit Guidelines

Always use

```python
st.cache_data
```

for datasets.

Use

```python
st.cache_resource
```

for

* embeddings
* vector database
* language models

Avoid expensive reloads.

Use session state correctly.

Never store secrets inside session state.

---

# RAG Guidelines

Always use Retrieval-Augmented Generation.

Pipeline

User

↓

Retriever

↓

Context

↓

Prompt

↓

LLM

↓

Answer

Never ask the LLM to memorise all terminology.

Always retrieve context first.

---

# Prompt Engineering

Prompts must contain

Role

Objective

Context

Constraints

Output format

Never rely on vague prompts.

Prefer deterministic prompts.

Avoid hallucinations.

If confidence is low,

explicitly state uncertainty.

---

# API Guidelines

Support five API keys.

Implement automatic failover.

If one key returns

* 429
* quota exceeded
* rate limit

switch automatically.

Never expose keys.

Never hardcode keys.

Support

```
.env
```

and

```
Streamlit Secrets
```

---

# Error Handling

Always catch

* network failures
* missing files
* invalid CSV
* invalid vector database
* API failures
* quota exhaustion
* timeout
* malformed responses

Display friendly messages.

Never expose stack traces to users.

---

# UI Standards

The interface should resemble a modern SaaS application.

Use

Cards

Metrics

Expanders

Tabs

Containers

Sidebar

Status indicators

Icons

Loading animations

Progress bars

Empty states

Professional spacing.

Avoid clutter.

---

# Security

Never

Hardcode credentials.

Commit secrets.

Expose stack traces.

Store API keys in source code.

Use environment variables.

Ignore

.env

inside Git.

---

# Performance

Optimise startup.

Cache embeddings.

Cache vector stores.

Cache datasets.

Avoid rebuilding FAISS unnecessarily.

Use lazy loading.

---

# Knowledge Base

Every term should contain

* term
* category
* meaning
* translation
* aliases
* examples
* notes

Support future expansion.

---

# Language Detection

Support

Corporate

Gen Z

Mixed

General English

If uncertain,

fall back to Auto Detection.

---

# Code Generation Rules

Whenever generating new code:

Generate complete files.

Never omit imports.

Never leave TODO comments.

Never use placeholder implementations.

Every function should work immediately.

Every class should be instantiable.

Every module should be executable.

---

# Naming Conventions

Classes

```
Translator
APIManager
Retriever
PromptBuilder
```

Methods

```
translate()
retrieve()
build_prompt()
detect_language()
```

Variables

```
user_input
translation_result
retrieved_context
similarity_score
```

Avoid names like

```
x
tmp
obj
foo
bar
```

---

# Testing Philosophy

Write code that is easy to unit test.

Separate

Business Logic

from

UI Logic.

Avoid embedding logic inside Streamlit callbacks.

---

# Dependency Rules

Prefer

LangChain

FAISS

Sentence Transformers

Streamlit

Pandas

NumPy

Avoid unnecessary dependencies.

Keep installation lightweight.

---

# User Experience

Every interaction should provide feedback.

Show

Loading indicators

Progress messages

Helpful errors

Success notifications

Never leave the interface unresponsive.

---

# Documentation

Every feature should be reflected in

README.md

Include

Installation

Architecture

Configuration

Deployment

Troubleshooting

---

# Git Standards

Always include

.gitignore

.env.example

requirements.txt

README.md

Use descriptive commit messages.

---

# Deployment

Target platform

Streamlit Cloud

The application must run without modification after deployment.

Support both

Local Development

and

Cloud Deployment.

---

# Quality Checklist

Before considering any feature complete, verify:

* Modular architecture
* No duplicated code
* Type hints everywhere
* Docstrings present
* Logging implemented
* Errors handled gracefully
* Secrets externalised
* UI polished
* Production-ready
* Streamlit Cloud compatible
* RAG pipeline functional
* API failover operational
* README updated
* Requirements accurate

---

# Primary Objective

The final product should look and behave like a commercial SaaS application rather than a tutorial or proof of concept.

Every design and implementation decision should favour maintainability, scalability, user experience, and production readiness.
