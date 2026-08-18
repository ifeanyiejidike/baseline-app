---
document_type: project_context
schema_version: 3
version: 1.8
last_reviewed: 2026-08-17
---

# PROJECT CONTEXT — Baseline (Multi-Tenant Business Operations SaaS)

## 0. Quick-Scan Header

```
PROJECT: Baseline
STAGE: pre-development (project structure confirmed, zero code written)
LAST UPDATED: 2026-08-17 (0 days ago) — App list, Tasks↔Projects, and Documents attachment shape confirmed. All entity-relationship gaps for the confirmed scope are now closed.
LIVE BLOCKER: none. Remaining open: hosting/infra, CI/CD, design system, trademark/domain clearance (owner-handled) — none of these block starting the backend scaffold.
NEXT ACTION: Owner to give explicit go-ahead to begin scaffolding — settings split, core platform models (Organization/Membership/RBAC/Invitation/AuditLog), tenant-scoped manager, RLS policies, NDPA-aware Customer/Lead fields. MVP build order: Customers → Leads → Projects → Invoices (core loop) before Documents/Notifications/Analytics. All shipped code is full production-grade — MVP is a scope boundary, not a quality tier.
```

---

## 1. Project Overview

**Name:** Baseline. **Confirmed final** by owner 2026-08-17, with trademark/domain clearance to be handled independently by the owner (existing "Baseline" SaaS trademark filings exist in the US for adjacent-but-not-identical categories — asset/predictive-maintenance analytics, environmental/social data reporting, behavior/academic monitoring — none an exact CRM/ops-platform match, but clearance was flagged as not yet done as of this confirmation). Referred to during architecture planning as "Business Operations SaaS" / "SaaS Business Management Platform" before the name was decided.

**One-line description:** Multi-tenant B2B SaaS combining CRM, project management, invoicing, and internal operations tooling — positioned as a smaller, coherent alternative to running HubSpot + Trello + invoicing software separately.

**Problem solved:** Not yet explicitly stated by the owner. Inferred from scope: consolidating fragmented business-operations tooling (customer/lead management, project/task tracking, invoicing, document handling, internal notifications, analytics) into one workspace per company. `[inferred]`

**End users:** Business teams operating as tenant organizations — internal staff (Owners/Admins/Managers/Members/Viewers per the RBAC model) managing their own customers, leads, projects, and invoices within an isolated workspace.

**Business context:** Gravity Concepts in-house product. **Confirmed final by owner 2026-08-17.** Baseline is to carry an **independent brand identity of its own** — not marketed, styled, or presented as a Gravity Concepts-branded tool despite being built and owned in-house. Affects branding/design system work (Section 5) and any public-facing copy (marketing site, ToS, support channels) later — none of that should default to Gravity Concepts visual identity or voice.

**Build stage tier:** Pre-development. Architecture and data-isolation model are decided; no repository, models, or code exist yet.

**Complexity/scale tier:** Complex-multi-service. Multi-tenancy, RBAC, billing/entitlements, audit logging, and multi-module domain scope (9 core entities) place this above "simple" or "moderate" regardless of year-one tenant count.

**Staleness flag:** Not applicable — this is the initial same-day pass (Ground Rule 10, exception for first pass).

**Definition of "done and working" for this project:** **Confirmed 2026-08-17.** MVP is the core revenue-generating loop only: **Customers, Leads, Projects, Invoices** — built full-depth (not stubbed) with the platform layer (Organization/Membership/RBAC/Invitation/AuditLog) underneath. Tasks, Documents, Notifications, and Analytics are explicitly phased out of v1; Tasks may start as a lightweight sub-object of Projects rather than a standalone module. Rationale: this is the part of the product that has to work end-to-end for Baseline to be usable at all — the remaining four modules are supporting infrastructure or depend on core-loop data existing first (Analytics has nothing to analyze otherwise). Per-feature acceptance criteria for the four MVP modules still need to be scoped individually — this defines the *boundary*, not the detailed feature cut within it.

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
- **Delivery health trend:** Not applicable — no build history yet (pre-development, single planning session so far).

---

## 3. Technical Context

- **Frontend:** Next.js, TypeScript `[confirmed — explicitly stated by owner]`
- **Backend:** Django, Python `[confirmed — explicitly stated by owner]`
- **Database:** PostgreSQL `[confirmed — required by the RLS-based isolation design, which is Postgres-specific]`
- **Hosting/infra:** Not yet decided. Open.
- **Auth strategy:** Custom, abstracted auth layer supporting email/password now, designed to accommodate SSO/SAML/OIDC later without rearchitecture `[confirmed — explicit architectural decision]`. No specific auth library (e.g. django-allauth, custom JWT) selected yet. Open.
- **Third-party integrations:**
  - Billing: **Paystack + Opay, dual-provider** `[confirmed]`. Stripe was the initial recommendation but was rejected — no NGN payout support. Dual-provider implies the entitlement layer must not assume a single provider's webhook shape or subscription model; provider-specific webhook handlers should normalize into the same internal `Entitlement` update path rather than each provider having bespoke downstream logic. Which provider handles which transaction type (e.g. cards vs. bank transfer/USSD vs. mobile money) has not been specified — open sub-decision, not yet blocking for model design.
  - No other third-party integrations discussed yet (e.g. email delivery for invitations, which is a stated feature dependency but has no provider selected).
