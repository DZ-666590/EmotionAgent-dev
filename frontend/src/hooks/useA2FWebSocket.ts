import { useEffect, useRef, useCallback, useState } from 'react';

/** SDK 直接输出的 Blendshape 权重帧 */
export interface BlendshapeFrame {
  type: 'frame';
  index: number;
  weights: number[];  // SDK 直接输出的 blendshape 权重
  count: number;      // 权重数量
}

export type { BlendshapeFrame as GeometryFrame };

export interface UseA2FWebSocketOptions {
  url?: string;
  autoConnect?: boolean;
  onFrame?: (frame: BlendshapeFrame) => void;
  onDone?: () => void;
  onError?: (message: string) => void;
}

export interface A2FMessage {
  type: 'frame' | 'done' | 'error' | 'ping' | 'pong';
  index?: number;
  weights?: number[];
  count?: number;
  message?: string;
}

export function useA2FWebSocket(options: UseA2FWebSocketOptions = {}) {
  const {
    url,
    autoConnect = true,
    onFrame,
    onDone,
    onError,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastFrame, setLastFrame] = useState<BlendshapeFrame | null>(null);
  const reconnectTimeoutRef = useRef<number | undefined>(undefined);
  const heartbeatRef = useRef<number | undefined>(undefined);
  const isConnectingInnerRef = useRef(false);

  // 使用 Ref 保存外部回调，防止函数引用变化导致 WebSocket 重连
  const callbacksRef = useRef({ onFrame, onDone, onError });
  useEffect(() => {
    callbacksRef.current = { onFrame, onDone, onError };
  }, [onFrame, onDone, onError]);

  const getWsUrl = useCallback(() => {
    // 强制使用 127.0.0.1 避免 localhost 域名解析到 IPv6 (::1) 导致连接失败
    const host = "127.0.0.1:8002";
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${host}/api/a2f/ws`;
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current || isConnectingInnerRef.current) return;

    isConnectingInnerRef.current = true;
    try {
      const socketUrl = url || getWsUrl();
      console.log(`[A2F WS] Attempting to connect to ${socketUrl}...`);
      const ws = new WebSocket(socketUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        isConnectingInnerRef.current = false;
        setIsConnected(true);
        console.log('[A2F WS] Connected Successfully');
        
        if (heartbeatRef.current) clearInterval(heartbeatRef.current);
        heartbeatRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 10000);
      };

      ws.onmessage = (event) => {
        try {
          if (event.data === 'pong') return;
          const data: A2FMessage = JSON.parse(event.data);
          
          // 调试：打印所有收到的消息类型
          console.log(`[A2F WS] Received Message Type: ${data.type}`);
          
          switch (data.type) {
            case 'frame':
              if (data.weights && data.index !== undefined) {
                const frame: BlendshapeFrame = {
                  type: 'frame',
                  index: data.index,
                  weights: data.weights,
                  count: data.count || data.weights.length,
                };
                setLastFrame(frame);
                callbacksRef.current.onFrame?.(frame);
              } else {
                console.warn('[A2F WS] Received invalid frame data:', data);
              }
              break;
            case 'done':
              callbacksRef.current.onDone?.();
              break;
            case 'error':
              callbacksRef.current.onError?.(data.message || 'Unknown error');
              break;
          }
        } catch (e) {
          // Ignore
        }
      };

      ws.onclose = (event) => {
        isConnectingInnerRef.current = false;
        setIsConnected(false);
        console.log(`[A2F WS] Disconnected (Code: ${event.code})`);
        if (heartbeatRef.current) clearInterval(heartbeatRef.current);

        if (autoConnect && event.code !== 1000) {
          if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = window.setTimeout(() => {
            console.log('[A2F WS] Reconnecting...');
            connect();
          }, 3000);
        }
      };

      ws.onerror = (e) => {
        isConnectingInnerRef.current = false;
        console.error('[A2F WS] Error:', e);
      };
    } catch (e) {
      isConnectingInnerRef.current = false;
      console.error('[A2F WS] Connection failed:', e);
    }
  }, [url, autoConnect, getWsUrl]);

  const disconnect = useCallback(() => {
    console.log('[A2F WS] Disconnect requested');
    isConnectingInnerRef.current = false;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = undefined;
    }
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = undefined;
    }
    
    if (wsRef.current) {
      const socket = wsRef.current;
      wsRef.current = null;
      socket.onclose = null; 
      socket.onerror = null;
      socket.onmessage = null;
      socket.onopen = null;

      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        console.log('[A2F WS] Closing socket...');
        socket.close(1000);
      }
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (autoConnect) {
        connect();
      }
    }, 300);

    return () => {
      clearTimeout(timer);
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
