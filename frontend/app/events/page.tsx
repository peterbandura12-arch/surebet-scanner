"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowUpRight, Search } from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  EmptyState,
  ErrorState,
  Input,
  Label,
  Select,
  SkeletonRows,
} from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { backend } from "@/lib/api";
import { fmtTime } from "@/lib/format";

export default function EventsPage() {
  const [sport, setSport] = useState("");
  const [status, setStatus] = useState("scheduled");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const { data: sports } = useApi(() => backend.sports(), []);
  const { data, loading, error } = useApi(
    () =>
      backend.events({
        sport,
        status,
        search,
        limit: pageSize,
        offset: page * pageSize,
      }),
    [sport, status, search, page]
  );

  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title="Monitored events"
          subtitle={`${total} events in the simulated demo universe`}
        />
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <div>
            <Label>Sport</Label>
            <Select value={sport} onChange={(e) => { setSport(e.target.value); setPage(0); }}>
              <option value="">All</option>
              {sports?.map((s) => (
                <option key={s.key} value={s.key}>{s.name}</option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Status</Label>
            <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(0); }}>
              <option value="">Any</option>
              <option value="scheduled">Scheduled</option>
              <option value="live">Live</option>
              <option value="finished">Finished</option>
            </Select>
          </div>
          <div className="sm:col-span-2">
            <Label>Search</Label>
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
              <Input
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                placeholder="Team name, e.g. Arsenal"
                className="pl-7"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {error ? <ErrorState message={error} /> : null}

      <Card>
        {loading && !data ? (
          <SkeletonRows rows={10} />
        ) : data?.results.length ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-[13px]">
                <thead>
                  <tr className="border-b border-line text-[11px] uppercase tracking-wider text-muted">
                    <th className="px-4 py-2 font-medium">Event</th>
                    <th className="px-3 py-2 font-medium">Sport</th>
                    <th className="px-3 py-2 font-medium">League</th>
                    <th className="px-3 py-2 font-medium">Country</th>
                    <th className="px-3 py-2 font-medium">Kick-off</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((e) => (
                    <tr key={e.id} className="border-b border-line/60 transition-colors hover:bg-hover/60">
                      <td className="px-4 py-2.5 font-medium">{e.name}</td>
                      <td className="px-3 py-2.5 text-dim">{e.sport.replace(/_/g, " ")}</td>
                      <td className="px-3 py-2.5 text-dim">{e.league || "–"}</td>
                      <td className="px-3 py-2.5 text-muted">{e.country || "–"}</td>
                      <td className="px-3 py-2.5 text-[12px] text-muted">{fmtTime(e.start_time)}</td>
                      <td className="px-3 py-2.5">
                        <Badge variant={e.status === "scheduled" ? "positive" : "outline"}>
                          {e.status}
                        </Badge>
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <Link
                          href={`/comparison?event=${e.id}`}
                          className="inline-flex items-center gap-1 text-xs text-accent/90 hover:text-accent"
                        >
                          Odds comparison <ArrowUpRight size={12} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between border-t border-line px-4 py-2.5 text-xs text-muted">
              <span>Page {page + 1} of {pages}</span>
              <div className="flex gap-2">
                <button className="rounded border border-line px-2 py-1 disabled:opacity-40 hover:bg-hover" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>Prev</button>
                <button className="rounded border border-line px-2 py-1 disabled:opacity-40 hover:bg-hover" disabled={page + 1 >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
              </div>
            </div>
          </>
        ) : (
          <EmptyState message="No events match these filters" />
        )}
      </Card>
    </div>
  );
}
