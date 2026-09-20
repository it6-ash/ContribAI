# ContribAI

**Find the open-source issue that is actually right for you.**

GitHub already recommends repositories from your activity and stars. The gap is one
level down: given *this* issue and *this* contributor, is it a realistic pull request,
and what would it take? ContribAI models both sides and answers that.

```
GitHub profile -> skill graph -> issue corpus -> hard filters -> retrieval
              -> weighted scoring -> explanation -> skill gap -> contribution plan
```

---

## Quick start

Nothing below requires a GitHub account, an API key, or network access. The demo
corpus (5 repositories, 23 issues, 3 contributor profiles) is seeded on first boot.

```bash
# backend
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Linux/macOS: .venv/bin/python
.venv/Scripts/python -m uvicorn app.main:app --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000, click **Explore demo**, pick `@alex`.

Optional configuration lives in `backend/.env` (see `backend/.env.example`). Every key
is optional; the product degrades to deterministic heuristics rather than failing.

---

## What it actually does

### 1. A skill graph from evidence, not self-assessment

`app/skills.py` derives skills from countable GitHub signals: repository languages and
byte counts, dependency manifests (`requirements.txt`, `package.json`, `go.mod`,
`pyproject.toml`), topics, commit recency, and merged pull requests. Forks are excluded
because they are not evidence of authorship.

Each signal carries a weight, and confidence saturates with diminishing returns, so
seven Python repositories do not produce a 700% Python score. Every skill stores the
evidence that produced it, and the UI shows it on expand.

Self-reported skills are stored separately and can never be silently demoted by a
GitHub re-scan.

### 2. Issue understanding

`app/analysis.py` produces, for each issue: a plain-language problem statement,
difficulty with its rationale, an effort range, required skills, concepts, likely
affected files, a suggested investigation order, and the things you should verify
before writing code.

Likely files are found by scoring repository tree paths against issue vocabulary, with
explicit filename mentions in the issue body resolved against the tree first. It is
token overlap, not an AST parse, and the UI labels it an inference.

### 3. Matching, in four stages

`app/matching.py`:

| Stage | What it does |
|---|---|
| 1. Hard filters | Drops closed, assigned, already-has-a-PR, wontfix/stale, security-labelled, inactive-repo, and out-of-stack issues. Reports what it dropped and why. |
| 2. Retrieval | TF-IDF cosine between the contributor profile and the issue corpus. |
| 3. Scoring | Eight weighted dimensions. Runs with no model call, so it is reproducible. |
| 4. Reasoning | The LLM writes prose over stages 1-3. It never changes the numbers. |

Weights: skill match 30%, difficulty fit 20%, technology match 15%, repository
accessibility 10%, issue clarity 10%, effort fit 5%, learning value 5%, repository
activity 5%. They are shown in the UI, because a ranking you cannot inspect is a
ranking you cannot trust.

Text similarity contributes at most 10% of the final score. It breaks ties; it does not
drive them. `test_semantic_similarity_cannot_dominate_the_score` pins this.

### 4. Facts, inferences and estimates never share a line

- **Fact** - the repository contains CONTRIBUTING.md; last commit 2 days ago.
- **Inference** - this issue probably needs SQLAlchemy familiarity.
- **Estimate** - roughly 3 to 6 hours.

Model-written text is tagged `ai-written`; rule-derived text is tagged `rule-derived`.
Stored separately too: `issues` holds the GitHub payload, `issue_analysis` holds the
interpretation.

---

## Design decisions worth defending

**No vendor SDK for the LLM.** Groq serves the OpenAI chat-completions wire format, so
the whole provider is one `httpx` POST (`app/llm.py`). Any OpenAI-compatible host works
by changing `GROQ_BASE_URL`. Default model: `openai/gpt-oss-120b`.

**Every LLM call can return `None`,** and every caller has a deterministic fallback.
With no API key the product still explains issues, generates plans, and answers
workspace questions from the rule-derived analysis. Nothing can break mid-demo because
a model is slow or rate-limited.

**TF-IDF instead of pgvector.** At a few hundred candidate issues, 40 lines of exact
lexical scoring is instant, offline and debuggable. Embeddings are the right call when
the corpus is large enough that lexical overlap genuinely misses matches, not before.

**SQLite by default.** `DATABASE_URL` points at Postgres for a real deployment;
SQLAlchemy handles the rest. Zero infrastructure for the demo.

**Tokens never reach the browser.** The session cookie is httpOnly and carries only a
signed user id. The GitHub access token is Fernet-encrypted at rest and is absent from
every response schema. OAuth requests `read:user` only, never repository write scope.

---

## Tests

```bash
cd backend && .venv/Scripts/python -m pytest tests -q
```

43 tests. The ones that matter are in `tests/test_matching.py`:

- `test_different_profiles_get_different_top_issues` - if this fails, the engine has
  stopped discriminating and is just a search box.
- `test_recommendations_match_the_profile_stack` - the backend dev gets the FastAPI
  issue, the frontend dev gets the React issue, the infra dev gets the Go issue.
- `test_every_recommendation_carries_its_reasoning` - a recommendation with no
  explanation is not shippable.
- `test_security_labelled_issues_are_excluded` - security work is not a first
  contribution and is often embargoed.

---

## Keeping the corpus fresh

A background task inside the API searches GitHub on an interval and ingests what
it finds. No Celery, no Redis, no external scheduler: this app has exactly one
recurring job, and it is idempotent, so an asyncio loop on a sleep is the whole
implementation (`app/scheduler.py`).

```
GITHUB_TOKEN=ghp_...              # required, or the refresh stays idle
REFRESH_INTERVAL_MINUTES=360
REFRESH_LANGUAGES=python,typescript,go
CORPUS_REFRESH_ENABLED=true
```

It stays idle without `GITHUB_TOKEN` on purpose: the anonymous GitHub budget is
60 requests/hour, which one refresh exhausts, leaving the rest of the hour broken.

| Endpoint | Purpose |
|---|---|
| `GET /api/refresh/status` | last run, next run, what it ingested |
| `POST /api/refresh/corpus` | run now, using the signed-in user's own queries |
| `POST /api/ingest/issues` | push a curated corpus from a script (shared secret) |

`POST /api/refresh/corpus` returns immediately and works in the background; a run
takes far longer than a request should block for. A refresh already in progress
refuses to start a second one rather than doubling the GitHub spend.

Known limit: with more than one worker process, each runs its own copy of the
loop. Harmless (every write is an upsert) but wasteful. Add a Postgres advisory
lock if the duplicate GitHub calls start costing quota.

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | provider, corpus size, demo profiles |
| GET | `/api/taxonomy` | skills, modes, scoring weights |
| GET | `/api/auth/github` | OAuth start, `read:user` scope |
| POST | `/api/auth/demo?username=alex` | demo sign-in, no network |
| GET/PUT | `/api/profile` | skill graph and preferences |
| POST | `/api/profile/analyze` | re-read GitHub, rebuild skill graph |
| GET | `/api/recommendations?limit=&refresh=` | ranked matches plus filter stats |
| GET | `/api/issues/{id}` | issue with rule-derived analysis |
| POST | `/api/issues/{id}/analyze` | deep explanation pass |
| POST | `/api/contribution/{id}/plan` | contribution roadmap |
| POST | `/api/contribution/{id}/chat` | workspace assistant |
| GET | `/api/refresh/status` | scheduler state and last run |
| POST | `/api/refresh/corpus` | refresh now, in the background |
| POST | `/api/ingest/issues` | bulk upsert, shared-secret auth |

Interactive docs at http://localhost:8000/docs.

---

## Layout

```
backend/app/
  skills.py     taxonomy + evidence-based extraction
  analysis.py   repository health + issue understanding
  matching.py   filters, TF-IDF retrieval, weighted scoring
  agents.py     contribution planning, gap narration, chat
  llm.py        provider abstraction, always fails soft
  github.py     REST client, TTL cache, rate-limit handling
  services.py   GitHub <-> analysers <-> database
  seed.py       the demo corpus, the only fabricated data in the repo
  api.py        all HTTP routes

frontend/
  app/          landing, onboarding, dashboard, issue, workspace, profile
  components/   skill graph, issue card, match score, roadmap, assistant
```

---

## Not built, on purpose

Automatic PR creation, autonomous code modification, repository cloning, multi-agent
orchestration, and background crawling. A reliable end-to-end path from sign-in to
contribution plan is worth more than a longer feature list.

Fit scores, readiness percentages and effort ranges are internal heuristics. They are
labelled as such everywhere they appear, and none of them is a validated model.
