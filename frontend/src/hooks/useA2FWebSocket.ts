import { useEffect, useRef, useCallback, useState } from 'react';

export interface GeometryFrame {
  type: 'frame';
  index: number;
  geometry: number[];
  size: number;
  is_blendshape?: boolean;
}

interface A2FMessage {
  type: 'frame' | 'done' | 'error' | 'ping' | 'pong';
  index?: number;
  geometry?: number[];
  size?: number;
  message?: string;
  is_blendshape?: boolean;
}

interface UseA2FWebSocketOptions {
  url?: string;
  autoConnect?: boolean;
  onFrame?: (frame: GeometryFrame) => void;
  onDone?: () => void;
  onError?: (message: string) => void;
}

export function useA2FWebSocket(options: UseA2FWebSocketOptions = {}) {
  const {
    // 强制直接连接到后端端口 8002，绕过 Vite 代理
    url = `ws://127.0.0.1:8002/api/a2f/ws`,
    autoConnect = true,
    onFrame,
    onDone,
    onError,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastFrame, setLastFrame] = useState<GeometryFrame | null>(null);
  const reconnectTimeoutRef = useRef<number | undefined>(undefined);
  const heartbeatRef = useRef<number | undefined>(undefined);

  const getWsUrl = useCallback(() => {
    const isDev = window.location.port === '5173' || window.location.hostname === 'localhost';
    const wsHost = isDev ? '127.0.0.1:8002' : window.location.host;
    return `ws://${wsHost}/api/a2f/ws`;
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const socketUrl = url || getWsUrl();
      const ws = new WebSocket(socketUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        console.log('[A2F WS] Connected');

        // 心跳
        heartbeatRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const data: A2FMessage = JSON.parse(event.data);

          switch (data.type) {
            case 'frame':
              if (data.geometry && data.index !== undefined && data.size !== undefined) {
                const frame: GeometryFrame = {
                  type: 'frame',
                  index: data.index,
                  geometry: data.geometry,
                  size: data.size,
                  is_blendshape: data.is_blendshape,
                };
                setLastFrame(frame);
                onFrame?.(frame);
              }
              break;

            case 'done':
              onDone?.();
              break;

            case 'error':
              onError?.(data.message || 'Unknown error');
              break;

            case 'ping':
              ws.send(JSON.stringify({ type: 'pong' }));
              break;
          }
        } catch (e) {
          console.error('[A2F WS] Parse error:', e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('[A2F WS] Disconnected');
        clearInterval(heartbeatRef.current);

        // 自动重连
        if (autoConnect) {
          reconnectTimeoutRef.current = window.setTimeout(() => {
            console.log('[A2F WS] Reconnecting...');
            connect();
          }, 2000);
        }
      };

      ws.onerror = (e) => {
        console.error('[A2F WS] Error:', e);
      };
    } catch (e) {
      console.error('[A2F WS] Connection failed:', e);
    }
  }, [url, autoConnect, onFrame, onDone, onError]);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimeoutRef.current);
    clearInterval(heartbeatRef.current);
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    isConnected,
    lastFrame,
    connect,
    disconnect,
  };
}
