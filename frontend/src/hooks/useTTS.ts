import { useState, useRef, useCallback } from 'react';

export const useTTS = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const playTTS = useCallback((text: string) => {
    if (!text.trim()) return;

    // Stop currently playing audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }

    setIsPlaying(true);
    
    // Construct the endpoint as per the old frontend's API contract
    const url = `/api/tts/stream?text=${encodeURIComponent(text)}`;
    const audio = new Audio(url);
    audioRef.current = audio;

    audio.onended = () => {
      setIsPlaying(false);
      audioRef.current = null;
    };

    audio.onerror = (e) => {
      console.error('TTS Playback Error', e);
      setIsPlaying(false);
      audioRef.current = null;
    };

    audio.play().catch(e => {
      console.error('Failed to auto-play audio', e);
      setIsPlaying(false);
    });
  }, []);

  const stopTTS = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
      audioRef.current = null;
    }
  }, []);

  return { isPlaying, playTTS, stopTTS };
};
