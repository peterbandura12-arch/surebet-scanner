export type Leg = {
  outcome: string;
  odds: number;
  bookmaker: string;
  captured_at: string;
  age_seconds?: number;
};

export type Opportunity = {
  id?: string;
  event_id: string;
  event_name: string;
  league: string;
  sport: string;
  market_key: string;
  market_name: string;
  start_time: string | null;
  roi_pct: number;
  sum_inverse: number;
  num_outcomes: number;
  legs: Leg[];
  stale: boolean;
  validation_notes?: string[];
  best_odds?: number;
  detected_at?: string | null;
  status?: string;
  expires_at?: string | null;
  estimated?: {
    bankroll: number;
    total_stake: number;
    stakes: number[];
    payout: number;
    profit: number;
  };
  snapshots?: { roi_pct: number; captured_at: string }[];
};

export type DashboardTotals = {
  opportunities_total: number;
  opportunities_active: number;
  avg_active_roi_pct: number;
  max_roi_pct: number;
  monitored_events: number;
  monitored_sports: number;
  virtual_capital: number;
  open_positions: number;
};

export type DashboardData = {
  demo_mode: boolean;
  totals: DashboardTotals;
  by_sport: { sport: string; count: number }[];
  by_bookmaker: { bookmaker: string; count: number }[];
  recent_opportunities: Opportunity[];
  recent_movements: {
    event_id: string;
    bookmaker: string;
    market: string;
    outcome: string;
    from_odds: number | null;
    to_odds: number;
    captured_at: string | null;
  }[];
};

export type EventItem = {
  id: string;
  name: string;
  sport: string;
  league: string;
  country: string;
  home: string;
  away: string;
  start_time: string | null;
  status: string;
};

export type EventDetail = EventItem & {
  markets: {
    market_key: string;
    bookmakers: Record<
      string,
      { bookmaker: string; odds: Record<string, { value: number; captured_at: string | null }> }
    >;
  }[];
  matches: {
    id: string;
    provider: string;
    external_event_id: string;
    confidence: number;
    method: string;
    manual: boolean;
    signals: Record<string, unknown>;
  }[];
};

export type SportInfo = { key: string; name: string; enabled: boolean };
export type Bookmaker = { key: string; name: string; is_demo: boolean; active: boolean };

export type SourceItem = {
  key: string;
  name: string;
  type: "demo" | "real";
  status: string;
  enabled: boolean;
  requires_api_key: boolean;
  docs_url: string | null;
  note: string | null;
  last_sync_at: string | null;
  last_error: string | null;
};

export type CalculatedResult = {
  is_arbitrage: boolean;
  sum_inverse: number;
  roi_pct: number;
  legs: { outcome: string; odds: number; stake: number; payout: number }[];
  total_stake: number;
  guaranteed_payout: number;
  guaranteed_profit: number;
  notes?: string[];
  [key: string]: unknown;
};

export type PaperPosition = {
  id: string;
  portfolio_id: string;
  event_name: string;
  market_key: string;
  market_name: string;
  sport: string;
  legs: { outcome: string; odds: number; stake: number }[];
  total_stake: number;
  status: string;
  payout: number | null;
  profit: number | null;
  simulated_result: string | null;
  placed_at: string | null;
  settled_at: string | null;
};

export type PaperData = {
  simulated: boolean;
  portfolio: {
    id: string;
    name: string;
    currency: string;
    starting_bankroll: number;
    balance: number;
    is_simulated: boolean;
  };
  summary: {
    open_positions: number;
    settled_positions: number;
    won: number;
    lost: number;
    total_profit: number;
    total_staked: number;
    roi_pct: number;
  };
  positions: PaperPosition[];
  disclaimer: string;
};

export type AlertRule = {
  id: string;
  name: string;
  event_type: string;
  threshold_roi: number | null;
  sport_key: string | null;
  channel: string;
  enabled: boolean;
};

export type Notification = {
  id: string;
  event_type: string;
  title: string;
  body: string;
  read: boolean;
  created_at: string | null;
};

export type ScanUpdate = {
  type: string;
  new: Opportunity[];
  updated: Opportunity[];
  expired: Opportunity[];
  stats?: Record<string, number>;
  simulated: boolean;
  ts?: string;
};
