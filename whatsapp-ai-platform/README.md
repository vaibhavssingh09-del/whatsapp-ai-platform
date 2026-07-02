# WhatsApp AI Platform

A multi-tenant WhatsApp Business platform: an agentic LangGraph bot answers customers automatically,
hands off to a human when it's unsure, and gives your team a dashboard to monitor conversations, send
broadcast campaigns, and review an audit trail.

> **Honest scope note:** this repo is a complete, working, end-to-end implementation of every
> requirement in the assignment. It is sized to be realistic to build and *understand* in 48 hours,
> which means a few things are intentionally simple rather than enterprise-grade — each one is called
> out inline as a code comment ("Design decision: ...") explaining what it is, why it's simple, and
> what to change to harden it for a larger deployment. Read those comments; they're not filler.

---

## 1. Architecture at a glance

```
                    ┌──────────────┐        ┌─────────────────────┐
   WhatsApp  ──────▶│  /webhook    │───────▶│   LangGraph Agent    │
   customer         │  (FastAPI)   │        │  planner → tools →   │
                    │              │        │  responder → (retry  │
                    │              │        │  / human handoff)    │
                    └──────┬───────┘        └──────────┬───────────┘
                           │                            │
                           ▼                            ▼
                    ┌──────────────────────────────────────────┐
                    │              MongoDB Atlas                │
                    │  tenants · users · conversations ·        │
                    │  messages · media_assets · broadcasts ·   │
                    │  audit_logs · agent_sessions              │
                    └──────────────┬─────────────────────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │   React Dashboard (Vite)      │
                    │  Conversations · Media ·      │
                    │  Broadcasts · Metrics · Audit │
                    └────────────────────────────────┘
```

### Backend layout (`backend/app/`)

| Folder            | Responsibility                                                                 |
|-------------------|---------------------------------------------------------------------------------|
| `core/`           | Settings, security (JWT/hashing), structured logging, MongoDB connection/indexes |
| `models/`         | Pydantic v2 schemas (also the Mongo document shape)                             |
| `repositories/`   | All MongoDB access. Every query is tenant-scoped here (see `repositories/base.py`) |
| `services/`       | Business logic: WhatsApp Cloud API client, webhook parsing, media, broadcast, audit, auth |
| `agent/`          | The LangGraph agent: state, tools, prompts, graph, session runner              |
| `api/routes/`     | FastAPI routers — thin, delegate to services/repositories                       |
| `middleware/`     | Request logging (binds a request_id to every log line in a request)             |

### The LangGraph agent (`backend/app/agent/graph.py`)

This is a real graph, not a linear chain — it has two genuine branch points and one cycle:

```
START → memory_node → planner_node ─┬─→ tool_node ─→ responder_node ─┬─→ END (confident enough)
                                     ├─→ responder_node ───────────────┼─→ retry_node → planner_node (loop)
                                     └─→ handoff_node → END            └─→ handoff_node → END (retries exhausted)
```

- **Planner** decides: call a tool, answer directly, or escalate.
- **Memory** compresses the rolling chat history into a durable summary every turn, so context never
  unboundedly grows the prompt.
- **Tool Registry** (`agent/tools.py`) — currently `get_current_datetime` and `search_faq`; add your
  own by registering a new async function in `TOOL_REGISTRY` + a schema in `TOOL_SCHEMAS`.
- **Retry logic** is about *response quality*, not transport errors: if the responder's self-reported
  confidence is below `AGENT_LOW_CONFIDENCE_THRESHOLD`, the graph loops back to re-plan (up to
  `AGENT_MAX_RETRIES` times) before giving up and escalating.
- **Human handoff** sets the conversation's status to `human_handoff`; the webhook then stops routing
  that customer's messages to the bot until a human marks the conversation resolved again.
- **Confidence scoring** is the responder LLM call's own self-rating (0–1), used purely as the retry/
  handoff signal — not exposed to the customer.
- **Session persistence** (`agent/runner.py`) — the graph itself is stateless and compiled once; all
  per-conversation state (message history, memory summary, retry count, handoff flag) lives in the
  `agent_sessions` Mongo collection and is loaded/saved around each graph invocation. This means the
  agent's memory survives process restarts and works correctly even if you run multiple backend
  replicas.

### Multi-tenancy

