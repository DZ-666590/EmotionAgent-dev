import { create } from 'zustand';

interface TTSState {
  isPlaying: boolean;
  audioElement: HTMLAudioElement | null;
  voice: string;
  setVoice: (voice: string) => void;
  setIsPlaying: (playing: boolean) => void;
  setAudioElement: (audio: HTMLAudioElement | null) => void;
  playTTS: (text: string) => void;
  stopTTS: () => void;
}

export const useTTSStore = create<TTSState>((set, get) => ({
  isPlaying: false,
  audioElement: null,
  voice: 'zh-CN-XiaoxiaoNeural',
  setVoice: (voice) => set({ voice }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  setAudioElement: (audio) => set({ audioElement: audio }),
  playTTS: async (text: string) => {
    const { audioElement, voice } = get();
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
    }
    if (!text.trim()) return;
    set({ isPlaying: true });
    
    try {
      const response = await fetch('/api/a2f/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voice })
      });
      
      if (!response.ok) throw new Error('TTS/A2F request failed');
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      
      set({ audioElement: audio });

      audio.onended = () => {
        set({ isPlaying: false, audioElement: null });
        URL.revokeObjectURL(url);
      };
      audio.onerror = () => {
        console.error('TTS Playback Error');
        set({ isPlaying: false, audioElement: null });
        URL.revokeObjectURL(url);
      };
      
      audio.play().catch(e => {
        console.error('Failed to auto-play audio', e);
        set({ isPlaying: false, audioElement: null });
        URL.revokeObjectURL(url);
      });
    } catch (e) {
      console.error('Failed to fetch TTS/A2F', e);
      set({ isPlaying: false, audioElement: null });
    }
  },
  stopTTS: () => {
    const { audioElement } = get();
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
      set({ isPlaying: false, audioElement: null });
    }
  }
}));
