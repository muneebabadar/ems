# Employee Attendance

Employees log in and mark attendance once per day. The button reads "Marked Present" (disabled) until the next day; past days are listed with check-in times.

Stack: React (Vite) + Express + Supabase Postgres (raw SQL via `pg`).

## Setup
1. Create a Supabase project, open the SQL Editor, and run `db/init.sql`.
2. Copy `server/.env.example` to `server/.env` and fill it in. Use the **Session pooler** connection string (Project Settings > Database) — Render can't reach Supabase's IPv6-only direct host.
3. Install: `npm --prefix server install && npm --prefix client install`
4. Create an employee: `npm run create-user -- "Jane Doe" jane@company.com secret123`
5. Run in two terminals: `npm run dev:server` and `npm run dev:client`, then open http://localhost:5173.

## Production / Render
One web service serves both API and the built React app.
- Build: `npm run build` — Start: `npm start` (or use `render.yaml`)
- Env vars: `DATABASE_URL`, `JWT_SECRET`, `APP_TIMEZONE`, `NODE_ENV=production`

## Tests
Requires Python and a running Docker. Tests use a temporary local Postgres, never your Supabase DB.
```
pip install -r tests/requirements.txt
python -m playwright install chromium
python -m pytest
```

## Notes
- "Today" is the calendar date in `APP_TIMEZONE`, computed by the database, not the browser.
- The `UNIQUE (employee_id, date)` constraint guarantees one mark per day; a duplicate request returns 409.
