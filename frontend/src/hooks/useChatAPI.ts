import { useRef } from 'react';
import { useChatStore } from '../store/chatStore';
import { useAdminStore } from '../store/adminStore';
import { useTTSStore } from '../store/ttsStore';

export const useChatAPI = () => {
  const abortControllerRef = useRef<AbortController | null>(null);
  const { addMessage, updateLastMessage, setStreaming, setStatusText, asrMeta } = useChatStore();
  const updateAdminData = useAdminStore((state) => state.updateData);
  const playTTS = useTTSStore((state) => state.playTTS);

  const sendMessage = async (message: string) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    addMessage({ role: 'user', content: message });
    addMessage({ role: 'assistant', content: '', isStreaming: true, raw: '' });
    setStreaming(true);
    setStatusText('Thinking...');

    try {
      const activeSession = useChatStore.getState().sessions.find(s => s.id === useChatStore.getState().activeSessionId);
      const history = (activeSession?.messages || [])
        .filter(m => !m.isStreaming && m.role !== 'error')
        .map(m => ({ role: m.role, content: m.raw || m.content }));

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history, asr_meta: asrMeta }),
        signal: controller.signal,
      });

      if (!response.ok) throw new Error('Network error');
      if (!response.body) throw new Error('No body returned');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let fullContent = '';
      let rawContent = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          if (part.startsWith('data: ')) {
            const dataStr = part.slice(6);
            if (!dataStr) continue;
            
            try {
              const data = JSON.parse(dataStr);
              
              if (data.type === 'status') {
                setStatusText(data.content);
              } else if (data.type === 'internal_state') {
                updateAdminData(data.data);
              } else if (data.type === 'chunk') {
                rawContent += data.content;
                fullContent = rawContent.replace(/\([^)]*\)|（[^）]*）/g, ''); 
                updateLastMessage(fullContent, true, rawContent);
              } else if (data.type === 'error') {
                updateLastMessage(data.content, false);
                setStatusText('Error');
              } else if (data.type === 'done') {
                updateLastMessage(fullContent, false, rawContent);
                setStatusText('');
                if (fullContent) {
                  playTTS(fullContent);
                }
              }
            } catch (e) {
              console.error('Failed to parse SSE JSON', e);
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        updateLastMessage('抱歉，连接服务器时发生错误，请稍后再试。', false);
        setStatusText('');
      }
    } finally {
      setStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const stopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setStreaming(false);
      setStatusText('已停止');
    }
  };

  return { sendMessage, stopStreaming };
};
