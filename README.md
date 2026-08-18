# baseline_app

Monorepo for **Baseline** — a multi-tenant B2B SaaS combining CRM, project
management, invoicing, and internal operations tooling. Django/DRF backend,
Next.js frontend.

```
baseline_app/
├── docker-compose.yml    # orchestrates both ends + Postgres + Redis
├── backend/              # Django + DRF API (see backend/README.md)
└── frontend/             # Next.js app (see frontend/README.md)
```

This README covers the monorepo as a whole — setup, architecture summary,
and current status of both ends. Each subproject has its own README for
implementation detail specific to it.

---

## Quickstart

```bash
git clone <repo-url> baseline_app && cd baseline_app

cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# edit backend/.env: DJANGO_SECRET_KEY at minimum
# edit frontend/.env.local: EmailJS values once that account exists

docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

This starts, together: Postgres, Redis, the Django API (`localhost:8000`),
a Celery worker, Celery beat, and the Next.js dev server
(`localhost:3000`). See `backend/README.md` and `frontend/README.md` for
running each side without Docker.

**There is currently no public endpoint to create an Organization.** Use
the Django admin or a shell command to bootstrap your first tenant —
see the note at the top of `backend/requests.http`.

---

## Architecture summary

### Backend

Multi-tenant, two-layer data isolation — every tenant-scoped table is
filtered by the ORM (`apps/core/managers.py`) **and** backstopped by
Postgres Row-Level Security (`apps/core/migrations/0002_row_level_security.py`
and equivalents per app). Neither layer is sufficient alone; both are
required. This is why Postgres is a hard requirement in every environment,
including local dev — RLS doesn't exist on sqlite, so dev would never
actually exercise the backstop layer if it ran there.

Eleven Django apps, one project, no microservices split:
`accounts`, `core` (Organization/Membership/RBAC/Invitation/AuditLog),
`customers`, `leads`, `projects` (+ nested `Task`), `invoices`, `billing`
(`EntitlementService`, Paystack/Opay webhooks), `documents`,
`notifications`, `analytics`, `platform_admin`.

RBAC is centralized (`apps/core/permissions.py` — never an inline role
check), audit logging is centralized and append-only
(`apps/core/audit.py`), and background jobs (overdue-invoice detection,
task-due-soon notifications) run on Celery + Celery Beat.

Full detail: `backend/README.md`.

### Frontend

Next.js 15 (App Router) + React 19 + Tailwind v4 + TypeScript. Currently a
**technical scaffold only** — routing, the API client, and env config are
wired up and verified (`npm ci` / `npm run build` / `npm run lint` all
pass), but no real pages, copy, or visual design exist yet. See "Open
questions" below for why.

Full detail: `frontend/README.md`.

---

## Naming — for anyone new to this repo

This monorepo is **Baseline**, both ends. If you've seen a `.gitignore`
referencing a project called **Verazi** (Django + SQLite + Channels)
anywhere — that's a separate, independent product, unrelated to this
repo. Nothing in `baseline_app` uses SQLite or Channels; don't merge
patterns or assumptions from Verazi into this project.

The frontend's `package.json`/`package-lock.json` were originally
scaffolded under the working name `casafrique`; both have been renamed to
`baseline` to match the backend.

---

## Testing

**Backend:** `backend/requests.http` — every endpoint, ordered as an
end-to-end flow, works with the VS Code REST Client extension or
JetBrains' HTTP Client. `backend/apps/*/tests/` has a full pytest suite
(tenant isolation, RBAC, audit-log immutability, entitlement enforcement,
scheduled-task idempotency, etc.) — run with `pytest` from `backend/`
against a real Postgres/Redis instance (`docker compose up` provides
both).

**Frontend:** `npm run lint` / `npm run build` from `frontend/`. No
component/integration tests yet — none were warranted for a
routing-only scaffold; add them alongside real pages.

---

## Known gaps / honest status

- **The backend has not been run end-to-end against a live Postgres +
  Redis instance from this side of the work.** Every check performed —
  `manage.py check`, `makemigrations --check --dry-run`, Celery app
  introspection — validates internal consistency (the model graph,
  settings, and task registration are all correct relative to each
  other), not actual runtime behavior against a live database. Run
  `docker compose up` + `pytest` before treating the backend as verified
  rather than just consistent.
- **No public Organization-creation endpoint.** First tenant must be
  bootstrapped via Django admin/shell (see `backend/requests.http`).
- **Frontend scope is undecided.** The current dependency set (EmailJS,
  one Radix primitive, react-hook-form + zod, no data-fetching/table/
  chart/auth libraries) reads like a marketing/lead-capture site, not a
  dashboard for an 11-app CRM. Building real pages before this is
  resolved risks throwing away work — see `frontend/README.md`.
- **Email is a no-op in dev** (`EMAIL_BACKEND=console`) — invitation
  emails print to the Django console rather than sending, pending a
  transactional email provider decision.
- **No CI** — no GitHub Actions (or equivalent) running lint/tests/
  migration checks on push yet.

---

## License

This project is source-available for personal, educational, and non-commercial use only.

Commercial use, redistribution as part of a commercial product or service, or use for commercial advantage requires prior written permission from the copyright holder.
