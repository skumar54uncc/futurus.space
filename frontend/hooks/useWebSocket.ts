"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";

export type WsMessage = {
  type?: string;
  progress?: number;
  message?: string;
  [key: string]: unknown;
};

interface UseWebSocketOptions {
  simulationId: string;
  enabled?: boolean;
  onMessage?: (msg: WsMessage) => void;
}

export function useWebSocket({ simulationId, enabled = true, onMessage }: UseWebSocketOptions) {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WsMessage | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  const { getToken, isLoaded } = useAuth();

  useEffect(() => {
    if (!simulationId || !enabled || !isLoaded) return;

    let ws: WebSocket | null = null;
    let cancelled = false;
    let retryTimer: number | null = null;

    const connect = async (attempt: number) => {
      try {
        const token = await getToken();
        if (cancelled) return;
        if (!token) {
          if (attempt < 12) {
            retryTimer = window.setTimeout(() => void connect(attempt + 1), 400);
          }
          return;
        }

        const base = (process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000").replace(
          /^http/,
          "ws"
        );
        const url = `${base}/ws/simulation/${encodeURIComponent(simulationId)}?token=${encodeURIComponent(token)}`;
        ws = new WebSocket(url);

        ws.onopen = () => {
          if (!cancelled) setConnected(true);
        };
        ws.onclose = () => {
          if (!cancelled) setConnected(false);
        };
        ws.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data) as WsMessage;
            if (!cancelled) setLastMessage(data);
            onMessageRef.current?.(data);
          } catch {
            /* ignore */
          }
        };
      } catch {
        /* ignore */
      }
    };

    void connect(0);

    return () => {
      cancelled = true;
      if (retryTimer !== null) window.clearTimeout(retryTimer);
      ws?.close();
      setConnected(false);
    };
  }, [simulationId, enabled, isLoaded, getToken]);

  return { connected, lastMessage };
}
