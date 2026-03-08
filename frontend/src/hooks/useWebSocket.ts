import { useRef, useState, useCallback } from 'react';
import { WS_URL } from '@/lib/api';

export type WsMessage = {
  type: string;
  [key: string]: any;
};

export function useWebSocket(roomId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<WsMessage[]>([]);

  const connect = useCallback(() => {
    if (!roomId) return;
    const ws = new WebSocket(`${WS_URL}/ws/${roomId}`);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        setMessages((prev) => [...prev, msg]);
      } catch {}
    };
  }, [roomId]);

  const send = useCallback((data: any) => {
    wsRef.current?.send(JSON.stringify(data));
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, []);

  const clearMessages = useCallback(() => setMessages([]), []);

  return { connected, messages, connect, send, disconnect, clearMessages };
}
