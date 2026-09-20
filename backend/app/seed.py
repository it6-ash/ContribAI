"""Demo corpus: 5 repositories, 20 issues, 3 contributor profiles.

This exists so the product demonstrates end to end with no network, no GitHub
rate limit and no API key. It is the ONLY place in the codebase that fabricates
GitHub-shaped data, and everything it produces is flagged `is_demo` so it can
never be mistaken for a live fetch.

The three profiles are deliberately different (backend Python / frontend TS /
infra Go) — if the matching engine ever stops producing visibly different
rankings for them, it is broken.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import analysis as analysis_mod
from .models import Issue, IssueAnalysis, Repository, Skill, User, UserSkill
from .skills import BY_NAME


def _ago(days: float) -> datetime:
    return (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)


REPOS: list[dict] = [
    {
        "github_id": 900001,
        "owner": "ledgerly",
        "name": "ledgerly-api",
        "description": "Open-source personal finance API. FastAPI, PostgreSQL, double-entry ledger.",
        "language": "Python",
        "topics": ["fastapi", "python", "postgresql", "fintech", "rest-api"],
        "stars": 3420,
        "forks": 291,
        "open_issues": 64,
        "contributors": 48,
        "last_commit_at": _ago(2),
        "has_contributing": True,
        "has_code_of_conduct": True,
        "has_tests": True,
        "license": "MIT",
        "median_pr_response_hours": 18,
        "setup_commands": ["uv sync", "docker compose up -d postgres", "pytest -q"],
        "readme": "Ledgerly is a double-entry personal finance API built on FastAPI and PostgreSQL. Run `docker compose up -d postgres` then `pytest`.",
        "tree": [
            "README.md", "CONTRIBUTING.md", "pyproject.toml", "docker-compose.yml",
            "src/ledgerly/__init__.py", "src/ledgerly/main.py", "src/ledgerly/config.py",
            "src/ledgerly/api/deps.py", "src/ledgerly/api/transactions.py",
            "src/ledgerly/api/accounts.py", "src/ledgerly/api/auth.py",
            "src/ledgerly/api/budgets.py", "src/ledgerly/api/reports.py",
            "src/ledgerly/services/transaction_service.py",
            "src/ledgerly/services/account_service.py",
            "src/ledgerly/services/budget_service.py",
            "src/ledgerly/services/currency_service.py",
            "src/ledgerly/services/import_service.py",
            "src/ledgerly/models/transaction.py", "src/ledgerly/models/account.py",
            "src/ledgerly/models/user.py", "src/ledgerly/schemas/transaction.py",
            "src/ledgerly/schemas/pagination.py", "src/ledgerly/db/session.py",
            "src/ledgerly/db/migrations/env.py", "src/ledgerly/auth/tokens.py",
            "src/ledgerly/auth/middleware.py", "src/ledgerly/workers/reconcile.py",
            "docs/api.md", "docs/getting-started.md", "docs/authentication.md",
            "tests/test_transactions.py", "tests/test_pagination.py",
            "tests/test_accounts.py", "tests/test_auth.py", "tests/conftest.py",
        ],
        "url": "https://github.com/ledgerly/ledgerly-api",
    },
    {
        "github_id": 900002,
        "owner": "vela-ui",
        "name": "vela",
        "description": "Accessible React component library with zero runtime CSS-in-JS.",
        "language": "TypeScript",
        "topics": ["react", "typescript", "components", "accessibility", "tailwind"],
        "stars": 12800,
        "forks": 740,
        "open_issues": 138,
        "contributors": 126,
        "last_commit_at": _ago(1),
        "has_contributing": True,
        "has_code_of_conduct": True,
        "has_tests": True,
        "license": "Apache-2.0",
        "median_pr_response_hours": 30,
        "setup_commands": ["pnpm install", "pnpm build", "pnpm test"],
        "readme": "Vela is an accessible React component library. `pnpm install && pnpm test`.",
        "tree": [
            "README.md", "CONTRIBUTING.md", "package.json", "tsconfig.json",
            "packages/core/src/index.ts", "packages/core/src/Button/Button.tsx",
            "packages/core/src/Dialog/Dialog.tsx", "packages/core/src/Dialog/useFocusTrap.ts",
            "packages/core/src/Select/Select.tsx", "packages/core/src/Select/useCombobox.ts",
            "packages/core/src/Tooltip/Tooltip.tsx", "packages/core/src/Table/Table.tsx",
            "packages/core/src/Table/useSorting.ts", "packages/core/src/Toast/Toast.tsx",
            "packages/core/src/DatePicker/DatePicker.tsx",
            "packages/core/src/hooks/useMediaQuery.ts",
            "packages/core/src/hooks/useId.ts", "packages/core/src/theme/tokens.ts",
            "packages/core/src/theme/dark.ts", "packages/docs/pages/index.mdx",
            "packages/docs/pages/components/select.mdx",
            "packages/docs/pages/getting-started.mdx",
            "packages/core/__tests__/Dialog.test.tsx",
            "packages/core/__tests__/Select.test.tsx",
            "packages/core/__tests__/Table.test.tsx",
        ],
        "url": "https://github.com/vela-ui/vela",
    },
    {
        "github_id": 900003,
        "owner": "orbitcache",
        "name": "orbit",
        "description": "Distributed cache with consistent hashing and pluggable eviction.",
        "language": "Go",
        "topics": ["go", "cache", "distributed-systems", "redis", "kubernetes"],
        "stars": 8210,
        "forks": 512,
        "open_issues": 47,
        "contributors": 34,
        "last_commit_at": _ago(6),
        "has_contributing": True,
        "has_code_of_conduct": False,
        "has_tests": True,
        "license": "MIT",
        "median_pr_response_hours": 96,
        "setup_commands": ["go mod download", "go test ./...", "make bench"],
        "readme": "Orbit is a distributed cache written in Go. `go test ./...` to run the suite.",
        "tree": [
            "README.md", "CONTRIBUTING.md", "go.mod", "Makefile", "Dockerfile",
            "cmd/orbitd/main.go", "internal/cluster/ring.go", "internal/cluster/gossip.go",
            "internal/cluster/rebalance.go", "internal/store/store.go",
            "internal/store/lru.go", "internal/store/lfu.go", "internal/store/ttl.go",
            "internal/proto/server.go", "internal/proto/client.go",
            "internal/metrics/prometheus.go", "internal/config/config.go",
            "deploy/k8s/statefulset.yaml", "deploy/helm/values.yaml",
            "internal/store/lru_test.go", "internal/cluster/ring_test.go",
            "docs/architecture.md", "docs/operations.md",
        ],
        "url": "https://github.com/orbitcache/orbit",
    },
    {
        "github_id": 900004,
        "owner": "docsmith",
        "name": "docsmith",
        "description": "Generate API reference docs from Python type hints. MkDocs plugin.",
        "language": "Python",
        "topics": ["documentation", "mkdocs", "python", "developer-tools"],
        "stars": 640,
        "forks": 58,
        "open_issues": 23,
        "contributors": 11,
        "last_commit_at": _ago(9),
        "has_contributing": True,
        "has_code_of_conduct": True,
        "has_tests": True,
        "license": "MIT",
        "median_pr_response_hours": 40,
        "setup_commands": ["pip install -e '.[dev]'", "pytest", "mkdocs serve"],
        "readme": "Docsmith turns Python type hints into MkDocs API reference pages. Good first issues are labelled.",
        "tree": [
            "README.md", "CONTRIBUTING.md", "pyproject.toml", "mkdocs.yml",
            "docsmith/__init__.py", "docsmith/plugin.py", "docsmith/parser.py",
            "docsmith/renderer.py", "docsmith/templates/module.html",
            "docsmith/templates/class.html", "docsmith/signatures.py",
            "docsmith/crossref.py", "docsmith/config.py",
            "docs/index.md", "docs/configuration.md", "docs/recipes.md",
            "tests/test_parser.py", "tests/test_renderer.py", "tests/test_signatures.py",
        ],
        "url": "https://github.com/docsmith/docsmith",
    },
    {
        "github_id": 900005,
        "owner": "pipeforge",
        "name": "pipeforge",
        "description": "Lightweight data pipeline orchestrator. Celery workers, Redis broker.",
        "language": "Python",
        "topics": ["python", "celery", "redis", "data-engineering", "docker"],
        "stars": 2150,
        "forks": 187,
        "open_issues": 51,
        "contributors": 22,
        "last_commit_at": _ago(4),
        "has_contributing": True,
        "has_code_of_conduct": False,
        "has_tests": True,
        "license": "Apache-2.0",
        "median_pr_response_hours": 60,
        "setup_commands": ["pip install -e .", "docker compose up -d redis", "pytest -q"],
        "readme": "Pipeforge schedules DAGs of tasks onto Celery workers with a Redis broker.",
        "tree": [
            "README.md", "CONTRIBUTING.md", "pyproject.toml", "docker-compose.yml",
            "pipeforge/__init__.py", "pipeforge/dag.py", "pipeforge/scheduler.py",
            "pipeforge/executor.py", "pipeforge/retry.py", "pipeforge/backends/redis.py",
            "pipeforge/backends/memory.py", "pipeforge/cli.py", "pipeforge/state.py",
            "pipeforge/observability/logging.py", "pipeforge/observability/metrics.py",
            "pipeforge/workers/celery_app.py", "pipeforge/workers/task.py",
            "docs/dags.md", "docs/deployment.md",
            "tests/test_dag.py", "tests/test_scheduler.py", "tests/test_retry.py",
        ],
        "url": "https://github.com/pipeforge/pipeforge",
    },
]


ISSUES: list[dict] = [
    # --- ledgerly/ledgerly-api ---------------------------------------------
    {
        "repo": "ledgerly/ledgerly-api", "github_id": 910001, "number": 1842,
        "title": "Pagination returns wrong page offsets when a transaction filter is applied",
        "labels": ["bug", "api", "help wanted"],
        "comments": 6, "created": 21, "updated": 3,
        "body": """**Describe the bug**
