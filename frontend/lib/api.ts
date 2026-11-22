import type {
  AlertRule,
  Bookmaker,
  CalculatedResult,
  DashboardData,
  EventDetail,
  EventItem,
  Notification,
  Opportunity,
  PaperData,
  PaperPosition,
  SourceItem,
  SportInfo,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "Backend unreachable. Is the API server running?");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const get = <T,>(path: string) => api<T>(path);
export const post = <T,>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
export const patch = <T,>(path: string, body: unknown) =>
  api<T>(path, { method: "PATCH", body: JSON.stringify(body) });

export const backend = {
  health: () =>
    get<{
      status: string;
      version: string;
      demo_mode: boolean;
      database: string;
      cache: string;
      simulated_data: boolean;
    }>("/api/health"),
  sports: () => get<SportInfo[]>("/api/sports"),
  sportMarkets: (sport: string) =>
    get<{ key: string; name: string; outcomes: string[] }[]>(
      `/api/sports/${sport}/markets`
    ),
  bookmakers: () => get<Bookmaker[]>("/api/bookmakers"),
  sources: () => get<SourceItem[]>("/api/sources"),
  settings: () =>
    get<Record<string, { value: string; description: string }>>("/api/settings"),
  putSetting: (key: string, value: string) =>
    api<{ key: string; value: string }>(
      `/api/settings?key=${encodeURIComponent(key)}&value=${encodeURIComponent(value)}`,
      { method: "PUT" }
    ),

  dashboard: () => get<DashboardData>("/api/dashboard"),
  analytics: {
    opportunitiesOverTime: (days: number, sport?: string) =>
      get<{ date: string; count: number; avg_roi: number | null }[]>(
        `/api/analytics/opportunities-over-time?days=${days}${sport ? `&sport=${sport}` : ""}`
      ),
    roiDistribution: () =>
      get<{ label: string; count: number }[]>("/api/analytics/roi-distribution"),
    roiBySport: () =>
      get<{ sport: string; count: number; avg_roi: number }[]>(
        "/api/analytics/roi-by-sport"
      ),
    roiByBookmaker: () =>
      get<{ bookmaker: string; leg_count: number; avg_best_odds: number }[]>(
        "/api/analytics/roi-by-bookmaker"
      ),
    lifetime: () =>
      get<{ count: number; avg_seconds: number | null; median_seconds: number | null }>(
        "/api/analytics/opportunity-lifetime"
      ),
    detectedVsExpired: (days = 14) =>
      get<{ status: string; count: number }[]>(
        `/api/analytics/detected-vs-expired?days=${days}`
      ),
    portfolioCurve: () =>
      get<{ ts: string; profit: number }[]>("/api/analytics/portfolio-curve"),
  },

  scanner: (params: Record<string, string | number | undefined>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    });
    return get<{ simulated: boolean; count: number; results: Opportunity[] }>(
      `/api/scanner?${qs.toString()}`
    );
  },
  opportunityHistory: (params: {
    status?: string;
    sport?: string;
    days?: number;
    sort?: string;
    limit?: number;
  }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    });
    return get<{ count: number; results: Opportunity[] }>(
      `/api/opportunities?${qs.toString()}`
    );
  },
  opportunity: (id: string) => get<Opportunity>(`/api/opportunities/${id}`),

  events: (params: {
    sport?: string;
    league?: string;
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    });
    return get<{ total: number; results: EventItem[] }>(
      `/api/events?${qs.toString()}`
    );
  },
  event: (id: string) => get<EventDetail>(`/api/events/${id}`),
  eventMovements: (id: string, limit = 100) =>
    get<{
      simulated: boolean;
      movements: {
        bookmaker: string;
        market: string;
        outcome: string;
        from_odds: number | null;
        to_odds: number;
        captured_at: string | null;
      }[];
    }>(`/api/events/${id}/odds-movements?limit=${limit}`),
  matchingReview: () =>
    get<{
      results: {
        match_id: string;
        provider: string;
        event_id: string | null;
        confidence: number;
        manual: boolean;
        signals: Record<string, unknown>;
      }[];
    }>("/api/matching/review"),
  resolveMatch: (
    matchId: string,
    action: "accept" | "reject",
    eventId?: string
  ) =>
    patch<{ id: string; confidence: number }>(`/api/matching/${matchId}`, {
      action,
      event_id: eventId,
    }),

  calc: (body: {
    odds: { outcome: string; odds: number }[];
    bankroll: number;
    fee_pct?: number;
    stake_step?: number;
    rounding_mode?: string;
  }) => post<CalculatedResult>("/api/calc", body),

  paper: () => get<PaperData>("/api/paper/portfolio"),
  createPortfolio: (body: {
    name: string;
    starting_bankroll: number;
    currency?: string;
  }) => post<{ id: string }>("/api/paper/portfolios", body),
  placePosition: (body: {
    portfolio_id: string;
    opportunity_id: string;
    total_stake: number;
  }) => post<PaperPosition>("/api/paper/positions", body),
  settle: () =>
    post<{ simulated: boolean; settled: unknown[] }>("/api/paper/settle"),

  alertRules: () => get<AlertRule[]>("/api/alerts/rules"),
  createAlertRule: (body: Partial<AlertRule>) =>
    post<AlertRule>("/api/alerts/rules", body),
  updateAlertRule: (id: string, body: Partial<AlertRule>) =>
    patch<AlertRule>(`/api/alerts/rules/${id}`, body),
  notifications: (limit = 100) =>
    get<{ count: number; unread: number; results: Notification[] }>(
      `/api/alerts/notifications?limit=${limit}`
    ),
  markRead: (id: string) =>
    post<{ id: string }>(`/api/alerts/notifications/${id}/read`),
  markAllRead: () => post<{ marked: number }>("/api/alerts/notifications/read-all"),
};
