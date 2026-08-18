# Baseline — Backend

Django + DRF backend for Baseline (CRM / project management / invoicing /
internal ops platform). See `project-context.md` (kept alongside this repo)
for the full product/architecture decision log — this README covers
day-to-day setup only.

## Architecture at a glance

- **Monolith, domain-separated apps** — one Django project (`config/`),
  one deployment unit, apps under `apps/` as peers: `accounts`, `core`,
  `customers`, `leads`, `projects`, `invoices`, `billing`, `documents`,
  `notifications`, `analytics`, `platform_admin`.
- **Multi-tenant, two-layer isolation:**
  1. **ORM layer** — `apps/core/managers.py`: `TenantScopedModel` /
     `TenantScopedManager` auto-filter every query by
     `organization_id = <current tenant>`, sourced from a request-scoped
     `contextvar` (`apps/core/context.py`), never from client input.
  2. **Database layer (backstop)** — Postgres Row-Level Security, applied
     in `apps/core/migrations/0002_row_level_security.py`. Catches
     anything that bypasses the ORM layer (raw SQL, the admin, a bad
     one-off script).

  Both layers are set together, once per request, by
  `TenantContextMiddleware` (`apps/core/middleware.py`). **Do not add a
  new tenant-scoped model without inheriting `TenantScopedModel`.**

- **RBAC** — `apps/core/permissions.py`. Every authorization check goes
  through `has_permission()` / `RequirePermission`, never an inline role
  comparison. Role → permission grants are seeded in
  `apps/core/migrations/0003_seed_rbac.py`.
- **Audit logging** — `apps/core/audit.py`. Every mutation-worthy action
  writes through `record()`. `AuditLog` is append-only, enforced at both
  the ORM layer (`AuditLogQuerySet`) and the DB layer (a trigger in the
  RLS migration).
- **Billing** — `apps/billing/`. `EntitlementService` is the single path
  for "can this org do X" checks (seat limits, project limits, active
  subscription) — and is actually wired into the creation paths that
  matter: `ProjectViewSet.perform_create`, `InvitationViewSet.perform_create`
  (fail-fast check before an invite is even sent), and
  `InvitationAcceptView` (the authoritative check — a seat is only truly
  consumed at acceptance, since org headcount can change between invite
  and accept). Every new Organization auto-provisions a `trial` Entitlement
  via a `post_save` signal (`apps/billing/signals.py`) — this is what
  prevents enforcement from locking a brand-new org out of its own first
  action before it's ever subscribed to a paid plan. Paystack + Opay
  webhooks both normalize into the same `Entitlement` write path
  (`apps/billing/webhooks.py`), idempotent via
  `WebhookEvent.provider_event_id`.