When `GET /transactions` is called with both `?category=groceries` and `?page=2`, the
response contains rows that also appear on page 1, and `total` reflects the unfiltered
count.

**Steps to reproduce**
1. Seed 120 transactions, 30 of them with category `groceries`.
2. `GET /transactions?category=groceries&page=1&per_page=20` → 20 rows, `total: 120`.
3. `GET /transactions?category=groceries&page=2&per_page=20` → 10 rows, 4 of which were
   already on page 1.

**Expected**
`total` should be 30 and pages should not overlap.

**Additional context**
Looks like the offset is computed from the base query before the category filter is
applied in `transaction_service.py`. The count query has the same problem.""",
    },
    {
        "repo": "ledgerly/ledgerly-api", "github_id": 910002, "number": 1856,
        "title": "Refresh tokens are not revoked when a user changes their password",
        "labels": ["bug", "security", "auth"],
        "comments": 9, "created": 14, "updated": 2,
        "body": """Changing a password invalidates the current access token but existing refresh
tokens keep working, so a stolen refresh token survives a password reset.

We should invalidate all refresh tokens for the user on password change. There is a
`token_version` column on `users` that is currently unused — bumping it on password
change and checking it during refresh would do it.""",
    },
    {
        "repo": "ledgerly/ledgerly-api", "github_id": 910003, "number": 1871,
        "title": "Add currency code validation to the account creation endpoint",
        "labels": ["good first issue", "help wanted", "api"],
        "comments": 3, "created": 8, "updated": 1,
        "body": """`POST /accounts` accepts any string as `currency`, so it is possible to create an
