# Baseline — Frontend

![Next.js](https://img.shields.io/badge/Next.js-15-000000)
![React](https://img.shields.io/badge/React-19-61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6)
![Tailwind](https://img.shields.io/badge/Tailwind-v4-06B6D4)
![Status](https://img.shields.io/badge/status-scaffold--only-orange)

Next.js 15 (App Router) frontend for **Baseline**. Part of the
[`baseline_app`](../README.md) monorepo — see the root README for the
cross-cutting picture.

> **Status: technical scaffold only.** Routing, the API client, and env
> configuration are wired up and verified (see [Verification](#verification)).
> No product pages, copy, or visual design exist yet — see
> [Open Question: Scope](#open-question-scope) for why, before adding any.

---

## Table of Contents

- [Open Question: Scope](#open-question-scope)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [Scripts](#scripts)
- [Verification](#verification)
- [Design System](#design-system)
- [Contributing](#contributing)

---

## Open Question: Scope

This project's dependency set is a real signal worth taking seriously
before writing pages:

| Present | Absent |
|---|---|
| `@emailjs/browser` | Any data-fetching library (react-query, SWR) |
| One Radix primitive (`react-separator`) | A table/data-grid library |
| `react-hook-form` + `zod` | A charting library |
| — | Any auth/session-management library |
| — | A toast/dialog/modal system beyond one primitive |

This reads like a **marketing or lead-capture site** — a form that emails
via EmailJS rather than hitting a backend — not a dashboard for an
11-app, 40+-endpoint multi-tenant CRM. Building CRUD pages for
Customers/Leads/Projects/Invoices under the wrong assumption would mean
adding a full data-fetching/table/chart/auth stack retroactively and
likely discarding early page work.

**Until this is resolved, only the technical scaffold is built** —
routing, styling setup, and an API client that works either way. See the
root README's [Frontend Scope](../README.md#frontend-scope-currently-undecided)
section.

---

## Tech Stack

| Concern | Choice |
|---|---|
| Framework | Next.js 15, App Router, Turbopack dev server |
| UI runtime | React 19 |
| Styling | Tailwind CSS v4 (`@theme` directive, no `tailwind.config.js`) |
| Type safety | TypeScript 5, strict mode |
| Forms | `react-hook-form` + `zod` resolvers |
| Class composition | `clsx` + `tailwind-merge` via a `cn()` helper (shadcn/ui convention) |
| UI primitives | Radix UI (`react-separator` currently; more added as needed) |
| Icons | `lucide-react` |
| Linting | ESLint 9 (flat config), `eslint-config-next` |

---

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx        # root layout — placeholder metadata
│   │   ├── page.tsx           # placeholder home page
│   │   └── globals.css         # Tailwind v4 entry + neutral theme tokens
│   ├── components/
│   │   └── ui/
│   │       └── separator.tsx    # shadcn-pattern primitive
│   └── lib/
│       ├── utils.ts              # cn() class-merge helper
│       └── api-client.ts          # typed fetch wrapper for the Baseline API
├── public/                        # static assets (currently empty)
├── Dockerfile.dev                 # local-dev only — see note below
├── next.config.ts
├── tsconfig.json
├── postcss.config.mjs
├── eslint.config.mjs
├── package.json
└── .env / .env.local / .env.example / .env.production
```

**`Dockerfile.dev` is local-development convenience only.** Production
deploy is expected via Vercel (see the monorepo `.gitignore`'s `.vercel`
entry) — this image is not a production build artifact.

---

## Setup

```bash
npm install
cp .env.example .env.local   # fill in EmailJS values once that account exists
npm run dev
```

Runs on `http://localhost:3000`. Expects the backend reachable at
`NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

Or via the monorepo's root `docker compose up`, which starts this
alongside PostgreSQL, Redis, and Django automatically.

---

## Environment Variables

Full reference — see `.env.example` for the always-current committed
template. Next.js env-file precedence (highest to lowest):
`.env.production` (prod builds only) → `.env.local` → `.env`.

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Recommended | Base URL of the Baseline API (`http://localhost:8000` in dev) |
| `NEXT_PUBLIC_SITE_URL` | Recommended | This site's own public URL — canonical links, OG tags |
| `NEXT_PUBLIC_SITE_NAME` | No | Display name, currently set in `.env` |
| `NEXT_PUBLIC_EMAILJS_SERVICE_ID` | For contact-form functionality | From your EmailJS dashboard |
| `NEXT_PUBLIC_EMAILJS_TEMPLATE_ID` | For contact-form functionality | From your EmailJS dashboard |
| `NEXT_PUBLIC_EMAILJS_PUBLIC_KEY` | For contact-form functionality | Public by EmailJS's own design — safe to expose client-side |

All variables are `NEXT_PUBLIC_*` — nothing server-only is needed yet
since there's no server-side logic beyond the static scaffold.

---

## Scripts

| Command | Effect |
|---|---|
| `npm run dev` | Dev server with Turbopack |
| `npm run build` | Production build |
| `npm run start` | Serve a production build |
| `npm run lint` | ESLint |

---

## Verification

Unlike parts of the backend (which need a live Postgres/Redis instance
this environment couldn't provide), **everything claimed about this
frontend has actually been executed, not just checked for internal
consistency:**

| Check | Result |
|---|---|
| `npm ci` against the committed `package-lock.json` | ✅ Passes, 355 packages resolved |
| `npm run build` | ✅ Production build succeeds |
| `npm run lint` | ✅ Zero warnings/errors |
| Env file precedence (`.env` / `.env.local` / `.env.production`) | ✅ Confirmed via build output showing correct load order |

---

## Design System

No design system exists yet. `src/app/globals.css` contains **functional
neutral tokens only** (background/foreground/border/muted colors, a
system font stack) — enough for the scaffold to be legible, not a design
decision. A real palette, type scale, and component library should be
derived from a concrete brief (subject, audience, the page's job) once
[scope](#open-question-scope) is resolved — not built speculatively ahead
of that.

---

## Contributing

See the root README's [Contributing](../README.md#contributing) section.
Frontend-specific: run `npm run build && npm run lint` before opening a
PR — there is no CI to catch it for you yet.