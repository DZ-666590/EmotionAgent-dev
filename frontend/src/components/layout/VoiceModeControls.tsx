import React from 'react';
import { Mic, Square as StopCircle, X } from 'lucide-react';
import { useMultimodalCapture } from '../../hooks/useMultimodalCapture';
import { useTTSStore } from '../../store/ttsStore';
import { useUIStore } from '../../store/uiStore';
import { clsx } from 'clsx';

export const VoiceModeControls: React.FC = () => {
  const { isRecording, startRecording, stopRecording } = useMultimodalCapture();
  const { isPlaying, stopTTS } = useTTSStore();
  const { toggleVoiceMode } = useUIStore();

  return (
    <div className="fixed bottom-12 left-1/2 -translate-x-1/2 z-50 flex items-center gap-6 glass-panel px-8 py-4 rounded-full shadow-2xl animate-in slide-in-from-bottom-12 fade-in duration-500 border border-white/20">
      
      <button 
        onClick={toggleVoiceMode}
        className="w-12 h-12 rounded-full bg-secondary/80 text-muted-foreground flex items-center justify-center hover:bg-secondary hover:text-foreground transition-colors"
        title="退出语音模式"
      >
        <X size={24} />
      </button>

      {isPlaying ? (
        <button 
          onClick={stopTTS}
          className="w-16 h-16 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center hover:bg-destructive/90 transition-colors shadow-lg shadow-destructive/20 animate-pulse"
          title="打断说话"
        >
          <StopCircle size={28} className="fill-current" />
        </button>
      ) : (
        <button 
          onClick={() => {
            if (isRecording) stopRecording();
            else startRecording();
          }}
          className={clsx(
            "w-16 h-16 rounded-full flex items-center justify-center transition-all shadow-lg",
            isRecording 
              ? "bg-destructive text-destructive-foreground scale-110 shadow-destructive/40 animate-pulse-ring" 
              : "bg-primary text-primary-foreground hover:scale-105 shadow-primary/30"
          )}
          title={isRecording ? "点击停止录音" : "点击开始录音"}
        >
          {isRecording ? <StopCircle size={28} className="fill-current" /> : <Mic size={28} />}
        </button>
      )}

    </div>
  );
};
