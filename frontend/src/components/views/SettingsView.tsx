import React from 'react';
import { Settings as SettingsIcon, Camera, Mic, Volume2, Shield, User } from 'lucide-react';
import { useMultimodalCapture } from '../../hooks/useMultimodalCapture';
import { useTTSStore } from '../../store/ttsStore';
import { clsx } from 'clsx';

export const SettingsView: React.FC = () => {
  const { isCameraOff, isMicMuted, toggleCamera, toggleMic } = useMultimodalCapture();
  const { voice, setVoice } = useTTSStore();

  return (
    <div className="flex-1 overflow-y-auto animate-in fade-in duration-500 scroll-smooth pb-12">
      <div className="max-w-3xl mx-auto space-y-8">
        <div className="flex items-center gap-3 border-b border-border/50 pb-6">
          <div className="w-12 h-12 rounded-2xl bg-primary/20 flex items-center justify-center text-primary">
            <SettingsIcon size={24} />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground tracking-tight">系统设置</h2>
            <p className="text-muted-foreground">个性化您的情感陪护体验与隐私权限</p>
          </div>
        </div>

        <div className="space-y-6">
          {/* Privacy & Devices */}
          <section className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2 text-foreground">
              <Shield size={18} className="text-primary" /> 隐私与设备权限
            </h3>
            <div className="glass-panel rounded-2xl overflow-hidden divide-y divide-border/50">
              <div className="p-4 flex items-center justify-between hover:bg-secondary/20 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center text-muted-foreground">
                    <Camera size={18} />
                  </div>
                  <div>
                    <p className="font-medium">多模态视觉感知 (摄像头)</p>
                    <p className="text-sm text-muted-foreground">允许 AI 通过面部表情感知您的情绪状态，数据仅在本地处理，不会保存。</p>
                  </div>
                </div>
                <div 
                  onClick={toggleCamera}
                  className={clsx(
                    "w-12 h-6 rounded-full relative cursor-pointer shadow-inner transition-colors",
                    !isCameraOff ? "bg-primary" : "bg-muted"
                  )}
                >
                  <div className={clsx(
                    "absolute top-1 w-4 h-4 bg-white rounded-full transition-all duration-300",
                    !isCameraOff ? "right-1" : "left-1"
                  )}></div>
                </div>
              </div>

              <div className="p-4 flex items-center justify-between hover:bg-secondary/20 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center text-muted-foreground">
                    <Mic size={18} />
                  </div>
                  <div>
                    <p className="font-medium">语音与语气分析 (麦克风)</p>
                    <p className="text-sm text-muted-foreground">允许记录并分析您的声音波形以提取情绪置信度。</p>
                  </div>
                </div>
                <div 
                  onClick={toggleMic}
                  className={clsx(
                    "w-12 h-6 rounded-full relative cursor-pointer shadow-inner transition-colors",
                    !isMicMuted ? "bg-primary" : "bg-muted"
                  )}
                >
                  <div className={clsx(
                    "absolute top-1 w-4 h-4 bg-white rounded-full transition-all duration-300",
                    !isMicMuted ? "right-1" : "left-1"
                  )}></div>
                </div>
              </div>
            </div>
          </section>

          {/* Assistant Preferences */}
          <section className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2 text-foreground">
              <User size={18} className="text-primary" /> 陪护者偏好
            </h3>
            <div className="glass-panel rounded-2xl overflow-hidden divide-y divide-border/50">
              <div className="p-4 flex items-center justify-between hover:bg-secondary/20 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center text-muted-foreground">
                    <Volume2 size={18} />
                  </div>
                  <div>
                    <p className="font-medium">默认音色</p>
                    <p className="text-sm text-muted-foreground">选择陪伴您的声音风格</p>
                  </div>
                </div>
                <select 
                  value={voice}
                  onChange={(e) => setVoice(e.target.value)}
                  className="bg-background border border-border/50 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value="zh-CN-XiaoxiaoNeural">温柔女性 (晓晓)</option>
                  <option value="zh-CN-YunxiNeural">成熟男性 (云希)</option>
                  <option value="zh-CN-XiaoyiNeural">治愈中性 (晓依)</option>
                </select>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};