- **Repo structure:** Backend confirmed as a single Django project with multiple domain-separated apps (monolith, not microservices) `[confirmed]`. Whether Next.js frontend lives in the same repo (true monorepo) or a separate repo alongside the Django backend repo is not yet decided — that question is deferred until backend build is underway, per owner's stated build order (backend first, frontend after).
- **Environments:** No local/staging/prod setup discussed yet. Open.
- **CI/CD:** Not yet discussed. Open.
- **Coding conventions:** Owner's standing preferences apply generally (see Section 8 / owner profile): PEP 8 and Django best practices, functional components + hooks on the frontend (no class components), TypeScript preferred over plain JS, feature/domain-based folder structure, no placeholder/TODO code, full production-grade implementations only.
- **Package manager/version constraints:** Not yet specified for this project.
- **Browser/device support targets:** Not yet specified. Owner's general standard requires full responsiveness from 320px mobile through wide desktop, mobile-first approach, WCAG 2.1 AA accessibility floor (per standing preferences, not yet confirmed as project-specific requirement).

### 3a. Dependency & Integration Map

| Service/dependency | Purpose | Status | Owner of credentials |
|---|---|---|---|
| Paystack | Billing/payments (NGN) | **Confirmed provider — integration not yet built** | Not yet applicable |
| Opay | Billing/payments (NGN) | **Confirmed provider — integration not yet built** | Not yet applicable |
| Transactional email provider | Invitation delivery, notifications | Not yet selected | Not yet applicable |
| Auth/SSO provider | Future SSO/SAML support | Not yet selected — architecture reserves the slot, no provider chosen | Not yet applicable |

---

## 4. Features & Functionality

No feature has entered build yet. Below is the scoped module list with the architectural decisions that will govern each, not yet feature-level acceptance criteria (those will populate as each module is scoped in detail).

### Core platform (multi-tenancy, auth, RBAC) — **status: architecture decided, not started**
- **What it does:** Establishes the tenant boundary every other module depends on — Organization creation, User↔Organization membership, role-based permissions, workspace switching, invitations, audit logging.
- **Architecture decided:**
  - `Organization` ↔ `User` many-to-many through `Membership` (fields: role, status [`pending`/`active`/`suspended`], joined_at). One user may belong to multiple organizations.
  - Roles are per-organization, not global: Owner, Admin, Manager, Member, Viewer.
  - Permissions modeled as custom `Role`/`Permission`/`RolePermission` tables (resource:action pairs, e.g. `invoices:create`), seeded at migration time — not hardcoded role checks in view logic. django-guardian explicitly rejected as unnecessary overhead for this permission shape.
  - Active workspace context carried in short-lived session/access token, re-validated against DB membership on every request (not trusted from a stale token claim).
  - Invitations: signed token (not bare UUID), 7-day expiry; accepting an invite for an existing email creates the Membership in the same transaction as user creation if the user doesn't yet exist.
  - Audit log: append-only `AuditLog` table (tenant_id, actor_id, action, resource_type, resource_id, diff, ip_address, created_at). Explicitly prioritized for day-one build, not deferred to v2, because mid-market sales-assisted buyers raise it during procurement evaluation.
  - Internal admin/support tooling kept structurally separate from the tenant-facing permission system, to prevent a bug in internal tooling from becoming a tenant-isolation bug.
- **Known edge cases (anticipated, not yet confirmed):** user removed from org mid-session with a still-valid token; invitation accepted after org is deleted/suspended; last Owner attempting to leave an org; concurrent role changes during an active session.
- **Dependencies:** Everything else in the platform depends on this module existing first.
- **Status:** Not started.

### Customers, Leads, Projects, Tasks, Invoices, Documents, Notifications, Analytics
- **What they do:** Not yet scoped in detail — currently just named as the entity list under Organization in the original planning brief.
- **Status:** Not started. No user flows, acceptance criteria, or edge cases discussed yet for any of these individually.