Every tenant-scoped Mongo collection is filtered by `tenant_id` inside the repository base class
(`repositories/base.py`) — there is no code path that can query without it. Each tenant has its own
WhatsApp Business number/token, stored on the `Tenant` document, so one deployment serves many
businesses. Users normally belong to one tenant (embedded in their JWT); a small number of users can
additionally be granted `additional_tenant_ids` for the dashboard's **Tenant Switcher**, which re-issues
a JWT scoped to the newly selected tenant rather than trusting a client-side switch.

---

## 2. Prerequisites (macOS)

Install these before anything else:

```bash
# Homebrew (skip if already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3.11
brew install python@3.11

# Node.js (v20 LTS)
brew install node@20
echo 'export PATH="/opt/homebrew/opt/node@20/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Git
brew install git

# Docker Desktop (needed for `docker compose up`)
brew install --cask docker
open /Applications/Docker.app   # start it once and let it finish initializing
```

You'll also need, before you can run the full app end-to-end:
- A **MongoDB Atlas** account (free tier is enough) — https://www.mongodb.com/cloud/atlas/register
- A **Meta Developer** account — https://developers.facebook.com
- An **OpenAI API key** — https://platform.openai.com/api-keys

---

## 3. Installation

```bash
git clone <your-repo-url> whatsapp-ai-platform
cd whatsapp-ai-platform

# --- Backend ---
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# now edit backend/.env — see "Environment Variables" below

# --- Frontend ---
cd ../frontend
npm install
cp .env.example .env
```

---

## 4. Environment variables

All backend variables live in `backend/.env` (copied from `.env.example`). Here's what each one is and
where to get it:

| Variable | What it is | Where to get it |
|---|---|---|
| `JWT_SECRET_KEY` | Signs/verifies dashboard login tokens | Generate: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | Which frontend origins may call the API | `["http://localhost:5173"]` for local dev |
| `MONGO_URI` | Atlas connection string | Atlas dashboard → Database → **Connect** → **Drivers** → Python |
| `MONGO_DB_NAME` | Database name inside the cluster | Any name, e.g. `whatsapp_ai_platform` |
| `OPENAI_API_KEY` | Powers the LangGraph agent's LLM calls | https://platform.openai.com/api-keys |
| `OPENAI_MODEL` | Which OpenAI model the agent uses | Default `gpt-4o-mini` works well and is cheap for a bot |
| `META_APP_SECRET` | Verifies webhook signatures | Meta App Dashboard → App Settings → Basic → **App Secret** |
| `META_VERIFY_TOKEN` | A string *you* invent, re-entered in Meta's webhook config | Make one up, e.g. `openssl rand -hex 16` |
| `MEDIA_STORAGE_DIR` | Local folder for uploaded images/PDFs | Default `./media_storage` is fine for dev |
| `AGENT_MAX_RETRIES` | How many times the agent re-plans on low confidence | Default `2` |
| `AGENT_LOW_CONFIDENCE_THRESHOLD` | Confidence floor before retry/handoff | Default `0.55` |

Per-tenant WhatsApp credentials (`whatsapp_phone_number_id`, `whatsapp_business_account_id`,
`whatsapp_access_token`) are **not** environment variables — they're stored on each `Tenant` document
in Mongo, because this is a multi-tenant platform where each business has its own WhatsApp number. Set
them via the seed script or by inserting/editing a tenant document directly.

Frontend (`frontend/.env`): just `VITE_API_BASE_URL=/api/v1` — leave as-is for both dev and the
Dockerized setup; only change it if frontend and backend are deployed to fully separate origins.

---

## 5. Running the project

### Option A — natively (best for active development)

```bash
# Terminal 1: backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: frontend
cd frontend
npm run dev
# open http://localhost:5173
```

### Option B — Docker Compose (closest to production)

```bash
docker compose up --build
# frontend: http://localhost:5173
# backend:  http://localhost:8000/docs
```

MongoDB is **not** included as a Compose service by design — point `MONGO_URI` at Atlas even locally,
so dev matches production exactly. (Un-comment the `mongo` service in `docker-compose.yml` if you'd
rather run it locally.)

### Seed the database

```bash
cd backend
source venv/bin/activate
python -m scripts.seed
```

