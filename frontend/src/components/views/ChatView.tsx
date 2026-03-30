import React, { useState, useRef, useEffect } from 'react';
import type { KeyboardEvent } from 'react';
import { useChatStore } from '../../store/chatStore';
import { useChatAPI } from '../../hooks/useChatAPI';
import { useTTSStore } from '../../store/ttsStore';
import { useMultimodalCapture } from '../../hooks/useMultimodalCapture';
import { useUIStore } from '../../store/uiStore';
import ReactMarkdown from 'react-markdown';
import { Send, Square, Mic, Volume2, Square as StopCircle, PlusCircle, MessageCircle, Trash2, RotateCcw } from 'lucide-react';
import { clsx } from 'clsx';
import { Avatar3D } from './Avatar3D';

export const ChatView: React.FC = () => {
  const { 
    sessions,
    activeSessionId,
    createNewSession,
    setActiveSession,
    deleteSession,
    statusText, 
    isStreaming, 
    setAsrMeta,
    undoLastMessage
  } = useChatStore();
  
  const { isVoiceMode } = useUIStore();
  const activeSession = sessions.find(s => s.id === activeSessionId);
  const messages = activeSession?.messages || [];
  const { isPlaying, stopTTS } = useTTSStore();
  const { sendMessage, stopStreaming } = useChatAPI();
  
  const { 
    isRecording, 
    startRecording, 
    stopRecording, 
    audioBlob, 
    clearAudioBlob 
  } = useMultimodalCapture();

  const [input, setInput] = useState('');
  const [isProcessingAsr, setIsProcessingAsr] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isUploadingRef = useRef(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, statusText]);

  // Handle ASR Upload
  useEffect(() => {
    if (audioBlob && !isUploadingRef.current) {
      isUploadingRef.current = true;
      const blobToUpload = audioBlob;
      clearAudioBlob(); // Immediately clear from store

      const uploadAudio = async () => {
        setIsProcessingAsr(true);
        const formData = new FormData();
        formData.append('file', blobToUpload, 'recording.webm');
        try {
          const response = await fetch('/api/asr', { method: 'POST', body: formData });
          if (!response.ok) throw new Error('ASR Failed');
          const data = await response.json();
          if (data.text) {
            setAsrMeta(data);
            sendMessage(data.text);
          }
        } catch (error) {
          console.error('ASR Upload Error', error);
          useChatStore.getState().addMessage({ role: 'error', content: '无法处理语音，请重试或直接输入文字。确保本地 ASR 服务已启动。' });
        } finally {
          setIsProcessingAsr(false);
          isUploadingRef.current = false;
        }
      };
      uploadAudio();
    } else if (!audioBlob) {
      isUploadingRef.current = false;
    }
  }, [audioBlob, clearAudioBlob, sendMessage, setAsrMeta]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isStreaming) return;
    sendMessage(input.trim());
    setInput('');
    setAsrMeta(null); // Clear previous ASR meta on manual text input
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
  };

  return (
    <div className="flex-1 flex h-full gap-4 overflow-hidden animate-in fade-in slide-in-from-bottom-8 duration-500 pb-2">
      
      {/* Sidebar for Sessions */}
      <div className={clsx(
        "hidden md:flex flex-col w-64 bg-background/40 backdrop-blur-md rounded-3xl border shadow-sm overflow-hidden transition-all duration-500",
        isVoiceMode && "opacity-0 w-0 md:hidden border-none"
      )}>
        <div className="p-4 border-b border-border/30">
          <button 
            onClick={createNewSession}
            className="flex items-center gap-2 justify-center w-full p-3 rounded-2xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
          >
            <PlusCircle size={18} />
            <span>新对话</span>
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-3 pb-4 space-y-2 custom-scrollbar">
          {sessions.map(session => (
            <div 
              key={session.id}
              onClick={() => setActiveSession(session.id)}
              className={clsx(
                "group flex items-center justify-between p-3 rounded-xl cursor-pointer transition-colors border border-transparent",
                activeSessionId === session.id 
                  ? "bg-secondary/80 border-border/50 text-foreground" 
                  : "hover:bg-secondary/40 text-muted-foreground"
              )}
            >
              <div className="flex items-center gap-2 overflow-hidden">
                <MessageCircle size={16} className="shrink-0" />
                <span className="truncate text-sm">{session.title}</span>
              </div>
              <button 
                onClick={(e) => { e.stopPropagation(); deleteSession(session.id); }}
                className="opacity-0 group-hover:opacity-100 p-1 hover:text-destructive transition-all rounded-md"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          {sessions.length === 0 && (
            <div className="text-center text-sm text-muted-foreground mt-10">
              暂无历史对话
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className={clsx(
        "flex-1 flex flex-col h-full relative transition-all duration-500 gap-4",
        isVoiceMode && "opacity-0 w-0 overflow-hidden"
      )}>
      <div className="flex-1 bg-background/40 backdrop-blur-md rounded-3xl border shadow-sm overflow-y-auto p-4 md:p-6 space-y-6 scroll-smooth">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground space-y-4">
            <div className="w-16 h-16 rounded-full bg-secondary/50 flex items-center justify-center ambient-glow">
              <span className="text-2xl">👋</span>
            </div>
            <p>你现在感觉怎么样？</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={clsx(
                "max-w-[85%] md:max-w-[75%] rounded-2xl px-5 py-3 shadow-sm",
                msg.role === 'user' 
                  ? 'bg-primary text-primary-foreground rounded-br-sm' 
                  : 'bg-card text-card-foreground rounded-bl-sm border',
                msg.role === 'error' && 'border-destructive text-destructive bg-destructive/10'
              )}>
                {msg.role === 'assistant' ? (
                  <div className="prose dark:prose-invert prose-sm md:prose-base max-w-none">
                    <ReactMarkdown>{msg.content || ''}</ReactMarkdown>
                    {msg.isStreaming && <span className="inline-block w-1.5 h-4 ml-1 bg-primary animate-pulse align-middle" />}
                  </div>
                ) : (
                  <span className="whitespace-pre-wrap">{msg.content || ''}</span>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="bg-background/60 backdrop-blur-md rounded-3xl border shadow-sm p-3 relative shrink-0">
        {(statusText || isProcessingAsr || isRecording || isPlaying) && (
          <div className="absolute -top-10 left-6 right-6 flex items-center justify-between">
            <span className={clsx(
              "text-xs font-medium px-3 py-1 rounded-full shadow-sm flex items-center gap-2",
              isRecording ? "bg-destructive text-destructive-foreground animate-pulse" : "bg-background/80 text-muted-foreground"
            )}>
              {isRecording ? "正在倾听..." : isProcessingAsr ? "正在处理语音..." : isPlaying ? <><Volume2 size={14} className="animate-pulse" /> 正在说话...</> : statusText}
            </span>
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="flex items-end gap-3 max-w-full mx-auto">
          {isPlaying ? (
            <button 
              type="button"
              onClick={stopTTS}
              className="w-12 h-12 rounded-full bg-secondary text-secondary-foreground flex items-center justify-center hover:bg-secondary/80 transition-colors shrink-0 shadow-sm"
              title="停止播放"
            >
              <StopCircle size={20} className="fill-current" />
            </button>
          ) : (
            <button 
              type="button"
              onClick={() => {
                if (isRecording) stopRecording();
                else startRecording();
              }}
              className={clsx(
                "w-12 h-12 rounded-full flex items-center justify-center transition-colors shrink-0 shadow-sm",
                isRecording ? "bg-destructive text-destructive-foreground animate-pulse" : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              )}
              title={isRecording ? "点击停止录音" : "点击开始录音"}
            >
              {isRecording ? <StopCircle size={20} className="fill-current" /> : <Mic size={20} />}
            </button>
          )}

          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={isRecording ? "正在倾听..." : "输入你的想法..."}
            className="flex-1 bg-background border-none rounded-2xl px-4 py-3 min-h-[48px] max-h-[150px] focus:outline-none focus:ring-0 transition-all resize-none"
            rows={1}
            disabled={isStreaming || isRecording || isProcessingAsr}
          />
          
          <button
            type="button"
            onClick={undoLastMessage}
            disabled={messages.length === 0 || isStreaming}
            className="w-12 h-12 rounded-full bg-secondary/50 text-muted-foreground flex items-center justify-center hover:bg-secondary hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0 shadow-sm"
            title="撤回上一条对话"
          >
            <RotateCcw size={20} />
          </button>
          
          {isStreaming ? (
            <button 
              type="button"
              onClick={stopStreaming}
              className="w-12 h-12 rounded-full bg-destructive/10 text-destructive flex items-center justify-center hover:bg-destructive hover:text-destructive-foreground transition-colors shrink-0 shadow-sm"
              title="停止生成"
            >
              <Square size={20} className="fill-current" />
            </button>
          ) : (
            <button 
              type="submit"
              disabled={!input.trim() || isRecording || isProcessingAsr}
              className="w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0 shadow-sm"
              title="发送"
            >
              <Send size={20} className="ml-1" />
            </button>
          )}
        </form>
      </div>
      </div>

      {/* Right side: Digital Human Reserved Area */}
      <div className={clsx(
        "hidden lg:flex flex-col w-80 h-[400px] bg-background/40 backdrop-blur-md rounded-3xl border shadow-sm overflow-hidden relative transition-all duration-500",
        isVoiceMode && "flex-1 w-full max-w-2xl h-full mx-auto shadow-xl ring-1 ring-primary/20 bg-background/60"
      )}>
        <div className="absolute inset-0 flex flex-col items-center justify-center opacity-20 z-0 pointer-events-none">
           <div className="w-48 h-48 rounded-full bg-[hsl(30,50%,80%)]/20 flex items-center justify-center blur-2xl"></div>
        </div>
        <div className="relative z-10 w-full h-full">
           <Avatar3D className="w-full h-full" />
        </div>
      </div>
    </div>
  );
};