- **Background jobs** — Celery + Celery Beat (`config/celery.py`,
  `CELERY_BEAT_SCHEDULE` in `config/settings/base.py`). Two scheduled
  tasks today: `apps/invoices/tasks.py:check_overdue_invoices` (hourly —
  flips past-due `SENT` invoices to `OVERDUE`, notifies org Owners/Admins)
  and `apps/projects/tasks.py:notify_tasks_due_soon` (daily — notifies a
  Task's assignee when it's due tomorrow, idempotent per day so a retry or
  a second same-day run doesn't double-notify).
- **Documents** — `apps/documents/`. Per-owner explicit FKs (customer/
  project/invoice), not a polymorphic GenericForeignKey — preserves real DB
  referential integrity and lets RLS apply uniformly. A DB `CheckConstraint`
  enforces exactly one owner. Local filesystem storage today; swapping to
  S3-compatible storage later is a `STORAGES` settings change, not a model
  change (see `apps/documents/models.py`).
- **Notifications** — `apps/notifications/`. Created through the
  centralized `NotificationService`, mirroring the audit-log pattern. Uses
  a loose (non-FK) `resource_type`/`resource_id` reference rather than a
  FK — a stale reference here is a harmless UX nit, not a security/
  integrity problem, unlike Documents. Gated by `recipient=request.user`,
  not RBAC — notifications are inherently personal.
- **Analytics** — `apps/analytics/`. No persisted models; a pure read/
  aggregation layer (`AnalyticsService`) over the core-loop models, so
  tenant isolation is inherited for free from each model's own
  `TenantScopedManager`. Gated by `analytics:view` RBAC (revenue/pipeline
  data is sensitive, unlike Notifications).
- **NDPA** — Customer/Lead carry `data_source` + `consent_obtained_at` for
  non-directly-collected data, and `Customer.hard_delete()` performs a real
  DB delete for data-subject erasure requests (distinct from the ordinary
  `is_archived` workflow flag).

## What's deliberately not built

Frontend, hosting/infra, and CI/CD are outside this delivery's scope.
Every backend module named in the confirmed app list (project-context.md
Section 7) is now built: `accounts`, `core`, `customers`, `leads`,
`projects`, `invoices`, `billing`, `documents`, `notifications`,
`analytics`, `platform_admin`.

## Requirements

- Python 3.12+
- **PostgreSQL 15+** — hard requirement, not a preference. RLS policies
  (`apps/*/migrations/*_row_level_security.py`) are Postgres-specific and
  are the second of two tenant-isolation enforcement layers (see
  Architecture above) — they cannot be exercised against sqlite/MySQL, and
  since they're the security backstop, "works in dev" would mean nothing
  if dev never actually runs them. **Don't substitute sqlite for local
  dev** even though it's more convenient to start up — `docker compose up`
  (below) gets you a real Postgres instance in one command, which is the
  actual fix for that friction.
- **Redis** — Celery broker + result backend (background jobs: overdue-
  invoice detection, task-due-soon notifications). Also provided by the
  root `docker-compose.yml` (see below).

## Setup — via Docker (recommended)

This backend is part of the `baseline_app` monorepo — `docker-compose.yml`
lives at the **monorepo root** (one level up from this file), not here, so
it can orchestrate the frontend alongside it. Run these from the repo
root, not from `backend/`:

```bash
cp backend/.env.example backend/.env
# edit backend/.env: DJANGO_SECRET_KEY at minimum (DB_HOST/CELERY_* are
# overridden by docker-compose.yml to point at the `db`/`redis` service names)

docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

This starts Postgres, Redis, the Django app (`web`), a Celery worker,
Celery beat (the scheduler), and the frontend dev server together. See the
root `README.md` for the full monorepo picture. `celery_beat` requires
`django_celery_beat` migrations to have run (included in the standard
`migrate` above) — it reads its schedule from the DB
(`DatabaseScheduler`), not a static file, so schedule changes made via the
Django admin (`Periodic Tasks`) take effect without a restart.

## Setup — without Docker

Run these from inside `backend/`:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
# edit .env: DJANGO_SECRET_KEY, DB_*, CELERY_* at minimum

createdb baseline          # requires a local Postgres install
# requires a local Redis install too, for Celery
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# in separate terminals:
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## Tests

```bash
createdb baseline_test
pytest
```

Tests require a real Postgres connection (same reason as above — RLS
can't be exercised against sqlite). `pytest-django` reuses the test DB
across runs via `--reuse-db` (see `pytest.ini`); pass `--create-db` to
force a rebuild after a migration change.

**Note on this delivery:** the full test suite in `apps/*/tests/` was
written and the complete model graph was validated via
`python manage.py check` and `makemigrations --dry-run` (both pass clean),
but the sandboxed environment this was built in has no Postgres binary
available to actually execute the suite end-to-end. Run `pytest` in a
real dev environment before treating this as verified-green.

## Settings

Three environments under `config/settings/`: `base.py` (shared),
`development.py`, `production.py`. Select via `DJANGO_SETTINGS_MODULE`
(`manage.py` defaults to `development`; `wsgi.py`/`asgi.py` default to
`production`). `config/settings/test.py` extends `development.py` for the
test suite.

## API

All endpoints are under `/api/v1/`. Every tenant-scoped request requires:
- `Authorization: Bearer <access_token>` (JWT, via `/api/v1/auth/login/`)
- `X-Organization-Id: <uuid>` — the active workspace, re-validated against
  a live `Membership` row on every request (never trusted from the token
  alone).

Auth, invitation-accept, health check, admin, and billing webhook routes
are exempt from the `X-Organization-Id` requirement — see
`TenantContextMiddleware.TENANT_EXEMPT_PATH_PREFIXES`.