This creates a demo tenant ("Demo Store"), two users (`owner@demo-store.test` /
`agent@demo-store.test`, password `ChangeMe123!`), and a handful of dummy conversations with messages
so the dashboard isn't empty on first login. **After seeding**, open the `tenants` collection in Atlas
and replace the placeholder `whatsapp_phone_number_id` / `whatsapp_business_account_id` /
`whatsapp_access_token` fields with your real values from the Meta setup below — the webhook can't
route real messages to this tenant until you do.

### OpenAI

No separate step — as long as `OPENAI_API_KEY` is set in `backend/.env`, the agent works immediately.
Test it in isolation with:

```bash
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

## 6. Meta WhatsApp Cloud API setup

1. **Create a Meta Developer App**
   Go to https://developers.facebook.com/apps → **Create App** → type **Business** → name it anything.

2. **Add the WhatsApp product**
   In the app dashboard, find **WhatsApp** under "Add products to your app" and click **Set up**.

3. **Get your test number + IDs**
   Under WhatsApp → **API Setup** you'll see a temporary test number, its **Phone Number ID**, and your
   **WhatsApp Business Account ID** — copy both into your seeded tenant document.

4. **Get a token**
   The API Setup page gives you a **temporary access token** (24h) for quick testing. For anything
   longer-lived: **Business Settings → System Users** → create a system user → **Generate Token** with
   `whatsapp_business_messaging` + `whatsapp_business_management` permissions → this is your
   **permanent token**. Put it in the tenant's `whatsapp_access_token` field.

5. **App Secret**
   **App Settings → Basic** → click "Show" next to **App Secret** → this is `META_APP_SECRET`.

6. **Verify Token**
   This one you invent yourself (`META_VERIFY_TOKEN` in `.env`) — Meta just echoes it back during setup
   to prove you control the webhook URL.

7. **Expose your local server with ngrok** (Meta requires HTTPS and can't reach `localhost` directly)
   ```bash
   brew install ngrok
   ngrok config add-authtoken <your-ngrok-token>   # from ngrok.com after free signup
   ngrok http 8000
   ```
   Copy the `https://xxxx.ngrok-free.app` URL it prints.

8. **Connect the webhook**
   WhatsApp → **Configuration** → **Webhook** → **Edit**:
   - Callback URL: `https://xxxx.ngrok-free.app/api/v1/webhook/whatsapp`
   - Verify token: whatever you set as `META_VERIFY_TOKEN`
   - Click **Verify and Save** — this triggers the `GET /webhook/whatsapp` handshake in
     `app/api/routes/webhook.py`. If it fails, see Troubleshooting below.
   - Under **Webhook fields**, subscribe to `messages`.

9. **Send a test message**
   From your own phone, message the test number shown in API Setup. You should see it logged in your
   backend terminal and get an AI-generated reply back within a few seconds.

---

## 7. Testing guide

**Webhook verification**
```bash
curl "http://localhost:8000/api/v1/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=<META_VERIFY_TOKEN>&hub.challenge=12345"
# should return: 12345
```

**LangGraph agent (in isolation, no WhatsApp needed)**
```python
# from backend/, with venv active: python
import asyncio
from app.agent.runner import AgentRunner
from app.repositories.misc_repositories import AgentSessionRepository
from app.core.database import connect_to_mongo, get_database

async def main():
    await connect_to_mongo()
    runner = AgentRunner(AgentSessionRepository(get_database()))
    result = await runner.run_turn("test-tenant", "test-convo-1", "What are your store hours?")
    print(result)

asyncio.run(main())
```

**Database**
```bash
# Confirm indexes were created:
# Atlas UI -> your cluster -> Browse Collections -> pick a collection -> Indexes tab
```

**Dashboard**
Log in at `http://localhost:5173` with the seeded credentials, confirm the Conversations list shows the
seeded dummy conversations, and that Metrics reflects them.

**Media replies**
Dashboard → Media Library → upload an image → open a conversation → the send-to-conversation action
(wired via `POST /api/v1/media/{asset_id}/send/{conversation_id}`) uploads it to Meta and delivers it.

**Broadcast**
Dashboard → Broadcasts → New broadcast → you'll need a Meta-approved template name (create one under
WhatsApp Manager → Message Templates first; templates take a few minutes to hours for Meta to approve).

