import React, { useEffect, useRef } from 'react';
import { useAdminStore } from '../../store/adminStore';

const EMOTION_COLORS: Record<string, string> = {
  'joy': '255, 200, 0',
  'trust': '0, 200, 100',
  'fear': '100, 200, 255',
  'surprise': '0, 255, 200',
  'sadness': '0, 100, 255',
  'disgust': '150, 50, 255',
  'anger': '255, 50, 50',
  'anticipation': '255, 150, 0',
  'neutral': '150, 150, 150',
  'calm': '100, 220, 150'
};

class Bubble {
  x: number;
  y: number;
  radius: number;
  speedX: number;
  speedY: number;
  color: string;
  wobbleOffset: number;
  wobbleSpeed: number;

  constructor(canvasWidth: number, canvasHeight: number, color: string) {
    this.radius = Math.random() * 20 + 10;
    this.x = Math.random() * (canvasWidth - this.radius * 2) + this.radius;
    this.y = Math.random() * (canvasHeight - this.radius * 2) + this.radius;
    this.speedX = (Math.random() - 0.5) * 1.5;
    this.speedY = (Math.random() - 0.5) * 1.5;
    this.color = color;
    this.wobbleOffset = Math.random() * Math.PI * 2;
    this.wobbleSpeed = Math.random() * 0.05 + 0.01;
  }

  update(canvasWidth: number, canvasHeight: number) {
    this.x += this.speedX;
    this.y += this.speedY;

    if (this.x - this.radius < 0 || this.x + this.radius > canvasWidth) this.speedX *= -1;
    if (this.y - this.radius < 0 || this.y + this.radius > canvasHeight) this.speedY *= -1;

    this.wobbleOffset += this.wobbleSpeed;
  }

  draw(ctx: CanvasRenderingContext2D) {
    const wobble = Math.sin(this.wobbleOffset) * 5;
    
    const gradient = ctx.createRadialGradient(
      this.x, this.y, 0,
      this.x, this.y, this.radius + wobble
    );
    gradient.addColorStop(0, `rgba(${this.color}, 0.6)`);
    gradient.addColorStop(1, `rgba(${this.color}, 0)`);

    ctx.beginPath();
    ctx.arc(this.x, this.y, this.radius + wobble, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();
  }
}

export const EmotionCanvas: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const data = useAdminStore((state) => state.data);
  const bubblesRef = useRef<Bubble[]>([]);
  const animationRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = canvas.parentElement?.clientWidth || 300;
    let height = canvas.parentElement?.clientHeight || 300;
    canvas.width = width;
    canvas.height = height;

    const emotions = data?.emotions || ['neutral'];
    const intensity = data?.intensity || 3;
    const bubbleCount = Math.max(5, Math.min(30, Math.floor(intensity * 3)));

    bubblesRef.current = [];
    for (let i = 0; i < bubbleCount; i++) {
      const emotion = emotions[i % emotions.length].toLowerCase();
      const color = EMOTION_COLORS[emotion] || EMOTION_COLORS['neutral'];
      bubblesRef.current.push(new Bubble(width, height, color));
    }

    const animate = () => {
      ctx.clearRect(0, 0, width, height);
      bubblesRef.current.forEach(bubble => {
        bubble.update(width, height);
        bubble.draw(ctx);
      });
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    const handleResize = () => {
      if (!canvas.parentElement) return;
      width = canvas.parentElement.clientWidth;
      height = canvas.parentElement.clientHeight;
      canvas.width = width;
      canvas.height = height;
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationRef.current);
    };
  }, [data]);

  return (
    <canvas 
      ref={canvasRef} 
      className="absolute inset-0 w-full h-full mix-blend-screen filter blur-md"
    />
  );
};
