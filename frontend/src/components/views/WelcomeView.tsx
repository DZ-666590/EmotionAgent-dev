import React from 'react';
import { MessageSquare } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const WelcomeView: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="flex-1 flex flex-col items-center justify-center max-w-2xl mx-auto text-center space-y-8 animate-in fade-in zoom-in duration-500">
      <div className="space-y-4">
        <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-foreground">
          你的专属 <span className="text-primary">情感树洞</span>
        </h2>
        <p className="text-lg md:text-xl text-muted-foreground leading-relaxed">
          我在这里倾听、理解并陪伴你度过每一个情绪起伏的时刻。没有评判，只有共情与陪伴。
        </p>
      </div>

      <button
        onClick={() => navigate('/chat')}
        className="group relative inline-flex items-center gap-3 px-8 py-4 bg-primary text-primary-foreground rounded-full text-lg font-medium overflow-hidden transition-transform hover:scale-105 active:scale-95 shadow-lg shadow-primary/25"
      >
        <span className="relative z-10 flex items-center gap-2">
          开启对话
          <MessageSquare className="group-hover:translate-x-1 transition-transform" size={20} />
        </span>
      </button>
    </div>
  );
};