### Established features
None — this is a pre-development project with no built features.

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
- **App list confirmed (2026-08-17):** `config` (settings/urls/asgi/wsgi, not an installed app), `accounts` (User, auth backend), `core` (Organization/Membership/Role/Permission/RolePermission/Invitation/AuditLog), `customers`, `leads` (incl. `converted_customer` FK), `projects` (incl. `Task` model nested here, not a standalone app), `invoices`, `billing` (Entitlement, Paystack/Opay webhooks, EntitlementService — kept separate from `invoices` since entitlements are plan-level not document-level), `platform_admin` (structurally isolated internal tooling). **Deferred, not scaffolded:** `documents`, `notifications`, `analytics` — no model/flow/acceptance criteria exist for these per the MVP decision (Section 1); creating empty apps for them now would invite scope drift. Naming convention: plural for domain-entity apps, singular for platform/capability apps. **Explicit note: MVP scope governs which modules ship in v1, not the engineering bar — every app above is built full production-grade (service-layer separation, full error handling, tests, RLS+ORM enforcement, real migrations), no reduced-quality "MVP-grade" code anywhere.**
- **State management (frontend):** Not yet decided — no Next.js work has started.
- **API design pattern:** Not yet decided beyond the authz layering described in Section 2/4 (AuthN → tenant validation → RBAC → object-level). REST vs. other API style not yet confirmed, though Django + DRF is implied by the stack and the owner's stated backend conventions (REST API design and integration is part of the owner's standard skillset).

---

## 8. Constraints & Guardrails

- **Never happen:** Cross-tenant data leakage, under any circumstance — this is the platform's core trust guarantee and the reason for the double-layered isolation enforcement.
- **Never happen:** Role/permission checks inlined ad hoc in view logic instead of routed through the centralized permission-check layer — this was explicitly called out as a source of permission drift to avoid.
- **Never happen:** Feature/tier gating checks scattered inline instead of centralized through the entitlement service — same rationale, avoiding drift as pricing/tiers change.
- **Regulatory context:** NDPA (Nigeria Data Protection Act) **confirmed in scope** `[confirmed]`. Data model must support: data minimization (no collection of fields not functionally required), a real deletion path (hard-delete capability for data-subject requests, not just soft-delete flags), data export/portability, and consent/source tracking on Customer and Lead records where data originates from a third party (e.g. purchased/imported lead lists). This governs Customer, Lead, and Invoice model design specifically, since those carry the PII/financial data.
- **Out of scope for current phase:** SSO/SAML implementation (architecture reserves the slot; no provider integration is being built yet). Schema-per-tenant or DB-per-tenant isolation (deferred unless the customer profile shifts toward enterprise/compliance-driven buyers).

---

## 9. Instructions to Future AI Models

- Check Section 0 before proceeding — this project is **pre-development**. Do not generate or reference application code, migrations, or a repository as if any exists; none does yet.
- The billing provider gap (Section 0 live blocker) is a hard dependency for the Invoices module and for entitlement enforcement — do not assume Stripe or invent a replacement provider. Confirm with the owner before proceeding on anything billing-adjacent.
- Do not silently fill Section 10's gaps with assumptions. Where a decision is needed to proceed (e.g., product name, per-entity relationships, NDPA scope), surface it explicitly or state the assumption being made and why before generating dependent work.
- The owner's stated build order is explicit: **Django backend first, complete, before any Next.js frontend work begins.** Do not front-run this by generating frontend code or scaffolding before the backend is confirmed complete.
- When scoping each of the eight product modules (Customers through Analytics), treat them as undefined until the owner specifies user flows and acceptance criteria — the entity list alone is not sufficient to build from.
- Apply the owner's standing engineering standard (Section 3 conventions) to all generated code: production-grade only, no placeholders, no truncation, full implementations.

---

## 10. Open Gaps, Assumptions & Superseded Facts

**Open gaps:**
- **Trademark/domain clearance for "Baseline"** — Name confirmed final for the build, but legal clearance (US trademark conflicts flagged, Nigeria/CAC name availability unchecked, domain availability unchecked) is owner's responsibility, not yet done as of confirmation. Not blocking code/architecture work. Needs confirmation once cleared, in case a rename becomes necessary.
- **Billing provider transaction split** — Paystack and Opay both confirmed, but which handles which payment method/transaction type is not yet decided. Not blocking for now; needed before the billing integration itself is built.
- **Per-module feature scope (Customers, Leads, Projects, Invoices)** — MVP boundary and all entity relationships confirmed. Detailed user flows and per-feature acceptance criteria still not defined for any of the four in-scope modules. Needs a scoping session per module before build.
- **Hosting/infra, CI/CD, environments** — Not yet discussed. No assumed default.
- **Design system** — Not yet defined; flagged in Section 5 as a genuine prerequisite gap, not a placeholder.
- **Localization requirements** — Not yet discussed, though relevant given NGN/Nigeria business context already surfaced via the billing gap.

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
