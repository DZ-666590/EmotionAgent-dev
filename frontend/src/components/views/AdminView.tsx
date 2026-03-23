import React from 'react';
import { useAdminStore } from '../../store/adminStore';
import { Activity, AlertTriangle, Brain, Thermometer, ShieldAlert, Heart, Frown, Zap } from 'lucide-react';
import { clsx } from 'clsx';

export const AdminView: React.FC = () => {
  const { data } = useAdminStore();

  const getRiskColor = (level?: string) => {
    if (!level) return 'text-muted-foreground bg-secondary/50 border-border/50';
    switch (String(level).toLowerCase()) {
      case 'low': return 'text-green-500 bg-green-500/10 border-green-500/20';
      case 'medium': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
      case 'high': return 'text-red-500 bg-red-500/10 border-red-500/20';
      default: return 'text-muted-foreground bg-secondary/50 border-border/50';
    }
  };

  return (
    <div className="flex-1 overflow-y-auto animate-in fade-in duration-500 scroll-smooth pb-12">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-semibold flex items-center gap-2">
            <Activity className="text-primary" /> 内部状态监控面板
          </h2>
          <span className="text-xs px-3 py-1 rounded-full bg-secondary text-secondary-foreground border">
            实时更新 (SSE)
          </span>
        </div>
        
        {!data ? (
          <div className="glass-panel rounded-3xl p-12 text-center text-muted-foreground flex flex-col items-center gap-4">
            <AlertTriangle className="opacity-50" size={48} />
            <p className="text-lg">暂无活跃会话数据</p>
            <p className="text-sm opacity-70">开启一次对话以查看实时的认知与心理评估状态。</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
             {/* Overall State */}
             <div className="glass-panel rounded-3xl p-6 space-y-4 col-span-1 md:col-span-2 lg:col-span-2">
               <h3 className="font-medium text-muted-foreground flex items-center gap-2">
                 <Brain size={18} /> 整体心理状态评估
               </h3>
               <p className="text-xl md:text-2xl font-medium leading-relaxed">{data.overall_state}</p>
             </div>
             
             {/* Risk Level */}
             <div className="glass-panel rounded-3xl p-6 space-y-4 flex flex-col justify-center">
               <h3 className="font-medium text-muted-foreground flex items-center gap-2">
                 <ShieldAlert size={18} /> 风险等级
               </h3>
               <div className={clsx("inline-flex items-center justify-center px-4 py-2 rounded-full border text-lg font-bold uppercase tracking-wider w-max", getRiskColor(data.risk_level))}>
                 {data.risk_level}
               </div>
             </div>

             {/* Intensity */}
             <div className="glass-panel rounded-3xl p-6 space-y-4">
               <h3 className="font-medium text-muted-foreground flex items-center gap-2">
                 <Thermometer size={18} /> 情绪强度
               </h3>
               <div className="flex items-center gap-4">
                 <div className="flex-1 h-4 bg-secondary rounded-full overflow-hidden shadow-inner">
                   <div 
                     className="h-full bg-gradient-to-r from-primary/50 to-primary transition-all duration-500" 
                     style={{ width: `${(data.intensity / 10) * 100}%` }} 
                   />
                 </div>
                 <span className="font-bold text-xl w-8 text-right">{data.intensity}</span>
               </div>
             </div>

             {/* Emotions */}
             <div className="glass-panel rounded-3xl p-6 space-y-4">
               <h3 className="font-medium text-muted-foreground flex items-center gap-2">
                 <Heart size={18} /> 侦测到的情绪
               </h3>
               <div className="flex flex-wrap gap-2">
                 {data.emotions && data.emotions.length > 0 ? data.emotions.map((emotion, i) => (
                   <span key={i} className="px-3 py-1 bg-secondary text-secondary-foreground rounded-full text-sm border shadow-sm">
                     {emotion}
                   </span>
                 )) : <span className="text-muted-foreground text-sm italic">未检测到明显情绪</span>}
               </div>
             </div>

             {/* Symptoms */}
             <div className="glass-panel rounded-3xl p-6 space-y-4">
               <h3 className="font-medium text-muted-foreground flex items-center gap-2">
                 <Frown size={18} /> 症状线索
               </h3>
               <ul className="space-y-2">
                 {data.symptoms && data.symptoms.length > 0 ? data.symptoms.map((symptom, i) => (
                   <li key={i} className="text-sm bg-background/50 px-3 py-2 rounded-lg border-l-2 border-l-primary">
                     {symptom}
                   </li>
                 )) : <li className="text-muted-foreground text-sm italic">无特定症状线索</li>}
               </ul>
             </div>

             {/* Stressors */}
             <div className="glass-panel rounded-3xl p-6 space-y-4 col-span-1 md:col-span-2 lg:col-span-3">
               <h3 className="font-medium text-muted-foreground flex items-center gap-2">
                 <Zap size={18} /> 压力源
               </h3>
               <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                 {data.stressors && data.stressors.length > 0 ? data.stressors.map((stressor, i) => (
                   <div key={i} className="text-sm bg-background/50 px-4 py-3 rounded-xl border border-border/50 flex items-start gap-3">
                     <span className="w-2 h-2 mt-1.5 rounded-full bg-accent shrink-0" />
                     <span>{stressor}</span>
                   </div>
                 )) : <span className="text-muted-foreground text-sm italic">无特定压力源</span>}
               </div>
             </div>

          </div>
        )}
      </div>
    </div>
  );
};
