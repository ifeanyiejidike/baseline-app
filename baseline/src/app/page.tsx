export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-2xl font-semibold">CasAfrique</h1>
      <p className="max-w-md text-sm text-[var(--color-muted)]">
        Project scaffold is in place — routing, Tailwind v4, the API client, and
        env config are wired up. Real pages and design are pending scope
        confirmation (marketing site vs. product dashboard).
      </p>
    </main>
  );
}