account with currency `"BANANA"`.

We should validate against ISO 4217. The `currency_service.py` module already has a
`SUPPORTED_CURRENCIES` set — it just isn't used by the account schema.

**Expected:** 422 with a clear message listing supported currencies.
**Where:** `src/ledgerly/schemas/transaction.py` has an example of a Pydantic field
validator to copy.""",
    },
    {
        "repo": "ledgerly/ledgerly-api", "github_id": 910004, "number": 1802,
        "title": "Reconciliation worker double-counts transactions on retry",
        "labels": ["bug", "workers", "hard"],
        "comments": 17, "created": 46, "updated": 5,
        "body": """The nightly reconcile job is not idempotent. If a worker is killed mid-run and Celery
retries the task, transactions processed before the crash are applied to account balances
a second time.

This needs an idempotency key per (account, run_id) and probably a transactional outbox.
There is disagreement in the thread about whether to do this in the worker or push it
into the database with a unique constraint — read the discussion before starting.""",
    },
    {
        "repo": "ledgerly/ledgerly-api", "github_id": 910005, "number": 1888,
        "title": "Document the authentication flow in docs/authentication.md",
        "labels": ["documentation", "good first issue"],
        "comments": 1, "created": 5, "updated": 1,
        "body": """`docs/authentication.md` is a stub. New users have to read `auth/tokens.py` to work out
