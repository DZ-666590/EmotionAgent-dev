import React, { useEffect, useRef } from 'react';
import { useMediaStore } from '../../hooks/useMultimodalCapture';

export const VideoPreview: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const { mediaStream, isCameraOff } = useMediaStore();

  useEffect(() => {
    if (videoRef.current && mediaStream && !isCameraOff) {
      videoRef.current.srcObject = mediaStream;
    }
  }, [mediaStream, isCameraOff]);

  if (isCameraOff || !mediaStream) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 w-48 h-36 rounded-2xl overflow-hidden shadow-2xl border-2 border-border/50 bg-black animate-in fade-in slide-in-from-bottom-8">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full h-full object-cover mirror-mode"
        style={{ transform: 'scaleX(-1)' }}
      />
      <div className="absolute top-2 left-2 flex items-center gap-2 bg-black/50 backdrop-blur-sm px-2 py-1 rounded-full">
        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
        <span className="text-[10px] text-white font-medium">视觉分析中</span>
      </div>
    </div>
  );
};
