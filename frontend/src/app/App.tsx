import { useEffect, useState } from "react";

type ConnectionState = "checking" | "connected" | "unavailable";

type HealthResponse = {
  status: string;
  service: string;
  api_version: string;
};

export default function App() {
  const [connection, setConnection] = useState<ConnectionState>("checking");

  useEffect(() => {
    const controller = new AbortController();

    async function checkBackend() {
      try {
        const response = await fetch("/api/health", { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`Health check returned ${response.status}`);
        }

        const health = (await response.json()) as HealthResponse;
        if (
          health.status !== "ok" ||
          health.service !== "running-coach" ||
          health.api_version !== "1"
        ) {
          throw new Error("Unexpected health response");
        }

        setConnection("connected");
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setConnection("unavailable");
        }
      }
    }

    void checkBackend();
    return () => controller.abort();
  }, []);

  const statusText = {
    checking: "Checking backend…",
    connected: "Backend connected",
    unavailable: "Backend unavailable",
  }[connection];

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f4f7f2] px-6 text-slate-950">
      <section className="w-full max-w-2xl border-l-4 border-emerald-700 py-3 pl-7">
        <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-[0.22em] text-emerald-800">
          Local application
        </p>
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">Running Coach is</h1>
        <p aria-live="polite" className="mt-6 flex items-center gap-2 text-sm text-slate-600">
          <span
            aria-hidden="true"
            className={`h-2.5 w-2.5 rounded-full ${
              connection === "connected"
                ? "bg-emerald-600"
                : connection === "unavailable"
                  ? "bg-rose-600"
                  : "bg-amber-500"
            }`}
          />
          {statusText}
        </p>
      </section>
    </main>
  );
}
