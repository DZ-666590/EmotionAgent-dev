import { useRef, useCallback } from 'react';
import { create } from 'zustand';

interface MediaState {
  mediaStream: MediaStream | null;
  setMediaStream: (stream: MediaStream | null) => void;
  isCameraOff: boolean;
  setIsCameraOff: (off: boolean) => void;
  isMicMuted: boolean;
  setIsMicMuted: (muted: boolean) => void;
  isRecording: boolean;
  setIsRecording: (recording: boolean) => void;
  audioBlob: Blob | null;
  setAudioBlob: (blob: Blob | null) => void;
}

export const useMediaStore = create<MediaState>((set) => ({
  mediaStream: null,
  setMediaStream: (stream) => set({ mediaStream: stream }),
  isCameraOff: true,
  setIsCameraOff: (off) => set({ isCameraOff: off }),
  isMicMuted: false,
  setIsMicMuted: (muted) => set({ isMicMuted: muted }),
  isRecording: false,
  setIsRecording: (recording) => set({ isRecording: recording }),
  audioBlob: null,
  setAudioBlob: (blob) => set({ audioBlob: blob }),
}));

export const useMultimodalCapture = () => {
  const { 
    mediaStream, 
    setMediaStream, 
    isCameraOff, 
    setIsCameraOff,
    isMicMuted,
    setIsMicMuted,
    isRecording,
    setIsRecording,
    audioBlob,
    setAudioBlob
  } = useMediaStore();

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);

  const startRecording = useCallback(async (e?: React.SyntheticEvent) => {
    if (e) e.preventDefault();
    if (isMicMuted) {
      alert("请先开启麦克风权限");
      return;
    }
    if (isRecording || mediaRecorderRef.current?.state === 'recording') return;
    
    try {
      let streamToRecord = mediaStream;
      let tempStream: MediaStream | null = null;

      // 如果当前没有任何流，或者流里没有音频轨道，我们单独请求一次录音权限
      if (!streamToRecord || streamToRecord.getAudioTracks().length === 0) {
        tempStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (streamToRecord) {
          tempStream.getAudioTracks().forEach(t => streamToRecord!.addTrack(t));
        } else {
          streamToRecord = tempStream;
          setMediaStream(streamToRecord);
        }
      }

      audioChunksRef.current = [];
      const options = { mimeType: 'audio/webm' };
      mediaRecorderRef.current = new MediaRecorder(streamToRecord!, options);

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      console.error("无法开始录音", err);
    }
  }, [isMicMuted, mediaStream, setMediaStream]);

  const stopRecording = useCallback((e?: React.SyntheticEvent) => {
    if (e) e.preventDefault();
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, [setIsRecording]);

  const toggleMic = useCallback(async () => {
    if (isMicMuted) {
      try {
        const aStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (mediaStream) {
          aStream.getAudioTracks().forEach(t => mediaStream.addTrack(t));
        } else {
          setMediaStream(aStream);
        }
        setIsMicMuted(false);
      } catch (e) {
        console.error("开启麦克风失败", e);
      }
    } else {
      if (mediaStream) {
        mediaStream.getAudioTracks().forEach(track => {
          track.stop();
          mediaStream.removeTrack(track);
        });
      }
      setIsMicMuted(true);
    }
  }, [isMicMuted, mediaStream, setIsMicMuted, setMediaStream]);

  const toggleCamera = useCallback(async () => {
    if (isCameraOff) {
      try {
        const vStream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (mediaStream) {
          vStream.getVideoTracks().forEach(t => mediaStream.addTrack(t));
        } else {
          setMediaStream(vStream);
        }
        setIsCameraOff(false);
      } catch (e) {
        console.error("开启摄像头失败", e);
      }
    } else {
      if (mediaStream) {
        mediaStream.getVideoTracks().forEach(track => {
          track.stop();
          mediaStream.removeTrack(track);
        });
      }
      setIsCameraOff(true);
    }
  }, [isCameraOff, mediaStream, setIsCameraOff, setMediaStream]);

  const clearAudioBlob = useCallback(() => setAudioBlob(null), []);

  return {
    isRecording,
    isMicMuted,
    isCameraOff,
    startRecording,
    stopRecording,
    toggleMic,
    toggleCamera,
    audioBlob,
    clearAudioBlob,
    mediaStream,
  };
};
