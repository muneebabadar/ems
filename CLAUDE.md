# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Employee attendance app: employees log in and mark attendance once per day; the button shows "Marked Present" (disabled) until the next day, and past days are listed with check-in times. React (Vite) client + Express server + Supabase-hosted Postgres accessed with raw SQL via `pg` (no ORM, no Supabase SDK).

## Commands

Run from the repo root:

- `npm run dev:server` — Express on :3000 with `node --watch`
- `npm run dev:client` — Vite on :5173, proxies `/api` to :3000 (run both in two terminals for development)
- `npm run build` — installs client deps, builds `client/dist`, installs server deps (Render build command)
- `npm start` — production server; serves the API and `client/dist`
- `npm run create-user -- "Full Name" email password` — the only way to create accounts (there is no signup)
- `docker compose up --build` — single container on :3000, reads `server/.env`

### Tests (pytest, black-box)

- Setup once: `pip install -r tests/requirements.txt` and `python -m playwright install chromium`
- `python -m pytest` runs everything. Use `python -m pytest tests/backend` for the API only, or `python -m pytest tests/frontend/test_ui.py::test_mark_attendance_disables_button_and_adds_history` for a single test. Add `--headed` to watch the browser.
- Docker must be running. `tests/conftest.py` starts a throwaway `postgres:16-alpine` container, applies `db/init.sql`, and launches the real Node server against it with `DATABASE_SSL=false` and `APP_TIMEZONE=UTC`. Tables are truncated before each test.
- Backend tests use `requests`; frontend tests use Playwright for Python against the built `client/dist` (built automatically if it's missing, but **rebuild with `npm --prefix client run build` after client changes**, or the tests will run against the stale bundle).
- Day rollover is simulated by inserting past-dated rows with `psycopg`, or in the UI by intercepting `/api/attendance/today` with `page.route`.

There are no linters configured.

## Setup

- Schema lives in `db/init.sql` and is run manually in the Supabase SQL Editor. There is no migration tool, so schema changes mean editing that file and running the SQL by hand.
- `server/.env` (see `server/.env.example`): `DATABASE_URL`, `JWT_SECRET`, `APP_TIMEZONE`, `PORT`, `NODE_ENV`. `server/src/config.js` throws on startup if `DATABASE_URL` or `JWT_SECRET` is missing.
- `DATABASE_URL` must be the Supabase **Session pooler** string (`*.pooler.supabase.com:5432`). The direct host is IPv6-only and doesn't work from Render. The Supabase `NEXT_PUBLIC_*` URL and key are not used.

## Architecture

- **Single deployable:** in production, Express serves `client/dist` as static files with an SPA fallback (`server/src/index.js`), so API and UI share one origin. No CORS. The same layout is used by `Dockerfile` (multi-stage) and `render.yaml`.
- **"Today" is decided by Postgres, not by JS or the browser.** `server/src/routes/attendance.routes.js` computes the date, day name and ms-until-midnight in SQL using `now() AT TIME ZONE $tz`, where `$tz` is `APP_TIMEZONE`. Keep new date logic there, and don't trust client clocks.
- **Once per day is enforced by the DB:** `UNIQUE (employee_id, date)` plus `INSERT ... ON CONFLICT DO NOTHING`. Zero returned rows → 409, which the client treats as "already marked" and resyncs.
- **Dates are returned as `date::text`** (`YYYY-MM-DD`) so that `pg` doesn't convert them to JS `Date` objects and shift them across timezones.
- **Auth:** a JWT (`sub` = employee id) in an httpOnly cookie named `token` (`server/src/middleware/auth.js`). The employee ID always comes from `req.user.id`, never from the request body. `trust proxy` is set so `secure` cookies work behind Render's TLS.
- **Client state:** no state library. `AuthContext` restores the session via `/api/auth/me`. `DashboardPage` holds today's status and history, and re-fetches with a `setTimeout(msUntilNextDay)` and on `visibilitychange`, so the button re-enables at midnight without a reload.
- Server is ESM (`"type": "module"`) on Express 5. Catch-all routes must use `app.use(...)` or named wildcards, not `'*'`.
