---
document_type: project_context
schema_version: 3
version: 1.12
last_reviewed: 2026-08-18
---

# PROJECT CONTEXT — Baseline (Multi-Tenant Business Operations SaaS)

## 0. Quick-Scan Header

```
PROJECT: Baseline
STAGE: active build — backend built and internally verified for full 11-app scope (MVP core loop + Documents/Notifications/Analytics, all built full production-grade at owner's explicit direction, ahead of original MVP phasing). Frontend is a verified technical scaffold only — no product pages exist yet, pending a scope decision (see NEXT ACTION). Monorepo structure confirmed and in place (`baseline_app/` — `backend/` + `frontend/`).
LAST UPDATED: 2026-08-18 — Owner directed building all previously-deferred modules (Documents/Notifications/Analytics) rather than holding them for a later phase; entitlement enforcement actually wired into creation paths (not just designed); Celery + Beat background jobs added; monorepo structure, combined .gitignore, and enterprise-grade documentation completed across root/backend/frontend; license decided (source-available, non-commercial); frontend naming resolved (casafrique → renamed to baseline; Verazi confirmed as a separate, unrelated product — do not merge assumptions between them).
LIVE BLOCKER: none blocking further backend work. Two items block real frontend page-building specifically: (1) frontend scope undecided — dependency set (EmailJS, one Radix primitive, react-hook-form+zod, no data-fetching/table/chart/auth libraries) reads as a marketing/lead-capture site, not a dashboard for an 11-app CRM, and building CRUD pages under the wrong assumption risks discarded work; (2) design system still undefined (Section 5 gap, unchanged from prior versions).
NEXT ACTION: Owner to resolve the frontend-scope question (marketing site vs. product dashboard) before real pages are built. Separately, and not blocking: (a) run the backend against a live Postgres + Redis instance and execute the full pytest suite — everything shipped has been verified for internal consistency (`manage.py check`, `makemigrations --check --dry-run`, Celery app introspection all pass) but NOT run end-to-end against live infrastructure from the AI side, since no Postgres/Redis binary was available in the build environment; (b) decide a transactional email provider (invitation emails currently print to console only); (c) a public Organization-creation/signup endpoint does not exist yet — first tenant must be bootstrapped via Django admin/shell.
```

---

## 1. Project Overview

**Name:** Baseline. **Confirmed final** by owner 2026-08-17, with trademark/domain clearance to be handled independently by the owner (existing "Baseline" SaaS trademark filings exist in the US for adjacent-but-not-identical categories — asset/predictive-maintenance analytics, environmental/social data reporting, behavior/academic monitoring — none an exact CRM/ops-platform match, but clearance was flagged as not yet done as of this confirmation). Referred to during architecture planning as "Business Operations SaaS" / "SaaS Business Management Platform" before the name was decided.

**One-line description:** Multi-tenant B2B SaaS combining CRM, project management, invoicing, and internal operations tooling — positioned as a smaller, coherent alternative to running HubSpot + Trello + invoicing software separately.

**Problem solved:** Not yet explicitly stated by the owner. Inferred from scope: consolidating fragmented business-operations tooling (customer/lead management, project/task tracking, invoicing, document handling, internal notifications, analytics) into one workspace per company. `[inferred]`

**End users:** Business teams operating as tenant organizations — internal staff (Owners/Admins/Managers/Members/Viewers per the RBAC model) managing their own customers, leads, projects, and invoices within an isolated workspace.

**Business context:** Gravity Concepts in-house product. **Confirmed final by owner 2026-08-17.** Baseline is to carry an **independent brand identity of its own** — not marketed, styled, or presented as a Gravity Concepts-branded tool despite being built and owned in-house. Affects branding/design system work (Section 5) and any public-facing copy (marketing site, ToS, support channels) later — none of that should default to Gravity Concepts visual identity or voice.

**Build stage tier:** Active build. Backend repository exists and is built out across all 11 planned apps (`accounts`, `core`, `customers`, `leads`, `projects`, `invoices`, `billing`, `documents`, `notifications`, `analytics`, `platform_admin`) — see Section 4 and Section 7 for what "built" means here (internal consistency verified; live-database execution not yet performed from the AI side). Frontend repository exists as a routing/tooling scaffold only. Monorepo (`baseline_app/`) confirmed as the repo structure.

**Complexity/scale tier:** Complex-multi-service. Multi-tenancy, RBAC, billing/entitlements, audit logging, and multi-module domain scope (9 core entities) place this above "simple" or "moderate" regardless of year-one tenant count.

**Staleness flag:** Not applicable in the original sense (this is no longer a same-day pass — see Section 11 for the multi-session change history), but flagging directly: this document underwent a large single-pass update on 2026-08-18 covering several sessions' worth of build work at once. Treat Section 4/7's "built" status as accurate to that date; re-verify against the actual repository if picking this up significantly later.

**Definition of "done and working" for this project:** **Originally confirmed 2026-08-17** as core-loop-only (Customers, Leads, Projects, Invoices) with Tasks/Documents/Notifications/Analytics phased to post-MVP. **Superseded 2026-08-18:** owner explicitly directed building the deferred modules (Documents, Notifications, Analytics) in the same build session rather than holding them — see Section 10 superseded facts. The original MVP-boundary reasoning (core loop is what has to work end-to-end; other modules depend on core-loop data existing) still holds as the *reasoning*, but the scope decision it produced was overridden by direct instruction, not by the reasoning changing. All 11 apps are now built full production-grade — the "MVP is a scope boundary, not a quality tier" principle from the prior version of this document held throughout.

---

## 2. Engineering Standard & Acceptance Criteria

No project-specific acceptance criteria have been established yet — architecture-level decisions only. Per-feature acceptance criteria will populate Section 4 as each module (Customers, Leads, Projects, Tasks, Invoices, Documents, Notifications, Analytics) is scoped and built.