how to get a token.

Should cover: obtaining an access token, refreshing it, token lifetimes, and the error
codes returned for expired vs invalid tokens. All of this is already implemented in
`src/ledgerly/auth/`.""",
    },
    {
        "repo": "ledgerly/ledgerly-api", "github_id": 910006, "number": 1863,
        "title": "CSV import silently drops rows with a malformed date",
        "labels": ["bug", "help wanted"],
        "comments": 4, "created": 17, "updated": 6,
        "body": """`import_service.py` wraps date parsing in a bare `except: continue`, so a CSV with a
single bad date imports fewer rows than it has, with no warning.

**Expected:** the import summary should report skipped rows and why, and ideally the
API response should include them so the UI can show the user what failed.

**Reproduce:** import a CSV where one row has `2024-13-45` as the date.""",
    },
    {
        "repo": "ledgerly/ledgerly-api", "github_id": 910007, "number": 1894,
        "title": "Add regression tests for the budget rollover edge cases",
        "labels": ["tests", "help wanted", "good first issue"],
        "comments": 2, "created": 6, "updated": 2,
        "body": """`budget_service.py` handles month rollover but `tests/` has no coverage for:
- a budget created on the 31st rolling into a 30-day month
- a budget whose period spans a DST change
- a zero-amount budget

The behaviour is believed correct; we want tests pinning it down before we refactor.""",
    },

    # --- vela-ui/vela -------------------------------------------------------
    {
        "repo": "vela-ui/vela", "github_id": 910008, "number": 2310,
        "title": "Dialog does not return focus to the trigger element on close",
        "labels": ["bug", "accessibility", "help wanted"],
        "comments": 7, "created": 12, "updated": 2,
        "body": """**Describe the bug**
Opening a `<Dialog>` and closing it with Escape leaves focus on `<body>`. Screen reader
users lose their place, and it fails WCAG 2.4.3.

**Steps to reproduce**
1. Render a Button that opens a Dialog.
2. Tab to the Button, press Enter.
3. Press Escape.
4. Press Tab — focus starts from the top of the document instead of the trigger.

**Expected**
Focus returns to the element that opened the dialog.

`useFocusTrap.ts` stores the previously focused element but never restores it on unmount.""",
    },
    {
        "repo": "vela-ui/vela", "github_id": 910009, "number": 2288,
        "title": "Select: typeahead breaks when options contain diacritics",
        "labels": ["bug", "i18n", "help wanted"],
        "comments": 5, "created": 25, "updated": 4,
        "body": """Typing `mun` does not match the option `München`. The combobox typeahead does a plain
`startsWith` on the raw label.

We should normalise with `String.prototype.normalize('NFD')` and strip combining marks
before comparing, in `useCombobox.ts`. Needs tests for Turkish dotted/dotless i too,
which is where a naive `toLowerCase()` goes wrong.""",
    },
    {
        "repo": "vela-ui/vela", "github_id": 910010, "number": 2341,
        "title": "Table sorting is unstable for rows with equal sort keys",
        "labels": ["bug", "help wanted"],
        "comments": 3, "created": 9, "updated": 3,
        "body": """`useSorting.ts` sorts with a comparator that returns 0 for ties. Array.prototype.sort is
stable in modern engines, but we re-derive the array from a Map each render, so tie order
shifts between renders and rows visibly jump.

Fix should keep a stable secondary key (the row id) in the comparator.""",
    },
    {
        "repo": "vela-ui/vela", "github_id": 910011, "number": 2355,
        "title": "Document the dark theme token overrides",
        "labels": ["documentation", "good first issue"],
        "comments": 0, "created": 4, "updated": 1,
        "body": """`theme/dark.ts` exports a token set but `docs/getting-started.mdx` doesn't explain how to
override individual tokens. Several issues have been opened asking the same question.

A short page with a worked example of overriding `--vela-surface` would close them.""",
    },
    {
        "repo": "vela-ui/vela", "github_id": 910012, "number": 2299,
        "title": "Tooltip renders off-screen near the viewport edge on mobile",
        "labels": ["bug", "help wanted"],
        "comments": 6, "created": 30, "updated": 8,
        "body": """On a 375px-wide viewport, a Tooltip anchored to a right-aligned button overflows the
