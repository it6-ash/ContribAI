# Going live

One `docker compose up`. Three containers: Postgres, the API, and the web app.
Only the web app is published, on loopback, for your reverse proxy to pick up.

```
browser -> reverse proxy (TLS) -> web:3000 -> /api/* proxied -> api:8000 -> db:5432
```

The API is never reachable from the internet. The browser only ever talks to one
origin, which is what keeps the session cookie working (see below).

---

## 1. What you need to supply

| Key | Required? | Where to get it |
|---|---|---|
| `POSTGRES_PASSWORD` | **yes** | generate |
| `SESSION_SECRET` | **yes** | generate |
| `PUBLIC_ORIGIN` | **yes** | the https URL users will type |
| `GITHUB_TOKEN` | **yes, in practice** | [github.com/settings/tokens](https://github.com/settings/tokens), classic, **no scopes ticked** |
| `GROQ_API_KEY` | optional | [console.groq.com/keys](https://console.groq.com/keys) |
| `GITHUB_CLIENT_ID` / `_SECRET` | optional | GitHub OAuth App |
| `INGEST_TOKEN` | optional | generate, only if you script bulk loads |

**`GITHUB_TOKEN` needs no scopes at all.** Searching public issues is unauthenticated
work; the token exists purely to lift the rate limit from 60/hr to 5000/hr. A
no-scope token that leaks can do nothing. Without it the scheduled refresh stays
idle by design, and your corpus never grows past the demo seed.

**`GROQ_API_KEY` is genuinely optional.** Without it, issue explanations, contribution
plans and the workspace assistant all still work from the deterministic analysis, and
the UI labels them `rule-derived` instead of `ai-written`. Nothing 500s.

**GitHub OAuth callback** must be exactly `${PUBLIC_ORIGIN}/api/auth/github/callback`.
Note that is the *public* origin, not a separate API domain: the proxy forwards the
callback so the cookie lands first-party.

---

## 2. Deploy

```bash
git clone <your-repo> /opt/contribai && cd /opt/contribai

cat > .env <<EOF
PUBLIC_ORIGIN=https://contribai.yourdomain.com
POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d /=+)
SESSION_SECRET=$(openssl rand -base64 48 | tr -d /=+)
GITHUB_TOKEN=ghp_your_no_scope_token
GROQ_API_KEY=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
REFRESH_INTERVAL_MINUTES=360
REFRESH_LANGUAGES=python,typescript,go
EOF
chmod 600 .env

docker compose up -d --build
docker compose logs -f api
```

Expect in the log:

```
production mode: demo corpus not seeded, demo sign-in disabled
corpus refresh every 360 min over [python,typescript,go]
```

Then point your reverse proxy at `127.0.0.1:3000`. Caddy is two lines:

```
contribai.yourdomain.com {
    reverse_proxy 127.0.0.1:3000
}
```

---

## 3. Verify

```bash
curl -s https://contribai.yourdomain.com/api/health | jq
```

`corpus_refresh.enabled` must be `true`. If it is `false`, `GITHUB_TOKEN` is missing
and the corpus will never grow. The first refresh runs 30s after boot; watch
`issues_in_corpus` climb, or check `/api/refresh/status`.

---

## What `ENVIRONMENT=production` changes

The compose file sets it. Three behaviours flip:

- The demo corpus is **not** seeded, so 23 fabricated issues never enter a real
  database where users would read them as real.
- `/api/auth/demo` returns 404, so nobody signs in as `alex`.
- The app **refuses to boot** on a default `SESSION_SECRET` rather than serving
  forgeable session cookies.

⚠️ `SESSION_SECRET` also encrypts stored GitHub tokens. Back it up. Changing it logs
everyone out **and** makes every stored token permanently undecryptable.

---

## Why the frontend proxies /api

With the API on its own hostname, the session cookie is cross-site. `SameSite=Lax`
means the browser never sends it, so every authenticated request 401s while
looking perfectly configured. The alternatives are `SameSite=None; Secure`, which
opens CSRF on every POST and then needs tokens, or routing the browser through one
origin. This does the latter, in `next.config.ts`.

Consequence: do **not** set `NEXT_PUBLIC_API_BASE` to a separate API domain unless
you have read that file and are prepared to deal with CSRF.

---

## Still outstanding before heavy traffic

- **No migrations.** `create_all()` adds missing tables and silently ignores changed
  columns. The first schema change against Postgres needs Alembic or manual SQL.
- **Recommendations re-score the full corpus per request**, and the issue and
  workspace pages each ask for 20. Fine at a few hundred issues; the scheduled
  refresh will eventually outgrow it. Serve the persisted `recommendations` rows
  instead of re-ranking on read.
- **No rate limiting** on the Groq-backed endpoints.
- **Single worker assumed.** The GitHub response cache and the refresh loop are
  both per-process. Raising `--workers` duplicates both.
- **No error tracking.** Logs go to stdout only.
