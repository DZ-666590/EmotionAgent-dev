import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'error';
  content: string;
  raw?: string;
  isStreaming?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  updatedAt: number;
  messages: ChatMessage[];
}

interface ChatState {
  sessions: ChatSession[];
  activeSessionId: string | null;
  isStreaming: boolean;
  statusText: string;
  asrMeta: any | null;
  
  // Actions
  createNewSession: () => void;
  setActiveSession: (id: string) => void;
  deleteSession: (id: string) => void;
  
  addMessage: (message: Omit<ChatMessage, 'id'>) => void;
  updateLastMessage: (content: string, isStreaming?: boolean, raw?: string) => void;
  setStatusText: (text: string) => void;
  setStreaming: (isStreaming: boolean) => void;
  setAsrMeta: (meta: any) => void;
  clearChat: () => void;
  undoLastMessage: () => void;
}

const generateId = () => Math.random().toString(36).substring(2, 15);

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: [],
      activeSessionId: null,
      isStreaming: false,
      statusText: '',
      asrMeta: null,

      createNewSession: () => {
        const newSession: ChatSession = {
          id: generateId(),
          title: '新的倾诉会话',
          updatedAt: Date.now(),
          messages: []
        };
        set((state) => ({
          sessions: [newSession, ...state.sessions],
          activeSessionId: newSession.id,
          statusText: '',
          asrMeta: null
        }));
      },

      setActiveSession: (id) => {
        set({ activeSessionId: id, statusText: '', asrMeta: null });
      },

      deleteSession: (id) => {
        set((state) => {
          const newSessions = state.sessions.filter(s => s.id !== id);
          return {
            sessions: newSessions,
            activeSessionId: state.activeSessionId === id 
              ? (newSessions.length > 0 ? newSessions[0].id : null) 
              : state.activeSessionId
          };
        });
      },
      
      addMessage: (message) => 
        set((state) => {
          // If no active session, create one first implicitly
          let targetSessionId = state.activeSessionId;
          let newSessions = [...state.sessions];
          
          if (!targetSessionId) {
            const newSession: ChatSession = {
              id: generateId(),
              title: message.role === 'user' ? message.content.slice(0, 15) + '...' : '新的倾诉会话',
              updatedAt: Date.now(),
              messages: []
            };
            targetSessionId = newSession.id;
            newSessions = [newSession, ...newSessions];
          }

          const sessionIndex = newSessions.findIndex(s => s.id === targetSessionId);
          if (sessionIndex > -1) {
            const session = { ...newSessions[sessionIndex] };
            session.messages = [...session.messages, { ...message, id: generateId() }];
            session.updatedAt = Date.now();
            
            // Auto-update title based on first user message if it's currently default
            if (session.messages.length === 1 && message.role === 'user') {
               session.title = message.content.slice(0, 15) + '...';
            }
            
            newSessions[sessionIndex] = session;
          }

          return { 
            sessions: newSessions,
            activeSessionId: targetSessionId
          };
        }),
        
      updateLastMessage: (content, isStreaming = true, raw) =>
        set((state) => {
          if (!state.activeSessionId) return state;
          
          const newSessions = [...state.sessions];
          const sessionIndex = newSessions.findIndex(s => s.id === state.activeSessionId);
          
          if (sessionIndex > -1) {
            const session = { ...newSessions[sessionIndex] };
            const messages = [...session.messages];
            
            if (messages.length > 0) {
              const lastIdx = messages.length - 1;
              messages[lastIdx] = { 
                ...messages[lastIdx], 
                content,
                isStreaming,
                ...(raw !== undefined ? { raw } : {})
              };
              session.messages = messages;
              session.updatedAt = Date.now();
              newSessions[sessionIndex] = session;
            }
          }
          return { sessions: newSessions };
        }),
        
      setStatusText: (text) => set({ statusText: text }),
      setStreaming: (isStreaming) => set({ isStreaming }),
      setAsrMeta: (meta) => set({ asrMeta: meta }),
      
      undoLastMessage: () => set((state) => {
        if (!state.activeSessionId) return state;
        const newSessions = [...state.sessions];
        const sessionIndex = newSessions.findIndex(s => s.id === state.activeSessionId);
        if (sessionIndex > -1) {
          const session = { ...newSessions[sessionIndex] };
          const msgs = [...session.messages];
          
          // Keep popping until we remove the last user message
          let foundUser = false;
          while (msgs.length > 0 && !foundUser) {
            const last = msgs.pop();
            if (last?.role === 'user') {
              foundUser = true;
            }
          }
          
          session.messages = msgs;
          session.updatedAt = Date.now();
          newSessions[sessionIndex] = session;
        }
        return { 
          sessions: newSessions, 
          isStreaming: false, 
          statusText: '', 
          asrMeta: null 
        };
      }),

      clearChat: () => {
         const activeId = get().activeSessionId;
         if (!activeId) return;
         set((state) => {
           const newSessions = [...state.sessions];
           const sessionIndex = newSessions.findIndex(s => s.id === activeId);
           if (sessionIndex > -1) {
             newSessions[sessionIndex] = {
               ...newSessions[sessionIndex],
               messages: [],
               updatedAt: Date.now()
             };
           }
           return { sessions: newSessions, asrMeta: null, statusText: '', isStreaming: false };
         });
      },
    }),
    {
      name: 'chat-storage', // key in localStorage
      partialize: (state) => ({ sessions: state.sessions, activeSessionId: state.activeSessionId }), // only save sessions and active id
    }
  )
);
