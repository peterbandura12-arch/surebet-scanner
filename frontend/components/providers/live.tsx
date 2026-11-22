"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { Opportunity, ScanUpdate } from "@/lib/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/live";

type LiveContextValue = {
  connected: boolean;
  lastUpdate: ScanUpdate | null;
  lastUpdateAt: number | null;
  recentNew: Opportunity[];
};

const LiveContext = createContext<LiveContextValue>({
  connected: false,
  lastUpdate: null,
  lastUpdateAt: null,
  recentNew: [],
});

export function useLive() {
  return useContext(LiveContext);
}

export function LiveProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<ScanUpdate | null>(null);
  const [lastUpdateAt, setLastUpdateAt] = useState<number | null>(null);
  const [recentNew, setRecentNew] = useState<Opportunity[]>([]);
  const retry = useRef(0);

  const handle = useCallback((msg: ScanUpdate) => {
    if (msg.type === "scan_update") {
      setLastUpdate(msg);
      setLastUpdateAt(Date.now());
      if (msg.new?.length) {
        setRecentNew((prev) => [...msg.new, ...prev].slice(0, 20));
      }
      window.dispatchEvent(new CustomEvent("surebet:scan_update"));
    }
  }, []);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;
    let timer: ReturnType<typeof setTimeout>;

    const scheduleRetry = () => {
      retry.current += 1;
      const delay = Math.min(1000 * retry.current, 10000);
      timer = setTimeout(connect, delay);
    };

    const connect = () => {
      if (closed) return;
      try {
        ws = new WebSocket(WS_URL);
      } catch {
        scheduleRetry();
        return;
      }
      ws.onopen = () => {
        retry.current = 0;
        setConnected(true);
      };
      ws.onmessage = (ev) => {
        try {
          handle(JSON.parse(ev.data) as ScanUpdate);
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = () => {
        setConnected(false);
        scheduleRetry();
      };
      ws.onerror = () => ws?.close();
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      ws?.close();
    };
  }, [handle]);

  return (
    <LiveContext.Provider value={{ connected, lastUpdate, lastUpdateAt, recentNew }}>
      {children}
    </LiveContext.Provider>
  );
}
