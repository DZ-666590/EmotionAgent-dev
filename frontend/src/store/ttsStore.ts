import { create } from 'zustand';

interface TTSState {
  isPlaying: boolean;
  audioElement: HTMLAudioElement | null;
  voice: string;
  offlineWeights: any[] | null;
  emotion: string | null;
  setVoice: (voice: string) => void;
  setIsPlaying: (playing: boolean) => void;
  setAudioElement: (audio: HTMLAudioElement | null) => void;
  setOfflineWeights: (weights: any[] | null) => void;
  setEmotion: (emotion: string | null) => void;
  playTTS: (text: string, emotion?: string) => void;
  stopTTS: () => void;
}

export const useTTSStore = create<TTSState>((set, get) => ({
  isPlaying: false,
  audioElement: null,
  voice: 'zh-CN-XiaoxiaoNeural',
  offlineWeights: null,
  emotion: null,
  setVoice: (voice) => set({ voice }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  setAudioElement: (audio) => set({ audioElement: audio }),
  setOfflineWeights: (weights) => set({ offlineWeights: weights }),
  setEmotion: (emotion) => set({ emotion }),
  playTTS: async (text: string, emotion?: string) => {
    const { audioElement, voice } = get();
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
    }
    if (!text.trim()) return;
    set({ isPlaying: true, offlineWeights: null, emotion: emotion || null });
    
    try {
      // 改为调用离线生成接口以获得更高同步精度
      const response = await fetch('/api/a2f/offline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voice })
      });
      
      if (!response.ok) throw new Error('A2F Offline request failed');
      
      const data = await response.json();
      // 优先使用 wav，如果用户发现播放有问题，可以在这里灵活切换为 data.audio_url_mp3
      const audioUrl = data.audio_url; 
      const weights = data.weights;
      
      console.log('Playing audio from:', audioUrl);
      if (data.audio_url_mp3) {
        console.log('Alternative MP3 available at:', data.audio_url_mp3);
      }

      const audio = new Audio(audioUrl);
      set({ audioElement: audio, offlineWeights: weights });

      audio.onended = () => {
        set({ isPlaying: false, audioElement: null, offlineWeights: null, emotion: null });
      };
      audio.onerror = () => {
        console.error('TTS Playback Error');
        set({ isPlaying: false, audioElement: null, offlineWeights: null, emotion: null });
      };
      
      audio.play().catch(e => {
        console.error('Failed to auto-play audio', e);
        set({ isPlaying: false, audioElement: null, offlineWeights: null, emotion: null });
      });
    } catch (e) {
      console.error('Failed to fetch A2F Offline data', e);
      set({ isPlaying: false, audioElement: null, offlineWeights: null, emotion: null });
    }
  },
  stopTTS: () => {
    const { audioElement } = get();
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
      set({ isPlaying: false, audioElement: null, emotion: null });
    }
  }
}));