right edge and is clipped.

We need collision detection — flip to the other side, then clamp. There's prior art in
`Select.tsx` which already handles this for the dropdown.""",
    },
    {
        "repo": "vela-ui/vela", "github_id": 910013, "number": 2364,
        "title": "Rewrite the theming layer on CSS cascade layers",
        "labels": ["enhancement", "architecture", "rfc"],
        "comments": 24, "created": 60, "updated": 3,
        "body": """Our specificity workarounds in `theme/tokens.ts` are fragile — consumers with their own
CSS reset regularly report overridden styles.

Proposal: move the entire theme into `@layer vela.base, vela.components, vela.overrides`.
This is a breaking change for anyone relying on current specificity. Needs an RFC, a
migration guide, and a codemod. See the thread for the debate on the layer names.""",
    },

    # --- orbitcache/orbit ---------------------------------------------------
    {
        "repo": "orbitcache/orbit", "github_id": 910014, "number": 774,
        "title": "Rebalance drops keys when a node rejoins during an in-flight migration",
        "labels": ["bug", "distributed-systems", "hard"],
        "comments": 19, "created": 38, "updated": 4,
        "body": """If node B leaves, a rebalance starts moving its range to node C, and B rejoins before the
migration completes, keys in the overlapping range are deleted from C without ever being
restored on B.

Reproducible with `make test-chaos` about 1 run in 8. Root cause is that `rebalance.go`
treats the ring version as monotonic but gossip can deliver an older view.

This one is genuinely hard — you need to understand the gossip protocol first.""",
    },
    {
        "repo": "orbitcache/orbit", "github_id": 910015, "number": 791,
        "title": "LRU eviction does not respect per-key TTL",
        "labels": ["bug", "help wanted"],
        "comments": 4, "created": 16, "updated": 5,
        "body": """`store/lru.go` evicts strictly by recency. A key with an expired TTL sitting at the hot
end of the list is kept while a live key at the cold end is evicted.

