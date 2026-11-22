"use client";

import { useMemo, useState } from "react";
import { BellRing, CheckCheck, Plus, Radio, Trash2 } from "lucide-react";
import {
  Badge,
  Button,
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
import { fmtAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

const EVENT_TYPES = [
  { value: "new_opportunity", label: "New opportunity detected" },
  { value: "roi_threshold", label: "ROI above threshold" },
  { value: "opportunity_expired", label: "Opportunity expired" },
  { value: "odds_changed", label: "Odds changed" },
  { value: "source_unavailable", label: "Data source unavailable" },
];

export default function AlertsPage() {
  const { data: rules, loading: loadingRules, error: rulesError, reload: reloadRules } =
    useApi(() => backend.alertRules(), []);
  const { data: notifs, loading: loadingNotifs, error: notifError, reload: reloadNotifs } =
    useApi(() => backend.notifications(100), [], { poll: 30000 });
  const { data: sports } = useApi(() => backend.sports(), []);

  const [name, setName] = useState("");
  const [eventType, setEventType] = useState("roi_threshold");
  const [threshold, setThreshold] = useState("2");
  const [sportKey, setSportKey] = useState("");
  const [channel, setChannel] = useState("in_app");
  const [msg, setMsg] = useState<string | null>(null);

  const unread = notifs?.unread ?? 0;
  const canCreate = useMemo(() => name.trim().length >= 1, [name]);

  const create = async () => {
    setMsg(null);
    try {
      await backend.createAlertRule({
        name: name.trim(),
        event_type: eventType,
        threshold_roi: eventType === "roi_threshold" ? parseFloat(threshold) : null,
        sport_key: sportKey || null,
        channel,
      });
      setName("");
      reloadRules();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Could not create rule");
    }
  };

  const toggle = async (id: string, enabled: boolean) => {
    await backend.updateAlertRule(id, { enabled: !enabled });
    reloadRules();
  };

  const markAll = async () => {
    await backend.markAllRead();
    reloadNotifs();
  };

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-1">
        <Card>
          <CardHeader title="Create alert rule" subtitle="In-app notifications are implemented; Telegram is prepared but disabled (no credentials required)." />
          <CardContent className="space-y-3">
            <div>
              <Label>Rule name</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. High ROI football" />
            </div>
            <div>
              <Label>Event type</Label>
              <Select value={eventType} onChange={(e) => setEventType(e.target.value)}>
                {EVENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </Select>
            </div>
            {eventType === "roi_threshold" ? (
              <div>
                <Label>ROI threshold %</Label>
                <Input className="tabular" type="number" step="0.1" value={threshold} onChange={(e) => setThreshold(e.target.value)} />
              </div>
            ) : null}
            <div>
              <Label>Sport (optional)</Label>
              <Select value={sportKey} onChange={(e) => setSportKey(e.target.value)}>
                <option value="">All sports</option>
                {sports?.map((s) => (
                  <option key={s.key} value={s.key}>{s.name}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label>Channel</Label>
              <Select value={channel} onChange={(e) => setChannel(e.target.value)}>
                <option value="in_app">In-app notification</option>
                <option value="telegram_future">Telegram (future — inert stub)</option>
              </Select>
            </div>
            <Button variant="primary" className="w-full" disabled={!canCreate} onClick={create}>
              <Plus size={13} /> Create rule
            </Button>
            {msg ? <ErrorState message={msg} /> : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader
            title={`Alert rules (${rules?.length ?? 0})`}
            right={
              <Radio size={13} className="text-muted" />
            }
          />
          {loadingRules && !rules ? (
            <SkeletonRows rows={3} />
          ) : rulesError ? (
            <CardContent><ErrorState message={rulesError} /></CardContent>
          ) : rules?.length ? (
            <CardContent className="space-y-2">
              {rules.map((r) => (
                <div key={r.id} className="flex items-center justify-between gap-2 rounded-md border border-line bg-raised px-3 py-2">
                  <div className="min-w-0">
                    <p className="truncate text-[13px] font-medium">{r.name}</p>
                    <p className="text-[11px] text-muted">
                      {EVENT_TYPES.find((t) => t.value === r.event_type)?.label ?? r.event_type}
                      {r.threshold_roi !== null ? ` · ROI ≥ ${r.threshold_roi}%` : ""}
                      {r.sport_key ? ` · ${r.sport_key}` : ""}
                      {" · "}
                      {r.channel === "in_app" ? "in-app" : "telegram (stub)"}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    <Badge variant={r.enabled ? "positive" : "outline"}>
                      {r.enabled ? "on" : "off"}
                    </Badge>
                    <button
                      className="rounded p-1 text-muted hover:bg-hover hover:text-bright"
                      title={r.enabled ? "Disable" : "Enable"}
                      onClick={() => toggle(r.id, r.enabled)}
                    >
                      {r.enabled ? <BellRing size={13} /> : <Trash2 size={13} />}
                    </button>
                  </div>
                </div>
              ))}
            </CardContent>
          ) : (
            <EmptyState message="No alert rules configured" />
          )}
        </Card>
      </div>

      <Card className="lg:col-span-2">
        <CardHeader
          title={
            <span className="inline-flex items-center gap-2">
              Notifications
              {unread > 0 ? <Badge variant="positive">{unread} unread</Badge> : null}
            </span>
          }
          subtitle="Generated by the background scanner against the simulated feed"
          right={
            <Button size="sm" onClick={markAll} disabled={!unread}>
              <CheckCheck size={12} /> Mark all read
            </Button>
          }
        />
        {loadingNotifs && !notifs ? (
          <SkeletonRows rows={6} />
        ) : notifError ? (
          <CardContent><ErrorState message={notifError} /></CardContent>
        ) : notifs?.results.length ? (
          <div className="max-h-[640px] divide-y divide-line overflow-y-auto">
            {notifs.results.map((n) => (
              <button
                key={n.id}
                className={cn(
                  "block w-full px-4 py-3 text-left transition-colors hover:bg-hover/60",
                  !n.read && "bg-accent-dim/30"
                )}
                onClick={() => {
                  if (!n.read) backend.markRead(n.id).then(reloadNotifs);
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[13px] font-medium text-bright">{n.title}</p>
                    <p className="mt-0.5 text-[12px] text-muted">{n.body}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-[10px] text-muted">{fmtAgo(n.created_at)}</p>
                    {!n.read ? (
                      <Badge variant="positive" className="mt-1">new</Badge>
                    ) : null}
                  </div>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <EmptyState
            message="No notifications yet"
            hint="Rules fire when the scanner detects matching opportunities in the simulated feed."
          />
        )}
      </Card>
    </div>
  );
}
