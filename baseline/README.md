# Baseline — Frontend

Next.js 15 (App Router) + React 19 + Tailwind v4 + TypeScript. See the
**root `README.md`** (one level up) for the full monorepo picture,
architecture notes shared with the backend, and the open scope question
this scaffold is currently waiting on.

## Setup

```bash
npm install
cp .env.example .env.local   # fill in EmailJS values once that account exists
npm run dev
```

Runs on `http://localhost:3000`. Expects the backend reachable at
`NEXT_PUBLIC_API_URL` (default `http://localhost:8000` — see `.env.local`).

Or via the monorepo's root `docker compose up`, which starts this
alongside Postgres/Redis/Django automatically.

## What's here

- `src/app/` — App Router pages. Currently just a placeholder home page —
  see root README for why real pages/design are pending a scope decision.
- `src/lib/api-client.ts` — typed fetch wrapper for the Baseline API
  (handles `Authorization` + `X-Organization-Id` headers).
- `src/lib/utils.ts` — `cn()` class-merging helper (shadcn/ui convention).
- `src/components/ui/` — UI primitives, currently just `Separator`
  (matches the one Radix dependency in `package.json`).

## Scripts

- `npm run dev` — dev server (Turbopack)
- `npm run build` — production build
- `npm run start` — serve a production build
- `npm run lint` — ESLint

## Verified

`npm ci`, `npm run build`, and `npm run lint` all pass clean against the
committed `package-lock.json` — this was actually run, not just checked
for internal consistency (unlike parts of the backend that need a live
Postgres/Redis instance to verify — see root README).
