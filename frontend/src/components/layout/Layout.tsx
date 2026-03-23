import React, { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { useUIStore } from '../../store/uiStore';
import { useAdminStore } from '../../store/adminStore';
import { Header } from './Header';
import { VideoPreview } from '../views/VideoPreview';
import { useVisionCapture } from '../../hooks/useVisionCapture';
import { VoiceModeControls } from './VoiceModeControls';

export const Layout: React.FC = () => {
  const { isVoiceMode } = useUIStore();
  const data = useAdminStore((state) => state.data);
  const location = useLocation();
  
  // Initialize periodic vision capture when camera is active
  useVisionCapture();

  useEffect(() => {
    if (isVoiceMode) {
      document.body.classList.add('voice-mode');
    } else {
      document.body.classList.remove('voice-mode');
    }
  }, [isVoiceMode]);

  const isChatRoute = location.pathname === '/chat';

  return (
    <div className={`min-h-screen flex flex-col transition-all duration-700 ease-in-out bg-background`}>
      <Header />
      
      <main className="flex-1 relative flex flex-col max-w-[1600px] mx-auto w-full p-4 md:p-6 md:pb-6 overflow-hidden">
        {/* Visualization layer - Removed global Avatar3D from center per user request */}
        {(location.pathname === '/' || location.pathname === '/chat') && (
          <div className={`absolute inset-0 transition-all duration-700 pointer-events-none flex items-center justify-center
            ${isVoiceMode ? 'scale-110 z-10' : 'scale-100 z-0 opacity-50'}`}>
             <div id="digital-human-area" className="relative w-64 h-64 md:w-96 md:h-96 rounded-full bg-secondary/30 ambient-glow flex items-center justify-center overflow-hidden pointer-events-auto">
               {/* Global Avatar3D removed - now only handled in ChatView's sidebar */}
               <div className="absolute inset-0 flex flex-col items-center justify-center z-10 pointer-events-none">
                 {data && data.emotions && data.emotions.length > 0 && (
                   <>
                     <span className="text-xl font-bold uppercase tracking-widest opacity-80 text-white drop-shadow-lg">{data.emotions[0]}</span>
                     <span className="text-sm opacity-60 text-white drop-shadow">情绪强度: {data.intensity}</span>
                   </>
                 )}
               </div>
             </div>
          </div>
        )}

        {/* Content layer */}
        <div className={`relative z-10 flex-1 flex flex-col transition-all duration-500 h-full
          ${isVoiceMode && !isChatRoute ? 'opacity-0 pointer-events-none translate-y-8' : 'opacity-100 translate-y-0'}`}>
          <Outlet />
        </div>
      </main>

      {/* Floating Video Preview for Multimodal */}
      <VideoPreview />

      {/* Voice Mode Floating Controls */}
      {isVoiceMode && <VoiceModeControls />}
    </div>
  );
};
