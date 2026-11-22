"use client";

import { ExternalLink, Info } from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  ErrorState,
  SkeletonRows,
} from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { backend } from "@/lib/api";
import { fmtAgo } from "@/lib/format";

export default function SourcesPage() {
  const { data, loading, error } = useApi(() => backend.sources(), []);
  const { data: books } = useApi(() => backend.bookmakers(), []);

  return (
    <div className="space-y-4">
      <ErrorStateBanner />
      <Card>
        <CardHeader
          title="Data sources"
          subtitle="Abstract provider architecture — demo provider active, real providers pending credentials"
        />
        {loading && !data ? (
          <SkeletonRows rows={4} />
        ) : error ? (
          <CardContent><ErrorState message={error} /></CardContent>
        ) : (
          <CardContent className="space-y-3">
            {data?.map((s) => (
              <div
                key={s.key}
                className="flex flex-col gap-2 rounded-md border border-line bg-raised p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-[13px] font-semibold text-bright">{s.name}</p>
                    <Badge variant={s.type === "demo" ? "warn" : "outline"}>
                      {s.type}
                    </Badge>
                    <Badge variant={s.status === "active" ? "positive" : "outline"}>
                      {s.status}
                    </Badge>
                    {s.requires_api_key ? (
                      <Badge variant="outline">API key required</Badge>
                    ) : null}
                  </div>
                  {s.note ? (
                    <p className="mt-1 text-[12px] text-muted">{s.note}</p>
                  ) : null}
                  {s.last_error ? (
                    <p className="mt-1 text-[12px] text-risk">Last error: {s.last_error}</p>
                  ) : null}
                </div>
                <div className="shrink-0 text-right text-[11px] text-muted">
                  <p>Last sync: {fmtAgo(s.last_sync_at)}</p>
                  {s.docs_url ? (
                    <a
                      href={s.docs_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-flex items-center gap-1 text-accent hover:underline"
                    >
                      Docs <ExternalLink size={11} />
                    </a>
                  ) : null}
                </div>
              </div>
            ))}
            <p className="flex items-start gap-2 rounded-md border border-line px-3 py-2 text-[11px] leading-relaxed text-muted">
              <Info size={13} className="mt-0.5 shrink-0" />
              Real providers (The Odds API, Sportradar, API-SPORTS) activate
              only when their key environment variables are configured. When a
              real source fails or lacks a key the system keeps returning only
              clearly-labelled simulated data — it never silently substitutes
              fake data for real feeds.
            </p>
          </CardContent>
        )}
      </Card>

      <Card>
        <CardHeader title={`Simulated bookmakers (${books?.length ?? 0})`} subtitle="Each demo bookmaker applies its own margin model to generate distinct odds" />
        <CardContent>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {books?.map((b) => (
              <div key={b.key} className="flex items-center justify-between rounded-md border border-line bg-raised px-3 py-2">
                <span className="text-[13px]">{b.name}</span>
                <Badge variant={b.active ? "positive" : "outline"}>
                  {b.active ? "active" : "inactive"}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ErrorStateBanner() {
  return null;
}
