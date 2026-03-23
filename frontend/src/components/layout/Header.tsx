import React from 'react';
import { MessageSquare, LayoutDashboard, Home, Mic, MicOff, Video, VideoOff, Settings } from 'lucide-react';
import { useUIStore } from '../../store/uiStore';
import { useMultimodalCapture } from '../../hooks/useMultimodalCapture';
import { NavLink } from 'react-router-dom';
import { clsx } from 'clsx';

export const Header: React.FC = () => {
  const { isVoiceMode, toggleVoiceMode } = useUIStore();
  const { isCameraOff, isMicMuted, toggleCamera, toggleMic } = useMultimodalCapture();

  const navItems = [
    { id: '/', icon: Home, label: '首页' },
    { id: '/chat', icon: MessageSquare, label: '对话' },
    { id: '/admin', icon: LayoutDashboard, label: '监控面板' },
    { id: '/settings', icon: Settings, label: '设置' },
  ];

  return (
    <header className="sticky top-0 z-50 glass-panel border-b px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold">
          心
        </div>
        <h1 className="text-xl font-semibold text-foreground tracking-tight hidden sm:block">
          情感陪护
        </h1>
      </div>

      <nav className="hidden md:flex items-center gap-1 bg-secondary/50 p-1 rounded-full border border-border/50">
        {navItems.map(({ id, icon: Icon, label }) => (
          <NavLink
            key={id}
            to={id}
            className={({ isActive }) => clsx(
              'flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-300',
              isActive 
                ? 'bg-background shadow-sm text-primary' 
                : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
            )}
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="flex items-center gap-2">
        {/* Hardware Kill Switches */}
        <div className="flex items-center gap-1 mr-2 border-r border-border/50 pr-4">
          <button 
            onClick={toggleMic}
            className={clsx(
              "p-2 rounded-full transition-colors",
              !isMicMuted ? "text-primary hover:bg-primary/10" : "text-destructive hover:bg-destructive/10"
            )}
            title={!isMicMuted ? "麦克风已开启 - 点击禁用" : "麦克风已禁用 - 点击开启"}
          >
            {!isMicMuted ? <Mic size={18} /> : <MicOff size={18} />}
          </button>
          <button 
            onClick={toggleCamera}
            className={clsx(
              "p-2 rounded-full transition-colors",
              !isCameraOff ? "text-primary hover:bg-primary/10" : "text-muted-foreground hover:bg-secondary"
            )}
            title={!isCameraOff ? "摄像头已开启 - 点击禁用" : "摄像头已禁用 - 点击开启"}
          >
            {!isCameraOff ? <Video size={18} /> : <VideoOff size={18} />}
          </button>
        </div>

        <button
          onClick={toggleVoiceMode}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-full transition-all duration-300 border',
            isVoiceMode 
              ? 'bg-primary text-primary-foreground border-primary shadow-[0_0_15px_rgba(170,59,255,0.5)]' 
              : 'glass-panel text-muted-foreground hover:text-foreground border-border/50'
          )}
        >
          <span className="relative flex h-3 w-3">
            {isVoiceMode && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-foreground opacity-75"></span>}
            <span className={clsx("relative inline-flex rounded-full h-3 w-3", isVoiceMode ? "bg-primary-foreground" : "bg-muted-foreground")}></span>
          </span>
          <span className="hidden sm:inline">语音模式</span>
        </button>
      </div>
    </header>
  );
};