Expected: expired keys are evicted first regardless of position. `ttl.go` already tracks
expiry timestamps; the LRU just doesn't consult them.""",
    },
    {
        "repo": "orbitcache/orbit", "github_id": 910016, "number": 803,
        "title": "Add a Prometheus metric for eviction rate",
        "labels": ["enhancement", "good first issue", "observability"],
        "comments": 2, "created": 7, "updated": 2,
        "body": """We expose hit rate and memory usage but not evictions. Operators can't tell whether a
cache is undersized.

`metrics/prometheus.go` has the pattern to copy — add a counter incremented from the
eviction path in `store/store.go`.""",
    },
    {
        "repo": "orbitcache/orbit", "github_id": 910017, "number": 812,
        "title": "Helm chart ignores the configured resource limits",
        "labels": ["bug", "kubernetes", "help wanted"],
        "comments": 3, "created": 11, "updated": 6,
        "body": """`values.yaml` exposes `resources.limits` but `statefulset.yaml` doesn't template them in,
so limits set by the user are silently ignored and pods run unbounded.

Straightforward templating fix, but needs a test in the chart's CI to stop it regressing.""",
    },

    # --- docsmith/docsmith --------------------------------------------------
    {
        "repo": "docsmith/docsmith", "github_id": 910018, "number": 132,
        "title": "Generated signatures lose default values for keyword-only arguments",
        "labels": ["bug", "help wanted"],
        "comments": 3, "created": 19, "updated": 7,
        "body": """For `def f(*, retries: int = 3)` the generated docs render `retries: int` with no default.

`signatures.py` reads `inspect.Parameter.default` but the keyword-only branch drops it.
Positional arguments are handled correctly, so there's a working example right above the
bug.

Reproduce: run `pytest tests/test_signatures.py -k keyword_only` after adding a case.""",
    },
    {
        "repo": "docsmith/docsmith", "github_id": 910019, "number": 141,
        "title": "Cross-references to inherited methods resolve to the wrong class",
        "labels": ["bug", "help wanted"],
        "comments": 5, "created": 23, "updated": 9,
        "body": """When class `B(A)` inherits `A.save()`, a `[[save]]` reference inside B's docs links to
`A.save` instead of `B.save`, so readers land on the base-class page.

`crossref.py` resolves by MRO and takes the first hit rather than preferring the class
being rendered.""",
    },
    {
        "repo": "docsmith/docsmith", "github_id": 910020, "number": 147,
        "title": "Add a --strict flag that fails the build on unresolved references",
        "labels": ["enhancement", "good first issue"],
        "comments": 1, "created": 6, "updated": 2,
        "body": """Unresolved `[[refs]]` currently render as plain text and ship silently. CI users want the
build to fail instead.

Add `strict: bool = False` to the plugin config in `config.py`, collect unresolved refs
during `renderer.py`, and raise at the end of the build when strict is on.""",
    },

    # --- pipeforge/pipeforge -----------------------------------------------
    {
        "repo": "pipeforge/pipeforge", "github_id": 910021, "number": 418,
        "title": "Retry backoff ignores the configured jitter, causing thundering herd",
        "labels": ["bug", "help wanted", "reliability"],
        "comments": 6, "created": 13, "updated": 3,
        "body": """`retry.py` computes `delay = base * 2 ** attempt` and then never applies `jitter` even
when it is set in the task config. When a downstream API recovers, every retrying task
fires in the same tick and knocks it over again.

**Expected:** full jitter — `random.uniform(0, delay)` — when `jitter=True`.
**Reproduce:** `pytest tests/test_retry.py -k jitter` (the test exists and is marked xfail).""",
    },
    {
        "repo": "pipeforge/pipeforge", "github_id": 910022, "number": 426,
        "title": "Scheduler holds a Redis connection per DAG, exhausting the pool",
        "labels": ["bug", "redis", "performance"],
        "comments": 11, "created": 27, "updated": 4,
        "body": """With more than ~40 DAGs the scheduler exhausts the Redis connection pool and new tasks
queue indefinitely.

`backends/redis.py` creates a client per DAG in `scheduler.py` rather than sharing a pool.
Needs a shared connection pool and probably a semaphore around the state writes. Note the
scheduler is multi-process, so a module-level singleton alone won't be enough.""",
    },
    {
        "repo": "pipeforge/pipeforge", "github_id": 910023, "number": 433,
        "title": "CLI `pipeforge run` crashes with a traceback when the DAG file is missing",
        "labels": ["bug", "good first issue", "cli"],
        "comments": 2, "created": 5, "updated": 1,
        "body": """Running `pipeforge run missing.py` prints a raw `FileNotFoundError` traceback.

**Expected:** a one-line error — `error: DAG file not found: missing.py` — and exit code 2.

`cli.py` should catch it at the command boundary. Other commands already do this; `run`
was missed.""",
    },
]


PROFILES: list[dict] = [
    {
        "username": "alex",
        "bio": "Backend developer. Python, FastAPI, Docker. Built side projects, never contributed to open source.",
        "avatar_url": "https://avatars.githubusercontent.com/u/9919?v=4",
        "experience_level": "developer",
        "mode": "developer_match",
        "interests": ["fastapi", "rest-api", "fintech", "python"],
        "skills": {
            "Python": (0.88, ["7 repositories", "primary language of ledger-cli", "4,200 lines analysed"]),
            "FastAPI": (0.74, ["2 projects", "declared in requirements.txt"]),
            "REST APIs": (0.71, ["referenced in 3 repository descriptions"]),
            "Docker": (0.66, ["Dockerfile in 4 repositories"]),
            "PostgreSQL": (0.58, ["declared in requirements.txt", "2 repositories"]),
            "Git": (0.80, ["23 commits in the last 90 days"]),
            "Testing": (0.49, ["pytest declared in 3 repositories"]),
            "SQL": (0.44, ["2 repositories"]),
            "React": (0.22, ["1 repository"]),
        },
    },
    {
        "username": "priya",
        "bio": "Frontend engineer focused on design systems and accessibility. TypeScript, React, Next.js.",
        "avatar_url": "https://avatars.githubusercontent.com/u/9920?v=4",
        "experience_level": "some_oss",
        "mode": "developer_match",
        "interests": ["react", "accessibility", "components", "typescript"],
        "skills": {
            "TypeScript": (0.86, ["9 repositories", "primary language of design-tokens"]),
            "React": (0.83, ["declared in package.json", "6 repositories"]),
            "Next.js": (0.69, ["3 repositories"]),
            "Tailwind CSS": (0.61, ["declared in package.json"]),
            "Testing": (0.64, ["vitest declared in 4 repositories"]),
            "JavaScript": (0.72, ["5 repositories"]),
            "HTML/CSS": (0.70, ["significant CSS in 6 repositories"]),
            "Git": (0.85, ["3 merged pull requests"]),
            "Documentation": (0.41, ["docs/ directory in 2 repositories"]),
        },
    },
    {
        "username": "rahul",
        "bio": "Infrastructure engineer. Go, Kubernetes, distributed systems. Maintains two small OSS tools.",
        "avatar_url": "https://avatars.githubusercontent.com/u/9921?v=4",
        "experience_level": "experienced",
        "mode": "high_impact",
        "interests": ["distributed-systems", "kubernetes", "go", "cache"],
        "skills": {
            "Go": (0.90, ["8 repositories", "12 merged pull requests"]),
            "Kubernetes": (0.78, ["k8s/ manifests in 5 repositories"]),
            "Docker": (0.82, ["Dockerfile in 7 repositories"]),
            "Redis": (0.63, ["declared in go.mod"]),
            "CI/CD": (0.71, [".github/workflows in 8 repositories"]),
            "Testing": (0.68, ["extensive _test.go coverage"]),
            "Git": (0.92, ["41 commits in the last 90 days"]),
            "Async/Concurrency": (0.74, ["goroutine usage across 6 repositories"]),
            "Python": (0.35, ["2 repositories"]),
        },
    },
]


