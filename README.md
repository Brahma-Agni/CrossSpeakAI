# CrossSpeak AI

CrossSpeak AI translates between corporate English and Gen Z language with a
React interface, a FastAPI backend, Gemini generation, and Supabase-managed
accounts and history.

## Features

- Strict sign-in/register gate before application access
- Separate Corporate and Gen Z personas selected during registration
- Bidirectional translation with a curated retrieval knowledge base
- Five-key Gemini failover
- Supabase authentication, row-level security, conversations, and history
- Free plan limited to three translations; verified paid accounts have unlimited usage
- Razorpay checkout with server-side signature, capture, and webhook verification
- Input and output abusive-language controls
- User slang suggestions and an admin review workflow
- User-controlled light and dark themes
- Vercel-ready React and Python deployment

## Architecture

```text
React + Vite
    -> /api/*
FastAPI
    -> content guard
    -> curated lexical retrieval
    -> Gemini API key failover
    -> Supabase auth, RLS, history, plans, and suggestions
```

The lightweight deterministic retriever avoids shipping a local ML runtime in
the serverless function. It also produces 384-dimensional vectors for approved
term matching in Supabase.

## Run locally

Requirements: Python 3.12+ and Node.js 20+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
npm --prefix frontend ci
uvicorn server:app --reload --port 8000
```

In a second terminal:

```bash
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5174`. Vite proxies `/api` requests to FastAPI on port
8000.

## Configuration

Configure these values in `.env` locally and as encrypted Vercel environment
variables when deployed:

| Variable | Required | Description |
|---|---:|---|
| `GEMINI_API_KEY_1` ... `_5` | At least one | Gemini generation keys used in failover order |
| `GEMINI_MODEL` | No | Gemini model; defaults to `gemini-1.5-flash` |
| `SUPABASE_ENABLED` | Production | Set to `true` for managed authentication and storage |
| `SUPABASE_URL` | With Supabase | Project URL |
| `SUPABASE_PUBLISHABLE_KEY` | With Supabase | Publishable, RLS-constrained key only |
| `DYNAMIC_KB_ENABLED` | No | Enables approved-term vector search |
| `CONVERSATION_MEMORY_TURNS` | No | Prior conversation turns included in prompts |
| `PAYMENTS_ENABLED` | No | Set to `true` only after all billing secrets and migration 005 are ready |
| `RAZORPAY_KEY_ID` | With payments | Razorpay test/live key ID; returned to Checkout only when an order is created |
| `RAZORPAY_KEY_SECRET` | With payments | Server-only Razorpay key secret |
| `RAZORPAY_WEBHOOK_SECRET` | With payments | Server-only secret configured on the Razorpay webhook |
| `SUPABASE_SECRET_KEY` | With payments | Server-only Supabase secret key used for verified plan activation |
| `PAID_PLAN_AMOUNT_SUBUNITS` | No | Price in currency subunits; defaults to `49900` (₹499) |
| `PAID_PLAN_CURRENCY` | No | Three-letter currency; defaults to `INR` |
| `PAID_PLAN_DURATION_DAYS` | No | Paid access duration; defaults to 30 days |

Never commit `.env`, a Supabase secret/service-role key, a Razorpay secret, or Gemini keys. `SUPABASE_SECRET_KEY`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` must never use a `VITE_` prefix or be exposed to the browser.

## Supabase setup

Create separate development and production Supabase projects. Apply every SQL
file in `supabase/migrations/` in numeric order, then configure the publishable
project values above. The migrations create the profile, conversation,
translation history, suggestions, plan/quota, persona, RLS, and dynamic
knowledge-base structures.

Migration `005_secure_billing.sql` adds private order records, a server-only,
atomic plan-activation function, and a new free allowance that starts after a
paid period expires. A successful checkout does not promote the browser
directly: the backend verifies the checkout signature, fetches the captured
payment from Razorpay, and then activates the plan. A signed
`payment.captured` webhook performs the same activation idempotently.

## Enable paid checkout

1. Apply `supabase/migrations/005_secure_billing.sql` and create a Supabase
   secret key for the backend.
2. In Razorpay Test Mode, create API keys and enable automatic payment capture.
3. Create a webhook for
   `https://your-domain.example/api/billing/webhook`, subscribe to
   `payment.captured`, and set a strong webhook secret.
4. Add the four server secrets plus the plan price/duration to Vercel Preview
   first. Set `PAYMENTS_ENABLED=true` only after they are present.
5. Complete a test payment, verify the profile becomes `paid`, verify the order
   is recorded once, and then repeat the setup with Live Mode keys for
   Production.

The current paid product is a one-time 30-day pass, not an auto-renewing
subscription. Re-purchasing while active extends the existing expiry date.

## Vercel deployment

The repository includes `vercel.json`, `api/index.py`, and `.python-version`.
From the repository root:

```bash
vercel login
vercel
vercel env add GEMINI_API_KEY_1 production
vercel env add SUPABASE_URL production
vercel env add SUPABASE_PUBLISHABLE_KEY production
vercel env add SUPABASE_ENABLED production
vercel env add DYNAMIC_KB_ENABLED production
# Add Razorpay and Supabase server secrets before enabling checkout:
vercel env add SUPABASE_SECRET_KEY production
vercel env add RAZORPAY_KEY_ID production
vercel env add RAZORPAY_KEY_SECRET production
vercel env add RAZORPAY_WEBHOOK_SECRET production
vercel env add PAYMENTS_ENABLED production
vercel --prod
```

Add all configured Gemini keys to both Preview and Production when branch
previews must perform translations. The Vercel configuration builds the React
frontend, sends `/api/*` to the FastAPI function, and falls back to `index.html`
for client-side routes.

## Verification

```bash
python -m unittest discover -s tests
npm --prefix frontend run build
```

The health endpoint is available at `/api/health`.
