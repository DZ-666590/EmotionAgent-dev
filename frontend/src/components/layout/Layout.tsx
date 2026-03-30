import React, { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { useUIStore } from '../../store/uiStore';
import { useAdminStore } from '../../store/adminStore';
import { Header } from './Header';
import { VideoPreview } from '../views/VideoPreview';
import { useVisionCapture } from '../../hooks/useVisionCapture';
import { VoiceModeControls } from './VoiceModeControls';
import { Avatar3D } from '../views/Avatar3D';

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