**Human handoff**
Message the bot something like *"I want to speak to a person about a refund"* — the planner should
route to `handoff_node`, the conversation's status flips to `human_handoff` in the dashboard, and an
audit log entry (`conversation.handoff`) appears under Audit Logs.

---

## 8. Troubleshooting (macOS)

**`python3.11: command not found`**
Homebrew installs versioned binaries — try `python3.11` explicitly, or `brew link python@3.11` if it's
shadowed by another Python install (check with `which -a python3`).

**`ModuleNotFoundError` even though `pip install` succeeded**
Your venv probably isn't active. Confirm with `which python` — it should point inside `backend/venv/`.
Re-activate: `source venv/bin/activate`.

**MongoDB connection errors (`ServerSelectionTimeoutError`)**
- Atlas → Network Access → confirm your current IP is allow-listed (or `0.0.0.0/0` for dev-only).
- Double check the password in `MONGO_URI` doesn't have unescaped special characters (URL-encode them).
- Confirm the cluster isn't paused (Atlas free tier pauses after inactivity).

**Docker Desktop issues**
- "Cannot connect to the Docker daemon" → open Docker Desktop from Applications and wait for the whale
  icon in the menu bar to stop animating before running `docker compose up`.
- Apple Silicon build failures on some base images → add `platform: linux/amd64` under the affected
  service in `docker-compose.yml` as a fallback (slower via emulation, but works).

**Port conflicts (`address already in use`)**
```bash
lsof -i :8000   # or :5173
kill -9 <PID>
```

**Node version issues**
```bash
node --version   # should be v20.x
brew unlink node && brew link node@20 --force
```

**OpenAI authentication errors (`401`)**
- Confirm `OPENAI_API_KEY` in `backend/.env` has no leading/trailing whitespace or quotes.
- Confirm the key hasn't been revoked/rotated on the OpenAI dashboard.

**WhatsApp webhook verification failures**
- The callback URL must be reachable over HTTPS — a fresh `ngrok http 8000` restart changes the URL,
  so re-save it in Meta's webhook config every time you restart ngrok (or use a paid ngrok static
  domain to avoid this).
- `META_VERIFY_TOKEN` in `.env` must be the *exact* same string entered in the Meta dashboard field.
- Check backend logs for `webhook_signature_invalid` — this means `META_APP_SECRET` doesn't match; also
  confirm the request actually hit your `/api/v1/webhook/whatsapp` path, not `/webhook/whatsapp`.

---

## 9. Deploying to Render

1. Push this repo to GitHub.
2. Render Dashboard → **New +** → **Blueprint** → point at your repo (uses `render.yaml`).
3. After the first deploy, set the `sync: false` secrets manually on the backend service: `JWT_SECRET_KEY`,
   `MONGO_URI`, `OPENAI_API_KEY`, `META_APP_SECRET`, `META_VERIFY_TOKEN`.
4. Verify the frontend's `BACKEND_ORIGIN` env var resolved to a full URL with scheme
   (`https://whatsapp-ai-platform-backend.onrender.com`) — Render's `fromService` property sometimes
   returns a bare host:port depending on plan/region; if so, set it manually as a plain string env var
   on the frontend service instead.
5. Update the tenant's WhatsApp webhook URL in Meta to the deployed backend's
   `/api/v1/webhook/whatsapp` URL, and update `CORS_ORIGINS` on the backend to the deployed frontend URL.

---

## 10. Scaling beyond 48 hours (not implemented here, called out for honesty)

- **Media storage**: swap `MediaService`'s local-disk methods for S3/R2 — Render's filesystem is
  ephemeral, so uploaded media won't survive a redeploy in the current implementation.
- **Broadcast/webhook processing**: currently runs via FastAPI `BackgroundTasks` (same process, fired
  under the request). At high volume, move to a real task queue (Celery/RQ + Redis) so a burst of
  webhook traffic can't starve the event loop.
- **Metrics**: computed on-demand via Mongo aggregation. Fine at this project's scale; move to a
  scheduled rollup collection once a single tenant's daily message volume gets large.
- **Encryption at rest for `whatsapp_access_token`**: currently stored as plaintext in Mongo (typical
  for an MVP behind Atlas's encryption-at-rest + network controls); for stricter compliance, encrypt
  this field with a KMS-managed key before storing it.
