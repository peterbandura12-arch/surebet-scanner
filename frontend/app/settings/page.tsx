"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  Disclaimer,
  ErrorState,
  Input,
  Label,
  SkeletonRows,
} from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { backend, ApiError } from "@/lib/api";

const EDITABLE = new Set([
  "min_roi_pct",
  "odds_max_age_seconds",
  "feed_tick_seconds",
]);

export default function SettingsPage() {
  const { data, loading, error, reload } = useApi(() => backend.settings(), []);
  const { data: health } = useApi(() => backend.health(), [], { poll: 30000 });
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setDrafts(Object.fromEntries(Object.entries(data).map(([k, v]) => [k, String(v.value)])));
    }
  }, [data]);

  const save = async (key: string) => {
    setSaved(null);
    setSaveError(null);
    try {
      const v: string | number = /^\d+(\.\d+)?$/.test(drafts[key])
        ? Number(drafts[key])
        : drafts[key];
      await backend.putSetting(key, String(v));
      setSaved(key);
      reload();
    } catch (e) {
      setSaveError(e instanceof ApiError ? e.message : "Save failed");
    }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader
          title="System settings"
          subtitle="Stored in the database; the background feed reads them on the next tick"
        />
        {loading && !data ? (
          <SkeletonRows rows={6} />
        ) : error ? (
          <CardContent><ErrorState message={error} /></CardContent>
        ) : (
          <CardContent className="space-y-3">
            {Object.entries(data ?? {}).map(([key, setting]) => (
              <div key={key} className="rounded-md border border-line bg-raised p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[13px] font-medium text-bright">{key}</p>
                    <p className="text-[11px] text-muted">{setting.description}</p>
                  </div>
                  {EDITABLE.has(key) ? (
                    <div className="flex shrink-0 items-center gap-1.5">
                      <Input
                        className="tabular w-24"
                        value={drafts[key] ?? ""}
                        onChange={(e) => setDrafts((d) => ({ ...d, [key]: e.target.value }))}
                      />
                      <button
                        className="rounded border border-accent/40 bg-accent-dim px-2 py-1 text-[11px] font-semibold text-accent hover:bg-accent hover:text-[#04130c]"
                        onClick={() => save(key)}
                      >
                        Save
                      </button>
                    </div>
                  ) : (
                    <span className="tabular shrink-0 text-[13px] text-dim">
                      {String(setting.value)}
                    </span>
                  )}
                </div>
                {saved === key ? (
                  <p className="mt-1 text-[11px] text-accent">Saved.</p>
                ) : null}
              </div>
            ))}
            {saveError ? <ErrorState message={saveError} /> : null}
          </CardContent>
        )}
      </Card>

      <div className="space-y-4">
        <Card>
          <CardHeader title="System health" subtitle="Live backend diagnostics" />
          <CardContent className="space-y-2 text-[13px]">
            <Row label="Status" value={health?.status ?? "…"} ok={health?.status === "ok"} />
            <Row label="Database" value={health?.database ?? "…"} ok={health?.database === "connected"} />
            <Row label="Cache" value={health?.cache ?? "…"} ok />
            <Row
              label="Demo mode"
              value={health?.demo_mode ? "enabled" : "disabled"}
              ok={health?.demo_mode}
            />
            <Row label="Simulated data" value={health?.simulated_data ? "yes" : "no"} ok={health?.simulated_data} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Deployment notes" subtitle="Environment configuration reference" />
          <CardContent>
            <ul className="space-y-2 text-[12px] leading-relaxed text-muted">
              <li>
                <span className="text-dim">DATABASE_URL</span> — SQLAlchemy
                connection string. SQLite works out of the box; use PostgreSQL in
                the provided docker-compose stack.
              </li>
              <li>
                <span className="text-dim">REDIS_URL</span> — optional; when unset
                an in-process cache is used.
              </li>
              <li>
                <span className="text-dim">THEODDSAPI_KEY</span> — optional key for
                The Odds API. Leaving it empty keeps the platform on simulated
                demo feeds only.
              </li>
              <li>
                <span className="text-dim">FEED_TICK_SECONDS</span> — background
                scan interval for the simulated feeds.
              </li>
            </ul>
          </CardContent>
        </Card>

        <Disclaimer>
          DEMO MODE is enforced in this build: real-money betting and automated
          bet placement do not exist in the codebase. External providers must be
          explicitly enabled with credentials before any real data enters the
          system.
        </Disclaimer>
      </div>
    </div>
  );
}

function Row({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-line bg-raised px-3 py-2">
      <span className="text-muted">{label}</span>
      <span className={ok === false ? "text-risk" : ok ? "text-accent" : "text-dim"}>
        {value}
      </span>
    </div>
  );
}
