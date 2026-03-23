import { useEffect, useRef } from 'react';
import { useMediaStore } from './useMultimodalCapture';

// 抓取帧的间隔(毫秒)
const CAPTURE_INTERVAL = 3000;

export const useVisionCapture = () => {
  const { mediaStream, isCameraOff } = useMediaStore();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (isCameraOff || !mediaStream) return;
    
    const videoTracks = mediaStream.getVideoTracks();
    if (videoTracks.length === 0) return;

    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas');
    }

    const videoTrack = videoTracks[0];
    
    // Fallback if ImageCapture is not supported in the browser
    if (!('ImageCapture' in window)) {
       console.warn("浏览器不支持 ImageCapture API");
       return;
    }
    
    const imageCapture = new (window as any).ImageCapture(videoTrack);

    const captureFrame = async () => {
      try {
        const bitmap = await imageCapture.grabFrame();
        
        const canvas = canvasRef.current!;
        canvas.width = bitmap.width;
        canvas.height = bitmap.height;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
          
          canvas.toBlob(async (blob) => {
            if (blob) {
              const formData = new FormData();
              formData.append('file', blob, 'frame.jpg');
              
              // 自动将帧发送给后端的 /api/vision 端点进行多模态分析
              try {
                const res = await fetch('/api/vision', { method: 'POST', body: formData });
                const data = await res.json();
                console.log("Vision analysis:", data);
              } catch (e) {
                console.error("Vision API error", e);
              }
            }
          }, 'image/jpeg', 0.8);
        }
      } catch (err) {
        console.error("Error capturing frame", err);
      }
    };

    const intervalId = setInterval(captureFrame, CAPTURE_INTERVAL);
    return () => clearInterval(intervalId);
  }, [mediaStream, isCameraOff]);
};
