import { WebSocketMessage } from "./types";

/**
 * SECURITY: WebSocket auth uses ?token= (Clerk JWT); browsers cannot send Authorization on WS.
 */
export async function buildSimulationWebSocketUrl(simulationId: string): Promise<string> {
  const token = await window.Clerk?.session?.getToken();
  if (!token) {
    throw new Error("Not authenticated");
  }
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
  const wsUrl = backendUrl.replace(/^http/, "ws");
  return `${wsUrl}/ws/simulation/${encodeURIComponent(simulationId)}?token=${encodeURIComponent(token)}`;
}

export class SimulationWebSocket {
  private ws: WebSocket | null = null;
  private listeners: Array<(msg: WebSocketMessage) => void> = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private simulationId: string;

  constructor(simulationId: string) {
    this.simulationId = simulationId;
  }

  async connect() {
    let url: string;
    try {
      url = await buildSimulationWebSocketUrl(this.simulationId);
    } catch {
      return;
    }
    this.ws = new WebSocket(url);

    this.ws.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data);
      this.listeners.forEach((fn) => fn(data));
      if (data.progress === 100 || data.progress === -1) {
        this.disconnect();
      }
    };

    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        setTimeout(() => void this.connect(), 2000 * this.reconnectAttempts);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  onMessage(fn: (msg: WebSocketMessage) => void) {
    this.listeners.push(fn);
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
  }
}