- **Functional correctness:** Not yet defined per feature. Open — see Section 10.
- **Reliability:** No SLA/uptime target stated. Behavior under network failure, API timeout, or concurrent access not yet discussed. Open.
- **Security (the one category with real decisions already made):**
  - Trust boundary: tenant (`Organization`) is the hard isolation boundary — no data may cross tenant boundaries under any circumstance.
  - Enforcement is two-layered, both required, neither sufficient alone:
    1. Django ORM: custom manager injecting `tenant_id` filter on every queryset by default, sourced from a request-scoped `contextvar` set from the authenticated session — never from client-supplied input.
    2. PostgreSQL Row-Level Security (RLS) as a backstop: policy on every tenant-scoped table checking `tenant_id = current_setting('app.tenant_id')`, with `SET LOCAL` issued per request/transaction. This exists specifically to catch bypasses of the ORM layer (raw SQL, admin panel, migration scripts, human error).
  - AuthZ is layered per request: AuthN → tenant/membership re-validation (never trust a token's org claim without a DB check) → RBAC (role → permission) → object-level ownership check.
  - Auth strategy is abstracted from day one — not hardcoded to email+password — specifically to support SSO/SAML later without a rewrite. No SSO provider selected yet; not required for initial build.
  - Data classification: not yet itemized (which fields count as sensitive/PII beyond the obvious Customer/Invoice data) — open.
- **Performance:** No budgets set (response time targets, page load targets). Open.
- **Scalability:** Expected load profile: under 100 tenant organizations in year one, mid-market sales-assisted acquisition (not high-volume self-serve). This explicitly ruled out schema-per-tenant and database-per-tenant isolation models as unnecessary overhead at this scale — shared database with row-level tenant scoping was chosen instead. Likely first bottleneck not yet analyzed (no code exists to profile).
- **Maintainability:** Django convention — business logic to be kept out of views (services/managers/utility modules), migrations kept clean and sequential per standing user preference. No project-specific conventions document exists yet.
- **Testing & verification:** Not yet defined. Open.
- **Observability:** Not yet discussed. Open — logging/monitoring/alerting approach undecided.
- **Delivery health trend:** Multi-session build, no CI/measured trend data. Qualitatively: the pattern across sessions has been build → owner review → gap identified (missing enforcement wiring, a packaging bug, insufficient doc depth, a naming mix-up) → fixed same-session. No regressions reported by the owner so far, but nothing has been verified against live infrastructure yet (see Section 7), so "delivery health" here reflects internal-consistency checks, not production incident history.

---

## 3. Technical Context

- **Frontend:** Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS v4 `[confirmed — built as a scaffold; see Section 4]`
- **Backend:** Django 5.1, Django REST Framework, Python 3.12 `[confirmed — built]`
- **Database:** PostgreSQL 16 `[confirmed — required by the RLS-based isolation design, which is Postgres-specific; hard requirement in every environment including local dev, not just production]`
- **Background jobs:** Celery + Celery Beat, Redis 7 as broker/result backend `[confirmed — built; two scheduled tasks live: overdue-invoice detection (hourly), task-due-soon notifications (daily)]`
- **Hosting/infra:** Not yet decided. Open. Deployment target assumptions documented for planning purposes only (backend: any container host supporting Postgres+Redis; frontend: Vercel, inferred from `.gitignore`'s `.vercel` entry) — neither is a confirmed decision.
- **Auth strategy:** Custom, abstracted auth layer. Built using `djangorestframework-simplejwt` for JWT issuance (15-min access token, 7-day rotating refresh with blacklist-on-rotation) with a custom `BaselineAuthBackend` wrapping Django's `ModelBackend` — chosen specifically so SSO/SAML backends can be added alongside it later without touching call sites `[confirmed — built]`.
- **Third-party integrations:**
  - Billing: **Paystack + Opay, dual-provider** `[confirmed, built]`. Webhook handlers (`apps/billing/webhooks.py`) verify HMAC signatures (SHA-512 Paystack, SHA-256 Opay) and normalize both providers into the same `Entitlement` write path. Which provider handles which transaction type is still not specified — open sub-decision, non-blocking (see Section 10).
  - Email delivery: **still not selected.** `EMAIL_BACKEND` is set to Django's console backend — invitation emails print to the server console rather than sending. This is a real functional gap, not a placeholder awaiting confirmation of something already decided.
  - EmailJS (`@emailjs/browser`) appears as a frontend dependency, apparently for a contact/lead-capture form — this is one of the signals behind the open frontend-scope question (Section 10). Not yet wired to any actual form.
- **Repo structure:** **Resolved 2026-08-18** — single monorepo, `baseline_app/`, with `backend/` and `frontend/` as sibling directories, one root `docker-compose.yml` orchestrating both plus Postgres and Redis, one combined root `.gitignore`. This was previously an open question (deferred "until backend build is underway" per the original build-order rule); it has now been resolved in favor of monorepo rather than split repos.
- **Environments:** Four Django settings modules exist (`base`, `development`, `production`, `test`) — see Section 7. Staging is not distinguished from production as a separate settings module yet. No environments discussed beyond local dev.
- **CI/CD:** Not yet built. Open — flagged explicitly as a gap, not assumed.
- **Coding conventions:** Owner's standing preferences applied throughout the build: PEP 8 and Django best practices (service-layer separation — e.g. `EntitlementService`, `NotificationService`, centralized `apps.core.audit.record()` rather than inline logic), functional components + hooks on the frontend, TypeScript throughout, no placeholder/TODO code, full production-grade implementations only, including on the entitlement-enforcement and background-job work added after initial delivery.
- **Package manager/version constraints:** Backend: `requirements.txt` / `requirements-dev.txt`, pinned versions. Frontend: `package-lock.json` present, npm as the package manager (confirmed by which lockfile was provided — no explicit statement against yarn/pnpm/bun, but the lockfile choice is the practical confirmation).
- **Browser/device support targets:** Not yet specified for this project specifically. Moot at present — no product UI has been built yet beyond a placeholder scaffold page.

### 3a. Dependency & Integration Map

| Service/dependency | Purpose | Status | Owner of credentials |
|---|---|---|---|
| Paystack | Billing/payments (NGN) | **Confirmed provider — webhook handler built and normalizing into `Entitlement`; not tested against a real Paystack sandbox** | Not yet applicable |
| Opay | Billing/payments (NGN) | **Confirmed provider — webhook handler built and normalizing into `Entitlement`; not tested against a real Opay sandbox** | Not yet applicable |
| Redis | Celery broker + result backend | **Built** — required for background jobs (overdue-invoice detection, task-due-soon notifications); provided via `docker-compose.yml` for local dev | Not yet applicable |
| Transactional email provider | Invitation delivery, notifications | **Still not selected.** `EMAIL_BACKEND=console` — a real functional gap, not a deferred decision awaiting something else | Not yet applicable |
| Auth/SSO provider | Future SSO/SAML support | Not yet selected — architecture reserves the slot (`User.auth_provider` field, `BaselineAuthBackend` abstraction), no provider chosen | Not yet applicable |
| EmailJS | Frontend contact-form email delivery (apparent purpose) | Present as a frontend dependency, not yet wired to any form — see the open frontend-scope question in Section 10 | Not yet applicable |

---

## 4. Features & Functionality

All 11 planned apps are built: the core platform layer plus Customers,
Leads, Projects (+Task), Invoices, Billing, Documents, Notifications,
Analytics, and platform_admin. "Built" here means: models, serializers,
DRF viewsets, URL routing, Django admin registration, migrations
(including RLS policy migrations and RBAC seed data), and a pytest test
suite exist and are internally consistent (`manage.py check`,
`makemigrations --check --dry-run` both pass clean). It does **not** yet
mean verified against a live PostgreSQL/Redis instance — see Section 0's
NEXT ACTION and Section 10. Per-feature UI/UX acceptance criteria (as
opposed to API/data-model behavior) were never separately scoped for any
module and still don't exist — this section describes what the API layer
does, not what a user-facing flow looks like, since no frontend pages
exist yet.

### Core platform (multi-tenancy, auth, RBAC) — **status: built**
- **What it does:** Establishes the tenant boundary every other module depends on — Organization creation, User↔Organization membership, role-based permissions, workspace switching, invitations, audit logging.
- **Architecture decided:**
  - `Organization` ↔ `User` many-to-many through `Membership` (fields: role, status [`pending`/`active`/`suspended`], joined_at). One user may belong to multiple organizations.
  - Roles are per-organization, not global: Owner, Admin, Manager, Member, Viewer.
  - Permissions modeled as custom `Role`/`Permission`/`RolePermission` tables (resource:action pairs, e.g. `invoices:create`), seeded at migration time — not hardcoded role checks in view logic. django-guardian explicitly rejected as unnecessary overhead for this permission shape.
  - Active workspace context carried in short-lived session/access token, re-validated against DB membership on every request (not trusted from a stale token claim).
  - Invitations: signed token (not bare UUID), 7-day expiry; accepting an invite for an existing email creates the Membership in the same transaction as user creation if the user doesn't yet exist.
  - Audit log: append-only `AuditLog` table (tenant_id, actor_id, action, resource_type, resource_id, diff, ip_address, created_at). Explicitly prioritized for day-one build, not deferred to v2, because mid-market sales-assisted buyers raise it during procurement evaluation.
  - Internal admin/support tooling kept structurally separate from the tenant-facing permission system, to prevent a bug in internal tooling from becoming a tenant-isolation bug.
- **Known edge cases (anticipated, not yet confirmed live):** user removed from org mid-session with a still-valid token (mitigated by design — every request re-validates Membership against the DB, not just the token); invitation accepted after org is deleted/suspended (handled — `InvitationAcceptView` checks `organization.is_suspended`); last Owner attempting to leave an org (`Membership.is_last_owner()` exists as a guard, though not yet wired into a "leave org" endpoint since none exists); concurrent role changes during an active session (not specifically tested).
- **Dependencies:** Everything else in the platform depends on this module existing first.
- **Status:** Built. `apps/core/` — `Organization`, `Membership`, `Permission`/`RolePermission`, `Invitation`, append-only `AuditLog`, `TenantContextMiddleware`, `AuditContextMiddleware`, centralized RBAC (`apps/core/permissions.py`) and audit logging (`apps/core/audit.py`). Not yet verified against a live database — see Section 0.

### Customers, Leads, Projects (+ Task), Invoices — the original MVP core loop
- **What they do:** Customer records (NDPA-aware: `data_source`, `consent_obtained_at`, real `hard_delete()`); Lead pipeline with a conversion-to-Customer event (`Lead.convert()`, preserving the Lead as history, supporting both new-Customer creation and linking to an existing Customer for upsell); Project management with optional Customer attachment (internal projects supported) and a nested Task model with its own optional Project attachment (standalone/personal Tasks supported); Invoice lifecycle (draft→sent→paid/overdue/void, required Customer FK, optional Project FK, deletion disabled by design — void instead).
- **Status:** Built. `apps/customers/`, `apps/leads/`, `apps/projects/`, `apps/invoices/`. Full CRUD via DRF ViewSets, RBAC-gated per action, audit-logged, entitlement-checked where relevant (Project creation checks `EntitlementService.assert_can_add_project()`).

### Billing & Entitlements
- **What it does:** `EntitlementService` (seat limits, project limits, active-subscription checks) — actually wired into the creation paths that matter (`ProjectViewSet.perform_create`, `InvitationViewSet.perform_create` as a fail-fast check, `InvitationAcceptView` as the authoritative check since a seat is only truly consumed at acceptance). Every new `Organization` auto-provisions a `trial` Entitlement via a `post_save` signal, preventing enforcement from locking a brand-new org out of its own first action before it's ever subscribed to a paid plan. Paystack + Opay webhook handlers normalize into the same `Entitlement` write path, idempotent via a `WebhookEvent.provider_event_id` uniqueness constraint.
- **Status:** Built. `apps/billing/`. Not tested against real Paystack/Opay sandbox webhooks — signature verification logic exists and is unit-testable, but no live provider round-trip has occurred.

### Documents, Notifications, Analytics — originally phased out of MVP, built anyway
- **What they do:**
  - **Documents:** File attachments with per-owner explicit FKs (customer/project/invoice — not a polymorphic `GenericForeignKey`, to preserve real DB referential integrity and let RLS apply uniformly), DB-level `CheckConstraint` enforcing exactly one owner. Local filesystem storage; swapping to S3-compatible storage is a settings change, not a model change.
  - **Notifications:** Centralized `NotificationService`, mirroring the audit-log centralization pattern. Loose (non-FK) `resource_type`/`resource_id` reference — a deliberate departure from Documents' FK approach, since a stale notification reference is a harmless UX nit rather than a security/integrity concern. Gated by `recipient=request.user`, not RBAC. Wired into real trigger points: task assignment, invitation acceptance, and the two scheduled background jobs below.
  - **Analytics:** No persisted models — a pure read/aggregation layer over the core-loop models, inheriting tenant isolation for free. Gated by `analytics:view` RBAC (revenue/pipeline data is sensitive).
  - **Background jobs (Celery + Celery Beat):** `check_overdue_invoices` (hourly — flips past-due `SENT` invoices to `OVERDUE`, notifies org Owners/Admins) and `notify_tasks_due_soon` (daily — notifies a Task's assignee when due tomorrow, idempotent per day).
- **Status:** Built, despite being explicitly phased to post-MVP as of v1.7/v1.8 of this document — see Section 10 superseded facts for why the scope boundary changed.

### Established features
No frontend product features are established — the backend API surface described above exists and is internally verified; no user has interacted with any of it through a UI, since none exists yet beyond a placeholder scaffold page.

---

## 5. Design & UI/UX Standard

No design system has been defined for this specific project — no palette, typography, spacing scale, or component patterns have been discussed. This is a prerequisite gap, not a placeholder decision. **Flagged in Section 10.**

**Confirmed constraint:** Baseline is to have an independent brand identity, distinct from Gravity Concepts' own visual identity (adire indigo/terracotta/gold aesthetic used elsewhere, e.g. Wardline). No palette/typography has been carried over or assumed from other Gravity Concepts products — this design system starts from zero, not from inheritance.

Standing requirements that apply regardless (per owner's general standard, not yet confirmed as this project's explicit spec):
- Every interactive element designed for all states: default, hover, active, focus, disabled, loading, empty, error, success.
- Genuine responsiveness across realistic breakpoints — intentionally composed at each, not just "doesn't break." Specific breakpoints not yet defined for this project.
- WCAG 2.1 AA as the accessibility floor.
- Four-part design justification test applies to meaningful visual/interaction decisions: logical, strategic, emotional, accessible.

---

## 6. Data & Content

**Key entities (from original scope):** Organization, Team, Customers, Leads, Projects, Tasks, Invoices, Documents, Notifications, Analytics — plus the platform-layer entities decided during architecture planning: User, Membership, Role, Permission, RolePermission, Invitation, AuditLog.

**Relationships confirmed:** Organization is the tenant root; every other entity is scoped under it via `tenant_id`. User↔Organization is many-to-many via Membership. Role/Permission/RolePermission form the RBAC layer, scoped per-organization.

**Relationships confirmed (Invoice):** `Invoice` has a required FK to `Customer` (every invoice belongs to a customer, no exceptions) and an optional/nullable FK to `Project`. Rationale: some customers are billed per-project, others via retainer/one-off invoices with no discrete project — the optional FK supports both without forcing either billing model.

**Relationships confirmed (Lead↔Customer):** Separate entities with a **conversion event**, not a shared table/status field. `Lead.converted_customer` is a nullable FK to `Customer`, set at the point of conversion. The Lead record is preserved as immutable history after conversion (not deleted or merged) — this matters for pipeline analytics, audit logging, and NDPA source/consent tracking, which is Lead-specific data that has no home on a Customer record. The same FK pattern supports linking a new Lead to an *existing* Customer for upsell/expansion scenarios, without requiring a schema change.

**Relationships confirmed (Project↔Customer):** **Optional** FK — `Project.customer` is nullable. Rationale: Baseline explicitly covers internal operations tooling per Section 1's one-line description (e.g. internal projects with no external Customer), so a required FK would force placeholder/fake Customer records, which conflicts with the NDPA data-minimization constraint in Section 8. A many-to-many was considered and rejected for now — no concrete multi-customer-per-project use case has been confirmed, and it would create ambiguity over which Customer's RLS/permission scope governs the Project.

**Relationships confirmed (Tasks↔Projects):** Optional FK — `Task.project` is nullable, allowing standalone/ad-hoc Tasks not attached to a Project (personal to-do items, quick-capture items pending triage). Rationale: matches real-world enterprise PM tool behavior; a required FK would force artificial placeholder Projects as a workaround. `Task` still carries a direct `organization` FK (tenant scope), independent of whether a Project is attached, since tenant isolation cannot depend on an optional relationship.

**Relationships confirmed (Documents):** **Per-owner explicit FKs, not a polymorphic/generic FK.** `Document.customer`, `Document.project`, `Document.invoice` — all nullable, with a DB-level `CHECK` constraint enforcing exactly one is set. A `GenericForeignKey` (ContentType + object_id) was considered and rejected: its `object_id` is an untyped integer with no DB-enforced referential integrity, which would leave one model's tenant-isolation protection resting on the ORM layer alone — undermining the RLS backstop that every other tenant-scoped table relies on (Section 2/7). Per-owner FKs cost a few nullable columns but preserve real FK constraints and let RLS policies apply uniformly.

**Relationships not yet defined:** None remaining at the entity-relationship level for the confirmed MVP + platform scope. Documents/Notifications/Analytics are still deferred as modules (Section 1) — the Document *attachment shape* above is decided so it doesn't block schema design when Documents is eventually built, but no Document feature work is scheduled for MVP.

**Data ownership/source of truth:** Not yet discussed.

**Localization:** Not yet discussed. Given the owner's Nigeria-based business context and the billing/NGN issue already surfaced, this is worth raising explicitly when scoping Invoices. Not yet confirmed as a requirement — noting only as a likely-relevant question.

**Data retention/privacy handling:** Not yet discussed. Given prior work referenced NDPA compliance on a separate project (Casafrique landing page), NDPA (Nigeria Data Protection Act) relevance should be confirmed for this platform too rather than assumed. **Flagged in Section 10.**

---

## 7. Architecture Notes

This section carries real weight for this project — the tenant isolation model is the central architectural decision made so far.

- **Tenant isolation:** Shared database, shared schema, row-level tenant scoping. Rejected alternatives: schema-per-tenant (migration complexity scales badly past ~500 tenants), database-per-tenant (ops cost not justified at <100 tenants, no stated compliance/data-residency requirement forcing it). Reasoning: current scale (under 100 orgs, year one) and customer profile (mid-market, not enterprise-compliance-driven, per owner's confirmation) don't justify heavier isolation models. If enterprise/compliance-driven customers enter the pipeline later, this decision should be revisited — it is not treated as permanent.
- **Enforcement pattern:** Deliberately two-layered (ORM manager + Postgres RLS) rather than relying on a single point of enforcement, specifically because a single missed `.filter(tenant=...)` in application code constitutes a data breach in a multi-tenant system — RLS exists as the safety net against that class of bug.
- **Entitlements/billing pattern:** Subscription status from the billing provider(s) maps to an internal `Entitlement` table (org_id, feature_key, limit_value), refreshed via provider webhooks. Feature gating checks this table centrally via an `EntitlementService`, never inline `org.plan == "x"` checks scattered through the codebase. With Paystack + Opay both in play, each provider's webhook handler normalizes into the same `Entitlement` write path rather than the application ever branching on "which provider" outside the webhook layer itself — the rest of the codebase should be unaware which provider funded a given subscription state.
- **Project structure:** Single Django project, multiple domain-separated apps — a monolith, not a service-oriented/microservices split. Confirmed by owner, referencing an existing project pattern (`mercora-backend`: one repo, one settings/config module, one deployment unit, apps like `accounts`, `core`, `customers`, `orders` sitting side by side as peers). Baseline's app breakdown will follow the same shape, scoped to its own domains (Organization/RBAC, Accounts, Customers, Leads, Projects, Tasks, Invoices, Documents, Notifications, Analytics, platform_admin) rather than mercora's e-commerce/marketplace domains — the reference was for structural pattern only, not a literal app list to copy. Reasoning: lower operational overhead than service-oriented deployment, right-sized for <100 tenants year one, and Django's app boundaries already give clean separation of concerns without deployment complexity.
- **App list confirmed (2026-08-17):** `config` (settings/urls/asgi/wsgi, not an installed app), `accounts` (User, auth backend), `core` (Organization/Membership/Role/Permission/RolePermission/Invitation/AuditLog), `customers`, `leads` (incl. `converted_customer` FK), `projects` (incl. `Task` model nested here, not a standalone app), `invoices`, `billing` (Entitlement, Paystack/Opay webhooks, EntitlementService — kept separate from `invoices` since entitlements are plan-level not document-level), `platform_admin` (structurally isolated internal tooling). **Update 2026-08-18:** `documents`, `notifications`, and `analytics` — originally listed as deliberately deferred/not scaffolded — have since been built in full, at the owner's explicit direction to build everything rather than hold to the original MVP app list. All 11 apps now exist. Naming convention: plural for domain-entity apps, singular for platform/capability apps. **Explicit note, still true: MVP scope governs which modules ship in v1 (moot now — all modules shipped), not the engineering bar — every app is built full production-grade (service-layer separation, full error handling, tests, RLS+ORM enforcement, real migrations), no reduced-quality "MVP-grade" code anywhere.**
- **API design pattern:** REST via Django REST Framework, confirmed by build (not just implied by stack as in prior versions of this document). Standard router-based ViewSets per resource, action-level RBAC via `get_permissions()` overrides, consistent error shape via a custom DRF exception handler (`apps/core/exceptions.py`).
- **State management (frontend):** Not yet decided — no product frontend work has started beyond a routing scaffold; no state-management library is present in `package.json`.
- **Monorepo structure (resolved 2026-08-18):** `baseline_app/` at the repo root, with `backend/` and `frontend/` as siblings, one root `docker-compose.yml`, one combined root `.gitignore`. Backend `Dockerfile` is production-oriented (multi-stage, non-root user, gunicorn); frontend `Dockerfile.dev` is explicitly local-dev-only — production frontend deploy is assumed to be Vercel (inferred from the `.gitignore`'s `.vercel` entry, not a confirmed decision).
- **Verification status (honest, as of 2026-08-18):** Backend internal consistency is verified — `manage.py check` and `makemigrations --check --dry-run` both pass clean across all 11 apps, Celery task registration and the beat schedule were confirmed via direct app introspection, and a full pytest suite exists covering tenant isolation, RBAC, audit-log immutability, NDPA hard-delete, Lead conversion, entitlement enforcement, and scheduled-task idempotency. **None of this has been executed against a live PostgreSQL/Redis instance from the AI side** — no Postgres binary was available in the build sandbox. Frontend verification is stronger: `npm ci`, `npm run build`, and `npm run lint` were all actually executed against the committed `package-lock.json` and passed. This asymmetry (frontend actually run, backend only internally checked) should not be read as the backend being less reliable in principle — it reflects a tooling constraint in the build environment, not a quality gap — but it does mean the backend needs a real `docker compose up` + `pytest` pass before being treated as verified rather than consistent.
- **Naming resolution (2026-08-18):** Three names surfaced during the build and were disambiguated:
  1. **Baseline** — this project, both backend and frontend.
  2. **Verazi** — a separate, independent product (Django + SQLite + Channels), confirmed by the owner as unrelated. A `.gitignore` referencing Verazi was uploaded during this project's work by mistake/for-reference; nothing about Verazi's stack (SQLite, Channels) should be assumed to apply to Baseline, which requires Postgres and has no Channels/websocket usage.
  3. **casafrique** — the frontend's original working name (as scaffolded from an uploaded `package.json`). Owner confirmed casafrique is independent of Baseline, then directed renaming `package.json`/`package-lock.json`'s `name` field to `baseline` regardless, to keep the frontend named consistently with the backend it's paired with in this monorepo. (Re-verified via `npm ci` post-rename — same 355-package resolution, confirming the rename didn't disturb the dependency tree.)
- **License (resolved 2026-08-18):** Source-available — personal, educational, and non-commercial use only; commercial use/redistribution requires prior written permission from the copyright holder. Previously listed as "not yet decided" in delivered README output; now a firm decision, added by the owner directly to the root README.

---

## 8. Constraints & Guardrails

- **Never happen:** Cross-tenant data leakage, under any circumstance — this is the platform's core trust guarantee and the reason for the double-layered isolation enforcement.
- **Never happen:** Role/permission checks inlined ad hoc in view logic instead of routed through the centralized permission-check layer — this was explicitly called out as a source of permission drift to avoid.
- **Never happen:** Feature/tier gating checks scattered inline instead of centralized through the entitlement service — same rationale, avoiding drift as pricing/tiers change.
- **Regulatory context:** NDPA (Nigeria Data Protection Act) **confirmed in scope** `[confirmed]`. Data model must support: data minimization (no collection of fields not functionally required), a real deletion path (hard-delete capability for data-subject requests, not just soft-delete flags), data export/portability, and consent/source tracking on Customer and Lead records where data originates from a third party (e.g. purchased/imported lead lists). This governs Customer, Lead, and Invoice model design specifically, since those carry the PII/financial data.
- **Out of scope for current phase:** SSO/SAML implementation (architecture reserves the slot; no provider integration is being built yet). Schema-per-tenant or DB-per-tenant isolation (deferred unless the customer profile shifts toward enterprise/compliance-driven buyers).

---

## 9. Instructions to Future AI Models

- **This is no longer pre-development.** A real backend repository exists (`baseline_app/backend/`) with 11 built Django apps and a frontend repository exists (`baseline_app/frontend/`) as a routing/tooling scaffold. Do not treat this as a from-scratch planning conversation or regenerate application code that already exists — read the actual repository/codebase first if you have access to it, and check Section 4/7 of this document for what's built before assuming a module needs to be created.
- **Verification honesty matters here specifically.** This project's backend has been checked for internal consistency (`manage.py check`, migration checks, Celery introspection) but not run against a live database from the AI side, as logged in Section 7. Do not describe the backend as "verified," "tested," or "production-ready" without qualifying that distinction — the owner has pushed back before on documentation overstating confidence relative to what was actually executed.
- **The frontend-scope question is a real, unresolved decision, not a stale gap.** Before adding real pages/components to the frontend, resolve or explicitly flag whether it's a marketing/lead-capture site or a full product dashboard — see Section 10. The current dependency set only supports the former; building CRUD dashboard pages without resolving this risks discarded work.
- **Naming discipline:** this project is Baseline. Verazi is a separate, unrelated product — never merge assumptions, stack choices (SQLite, Channels), or file contents from Verazi into Baseline without an explicit instruction to do so. If a file appears to reference Verazi, flag it rather than silently treating it as applicable here (this happened once already — see Section 11's change log).
- **The billing provider is confirmed** (Paystack + Opay) and integration is built — do not re-litigate this or treat it as an open blocker.
- Do not silently fill Section 10's remaining gaps with assumptions. Where a decision is needed to proceed (e.g., frontend scope, email provider, hosting/infra), surface it explicitly or state the assumption being made and why before generating dependent work — this document's whole change history is a record of gaps being surfaced and resolved one at a time rather than assumed away, and that pattern should continue.
- Apply the owner's standing engineering standard (Section 3 conventions) to all generated code: production-grade only, no placeholders, no truncation, full implementations — this was maintained throughout the actual build (entitlement enforcement, background jobs, and the three "deferred" modules were all built to the same standard as the original MVP scope, not a lesser one).
- When editing shared infrastructure — the `.gitignore`, root `docker-compose.yml`, or any of the three READMEs — check whether the owner has made manual edits since the last AI-generated version before overwriting (this happened once: the owner added the License section by hand and it needed to be preserved, not silently reverted).

---

## 10. Open Gaps, Assumptions & Superseded Facts

**Open gaps:**
- **Frontend scope** — marketing/lead-capture site vs. full product dashboard. Real, unresolved, and blocking real frontend page work (unlike most gaps in this document, this one has a strong contrary signal — the dependency set — rather than just being unstated). See Section 4/9.
- **Trademark/domain clearance for "Baseline"** — Name confirmed final for the build, but legal clearance (US trademark conflicts flagged, Nigeria/CAC name availability unchecked, domain availability unchecked) is owner's responsibility, not yet done as of last check. Not blocking code/architecture work.
- **Billing provider transaction split** — Paystack and Opay both confirmed and integrated, but which handles which payment method/transaction type is still not decided. Not blocking — the webhook layer already normalizes both into the same path regardless of the split.
- **Transactional email provider** — Not selected. `EMAIL_BACKEND=console` in the built settings. This is now a functional gap (invitations don't actually send) rather than a forward-looking placeholder.
- **Public Organization-creation (signup) endpoint** — Does not exist. First tenant must be bootstrapped via Django admin or shell. Not blocking further backend module work, but blocks any real "someone signs up and starts using Baseline" flow.
- **Live-infrastructure verification** — Backend has not been run against a real Postgres/Redis instance or had its pytest suite executed from the AI side (sandbox constraint, not a design gap). See Section 7.
- **Hosting/infra, CI/CD, environments** — Still not decided. No assumed default beyond the inferred-not-confirmed Vercel-for-frontend note in Section 3.
- **Design system** — Still not defined; still flagged in Section 5 as a genuine prerequisite gap, now also a concrete blocker for frontend page work specifically (not just a forward-looking note).
- **Localization requirements** — Still not discussed, still relevant given the NGN/Nigeria business context.
- **Per-feature UI/UX acceptance criteria** — Never separately scoped for any module, still don't exist. The API/data-model layer is built; user-facing flows for it are not designed.

**Superseded facts:**
- **Billing provider** — Previously: unresolved/blocked, Stripe rejected for lack of NGN payout support (as of 2026-08-17, v1.0). Now: Paystack + Opay, dual-provider (as of 2026-08-17, v1.1). Reason: owner confirmed NGN-compatible providers directly.
- **NDPA scope** — Previously: unconfirmed, no assumed default (as of 2026-08-17, v1.0/1.1). Now: confirmed in scope — NDPA-aware data handling (data minimization, deletion/export capability, consent/source tracking on Customer/Lead records) built into the data model from day one (as of 2026-08-17, v1.2). Reason: platform stores Customer/Lead/Invoice PII by design; owner confirmed building compliance-aware structure now rather than retrofitting later.
- **Product name** — Previously: unassigned (as of 2026-08-17, v1.0–1.2). Now: **Baseline** (as of 2026-08-17, v1.3). Reason: owner confirmed after AI recommendation — chosen over Ledger/Cadence for not being finance-coded, since Invoices is one of eight modules rather than the product's core identity.
- **Business context** — Previously: assumed default, Gravity Concepts in-house product, unconfirmed (as of 2026-08-17, v1.0–1.4). Now: confirmed final — in-house product, but with an **independent brand identity**, not presented as a Gravity Concepts-branded tool (as of 2026-08-17, v1.5).
- **Lead↔Customer relationship** — Previously: undefined, open gap (as of 2026-08-17, v1.0–1.6). Now: confirmed — separate entities, conversion event via nullable `Lead.converted_customer` FK, Lead preserved post-conversion for analytics/audit/NDPA history; same pattern supports upsell linking to an existing Customer (as of 2026-08-17, v1.7).
- **Project↔Customer relationship** — Previously: undefined, open gap (as of 2026-08-17, v1.0–1.6). Now: confirmed — optional/nullable `Project.customer` FK, to support internal (non-Customer-facing) projects without placeholder records (as of 2026-08-17, v1.7).
- **MVP / "done" definition** — Previously: not yet defined, no assumed default (as of 2026-08-17, v1.0–1.6). Now: confirmed — core loop only (Customers, Leads, Projects, Invoices) built full-depth for v1; Tasks/Documents/Notifications/Analytics phased to post-MVP (as of 2026-08-17, v1.7).
- **App list/naming** — Previously: undefined, open gap (as of 2026-08-17, v1.0–1.7). Now: confirmed — `config`, `accounts`, `core`, `customers`, `leads`, `projects` (Task nested here), `invoices`, `billing`, `platform_admin`; `documents`/`notifications`/`analytics` deliberately not scaffolded yet (as of 2026-08-17, v1.8).
- **Tasks↔Projects relationship** — Previously: undefined, open gap (as of 2026-08-17, v1.0–1.7). Now: confirmed — optional/nullable `Task.project` FK, standalone Tasks allowed, direct `organization` FK for tenant scope independent of Project (as of 2026-08-17, v1.8).
- **Documents attachment shape** — Previously: undefined, open gap (as of 2026-08-17, v1.0–1.7). Now: confirmed — per-owner nullable FKs (customer/project/invoice) with a DB CHECK constraint for exactly-one, generic/polymorphic FK explicitly rejected on RLS/referential-integrity grounds (as of 2026-08-17, v1.8).
- **MVP scope boundary** — Previously: core loop only (Customers/Leads/Projects/Invoices) for v1, Documents/Notifications/Analytics explicitly phased to post-MVP (as of 2026-08-17, v1.7–1.8). Now: owner directed building all three deferred modules in the same session, plus wiring actual entitlement enforcement (not just the service existing) and adding Celery/Beat background jobs — all 11 apps built to the same production-grade standard (as of 2026-08-18, v1.9–1.10). The original MVP reasoning (core loop is what has to work end-to-end first) wasn't wrong, it was simply overridden by direct instruction to build everything now rather than phase it.
- **Repo structure (monorepo vs. split)** — Previously: open, deferred "until backend build is underway" per the original build-order rule (as of 2026-08-17, v1.0–1.8). Now: confirmed monorepo — `baseline_app/` with `backend/` + `frontend/` siblings, one root `docker-compose.yml`, one combined `.gitignore` (as of 2026-08-18, v1.11).
- **Frontend naming** — Previously: frontend scaffolded under an uploaded `package.json`'s working name, `casafrique`, with no stated relationship to Baseline (as of 2026-08-18, v1.11 initial). Owner then confirmed casafrique is independent of Baseline as a project, but directed renaming `package.json`/`package-lock.json` to `baseline` anyway for consistency within this monorepo (as of 2026-08-18, v1.11).
- **"Verazi" naming confusion** — An uploaded `.gitignore` referenced a project called Verazi (Django + SQLite + Channels), initially raising the question of whether it was a mix-up, a rename, or a real separate project. Owner confirmed: Verazi is a real, independent product, unrelated to Baseline, uploaded for reference purposes only (as of 2026-08-18, v1.11). No Verazi assumptions apply to this codebase.
- **License** — Previously: not yet decided; README output explicitly flagged it as "add before making this repository public" (as of 2026-08-18, v1.11 initial delivery). Now: source-available, personal/educational/non-commercial use only, commercial use requires prior written permission — added directly by the owner to the root README (as of 2026-08-18, v1.12).
- **Documentation depth** — Initial README/`.gitignore` delivery (v1.11) was assessed by the owner as insufficiently thorough for the stated "production grade, enterprise level" bar — lacking a table of contents, architecture diagrams, full environment-variable reference tables, a complete API reference table, and dedicated security/deployment/troubleshooting/roadmap sections. Rewritten to include all of the above across the root, backend, and frontend READMEs (as of 2026-08-18, v1.12). Separately, a real packaging bug was caught and fixed in the same pass: the zip exclusion pattern `*.git*` had been silently stripping `.gitignore` itself from every delivered archive (substring match, not a `.git/`-directory-only match) — not a hidden-file display issue as first assumed.

---

## 11. Change Log

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-08-17 | 1.0 | Initial context file generated from architecture-planning conversation (tenant isolation model, RBAC design, membership/invitation model, audit logging, and billing/entitlement pattern decided; billing provider selection blocked on NGN payout gap) | AI |
| 2026-08-17 | 1.1 | Billing provider live blocker resolved — Paystack + Opay confirmed as dual-provider billing stack. Product name, business context, NDPA scope, and per-module entity relationships remain open but are non-blocking for core platform model build, which now begins. | AI |
| 2026-08-17 | 1.2 | NDPA scope confirmed in-scope (data minimization, deletion/export, consent tracking built in from day one). Invoice↔Customer/Project relationship confirmed (required Customer FK, optional Project FK). Business context set to an explicit assumed default (in-house Gravity Concepts product) pending owner correction, rather than left blank. Remaining open: product name, MVP/done definition, remaining per-module relationships (Lead↔Customer, Project↔Customer, Tasks, Documents), hosting/infra, design system. | AI |
| 2026-08-17 | 1.3 | Project name confirmed: **Baseline**. | AI |
| 2026-08-17 | 1.4 | Name confirmed final by owner despite flagged existing US "Baseline" trademark filings in adjacent SaaS categories (asset/predictive-maintenance analytics, ESG data reporting, academic monitoring) — none an exact category match. Owner will handle trademark/domain clearance independently. Logged as open gap, non-blocking. | AI |
| 2026-08-17 | 1.5 | Business context confirmed final: Gravity Concepts in-house product, but with an independent brand identity — not to be presented/styled as a Gravity Concepts-branded tool. Backend build proceeding from scratch (no existing Django scaffold to build into). Stage moving from pre-development toward active build. | AI |
| 2026-08-17 | 1.6 | Project structure confirmed: single Django project, multiple domain-separated apps (monolith), referencing the `mercora-backend` structural pattern (app-per-domain, one config module) — not a literal app list, not microservices. Monorepo-vs-split-repo question for Next.js frontend deferred until backend is underway. No code generated yet — this was a clarification/confirmation exchange, not a build step. | AI |
| 2026-08-17 | 1.7 | Three open gaps resolved: (1) Lead↔Customer relationship — conversion event via nullable FK, Lead preserved post-conversion; (2) Project↔Customer relationship — optional/nullable FK to support internal projects; (3) MVP/"done" definition — core loop (Customers, Leads, Projects, Invoices) full-depth for v1, Tasks/Documents/Notifications/Analytics phased post-MVP. Remaining open: Tasks↔Projects, Documents↔everything, hosting/infra, design system, trademark clearance, app list/naming. No code generated yet. | AI |
| 2026-08-17 | 1.8 | App list/naming confirmed (`config`, `accounts`, `core`, `customers`, `leads`, `projects`, `invoices`, `billing`, `platform_admin`; `documents`/`notifications`/`analytics` deferred, not scaffolded). Owner clarified MVP is a scope boundary only — every shipped module built full production-grade, no reduced-quality "MVP-grade" code. Tasks↔Projects confirmed optional FK (standalone Tasks allowed). Documents attachment shape confirmed as per-owner explicit FKs with DB CHECK constraint, generic/polymorphic FK rejected on RLS/referential-integrity grounds. Remaining open: hosting/infra, design system, trademark clearance. No code generated yet. | AI |
| 2026-08-18 | 1.9 | Backend build session: full repository created for the confirmed MVP scope — settings split (base/development/production/test), `core` app (Organization/Membership/RBAC/Invitation/AuditLog, two-layer tenant isolation via `TenantScopedModel` + Postgres RLS migrations), `accounts` (custom User, JWT auth), `customers`/`leads`/`projects`/`invoices` (full CRUD, RBAC-gated, audit-logged), `billing` (EntitlementService, Paystack/Opay webhook normalization), `platform_admin`. `manage.py check` and `makemigrations --check --dry-run` verified clean. A real bug caught and fixed during the build: `TenantScopedManager.unscoped()`'s auto-generated implementation would have raised `TenantContextError` before ever reaching the unscoped queryset — fixed by overriding it directly. | AI |
| 2026-08-18 | 1.10 | Owner directed building the three deferred modules (`documents`, `notifications`, `analytics`) rather than holding them to a later phase — all built to the same production-grade standard. Owner separately clarified this wasn't a request to lower the bar for anything: entitlement enforcement was found to be designed but not actually wired into any creation path, so `EntitlementService` checks were added to Project creation and the Invitation create/accept flow, including a `post_save` signal auto-provisioning a trial Entitlement per new Organization to avoid locking brand-new orgs out. Celery + Celery Beat added for two previously-unfired notification types (`INVOICE_OVERDUE`, `TASK_DUE_SOON`), with real scheduled tasks and idempotency guards. Owner explicitly declined SQLite as a dev-convenience substitute for Postgres when offered, on RLS-parity grounds — `docker-compose.yml` added instead to solve the actual friction (Postgres/Redis setup) without weakening the environment the RLS backstop runs in. | AI |
| 2026-08-18 | 1.11 | Frontend and monorepo work: `requests.http` built covering every backend endpoint; `.env`/`.env.example` (backend) and `.env`/`.env.local`/`.env.example`/`.env.production` (frontend) created. Frontend scaffolded from an uploaded `package.json` (Next.js 15/React 19/Tailwind v4) under its original working name `casafrique` — flagged as a likely scope mismatch (dependency set reads as marketing site, not CRM dashboard) rather than silently building dashboard pages under an unverified assumption. Owner confirmed casafrique is independent of Baseline, then directed renaming it to `baseline` anyway for monorepo consistency (re-verified via `npm ci` post-rename). Repo restructured into a single monorepo (`baseline_app/` — `backend/` + `frontend/`), root `docker-compose.yml`, combined `.gitignore`. Separately, an uploaded `.gitignore` referencing an unrelated project ("Verazi" — Django+SQLite+Channels) was caught before being mistakenly applied to Baseline; owner confirmed Verazi is a real, independent product, uploaded for reference only. | AI |
| 2026-08-18 | 1.12 | Owner assessed the initial README/`.gitignore` delivery as too basic for the stated "production grade, enterprise level" bar and pointed out the `.gitignore` appeared to be missing entirely. Root cause found and fixed: the zip packaging command's exclusion pattern (`*.git*`) was a substring match that silently stripped `.gitignore` from every delivered archive — not a hidden-file/display issue as first assumed. All three READMEs (root, backend, frontend) rewritten with tables of contents, architecture diagrams, complete environment-variable reference tables, a complete API endpoint reference table, and dedicated security/deployment/troubleshooting/roadmap sections. Owner's manually-added License section (source-available, non-commercial) preserved exactly rather than overwritten. This project-context document brought current to reflect the full build across all sessions — prior versions had drifted significantly stale (still describing the project as pre-development with zero code written). | AI |