def seed_all(db: Session, *, analyze: bool = True) -> dict:
    """Idempotent. Safe to call on every startup."""
    repo_by_slug: dict[str, Repository] = {}
    for spec in REPOS:
        repo = db.scalar(select(Repository).where(Repository.github_id == spec["github_id"]))
        if not repo:
            repo = Repository(is_demo=True, **spec)
            db.add(repo)
            db.flush()
        repo_by_slug[f"{spec['owner']}/{spec['name']}"] = repo
        repo.health_score = analysis_mod.repo_health(repo).score

    created_issues = 0
    for spec in ISSUES:
        existing = db.scalar(select(Issue).where(Issue.github_id == spec["github_id"]))
        if existing:
            continue
        repo = repo_by_slug[spec["repo"]]
        issue = Issue(
            github_id=spec["github_id"],
            number=spec["number"],
            repository_id=repo.id,
            title=spec["title"],
            body=spec["body"],
            state="open",
            is_demo=True,
            labels=spec["labels"],
            comments=spec["comments"],
            assignee=None,
            has_linked_pr=False,
            url=f"{repo.url}/issues/{spec['number']}",
            created_at=_ago(spec["created"]),
            updated_at=_ago(spec["updated"]),
        )
        db.add(issue)
        created_issues += 1
    db.flush()

    if analyze:
        # Heuristic only during seeding — deterministic, offline, instant.
        for issue in db.scalars(select(Issue)).unique():
            if issue.analysis:
                continue
            insight = analysis_mod.analyze_issue(issue, use_llm=False)
            db.add(IssueAnalysis(issue_id=issue.id, **insight.to_dict()))

    created_users = 0
    for spec in PROFILES:
        user = db.scalar(select(User).where(User.username == spec["username"]))
        if user:
            continue
        user = User(
            username=spec["username"],
            bio=spec["bio"],
            avatar_url=spec["avatar_url"],
            experience_level=spec["experience_level"],
            mode=spec["mode"],
            interests=spec["interests"],
            is_demo=True,
            profile_analyzed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(user)
        db.flush()
        for name, (confidence, evidence) in spec["skills"].items():
            skill = _get_or_create_skill(db, name)
            db.add(
                UserSkill(
                    user_id=user.id,
                    skill_id=skill.id,
                    confidence=confidence,
                    evidence=evidence,
                    source="github",
                    last_used_at=_ago(14),
                )
            )
        created_users += 1

    db.commit()
    return {
        "repositories": len(REPOS),
        "issues_created": created_issues,
        "profiles_created": created_users,
    }


def _get_or_create_skill(db: Session, name: str) -> Skill:
    skill = db.scalar(select(Skill).where(Skill.name == name))
    if skill:
        return skill
    definition = BY_NAME.get(name)
    skill = Skill(name=name, category=definition.category if definition else "engineering")
    db.add(skill)
    db.flush()
    return skill
