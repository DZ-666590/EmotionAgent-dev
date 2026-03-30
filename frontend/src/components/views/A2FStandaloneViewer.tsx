import React, { useRef, useEffect, useState, useCallback } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ARKit 52 Blendshape 标准顺序
const ARKIT_BLENDSHAPES = [
  'eyeBlinkLeft', 'eyeLookDownLeft', 'eyeLookInLeft', 'eyeLookOutLeft', 'eyeLookUpLeft',
  'eyeSquintLeft', 'eyeWideLeft', 'eyeBlinkRight', 'eyeLookDownRight', 'eyeLookInRight',
  'eyeLookOutRight', 'eyeLookUpRight', 'eyeSquintRight', 'eyeWideRight', 'jawForward',
  'jawLeft', 'jawRight', 'jawOpen', 'mouthClose', 'mouthFunnel', 'mouthPucker',
  'mouthLeft', 'mouthRight', 'mouthSmileLeft', 'mouthSmileRight', 'mouthFrownLeft',
  'mouthFrownRight', 'mouthDimpleLeft', 'mouthDimpleRight', 'mouthStretchLeft',
  'mouthStretchRight', 'mouthRollLower', 'mouthRollUpper', 'mouthShrugLower',
  'mouthShrugUpper', 'mouthPressLeft', 'mouthPressRight', 'mouthLowerDownLeft',
  'mouthLowerDownRight', 'mouthUpperUpLeft', 'mouthUpperUpRight', 'browDownLeft',
  'browDownRight', 'browInnerUp', 'browOuterUpLeft', 'browOuterUpRight', 'cheekPuff',
  'cheekSquintLeft', 'cheekSquintRight', 'noseSneerLeft', 'noseSneerRight', 'tongueOut',
];

const A2FStandaloneViewer: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [frames, setFrames] = useState<number[][]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const meshRef = useRef<THREE.SkinnedMesh | null>(null);
  const morphMapRef = useRef<Map<string, number>>(new Map());
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const animationFrameRef = useRef<number>(0);

  // 初始化场景
  useEffect(() => {
    if (!containerRef.current) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050505);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, containerRef.current.clientWidth / containerRef.current.clientHeight, 0.1, 100);
    camera.position.set(0, 0, 0.6);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0, 0);
    controls.enableDamping = true;

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(1, 1, 2);
    scene.add(directionalLight);

    // 加载模型
    const loader = new GLTFLoader();
    loader.load('/models/avatar.glb', (gltf) => {
      gltf.scene.traverse((child) => {
        if (child instanceof THREE.SkinnedMesh && child.morphTargetDictionary) {
          meshRef.current = child;
          // 建立映射
          ARKIT_BLENDSHAPES.forEach((name) => {
            const idx = child.morphTargetDictionary![name] ?? child.morphTargetDictionary![name.toLowerCase()];
            if (idx !== undefined) morphMapRef.current.set(name, idx);
          });
        }
      });
      
      // 自动居中
      const box = new THREE.Box3().setFromObject(gltf.scene);
      const center = box.getCenter(new THREE.Vector3());
      gltf.scene.position.sub(center);
      scene.add(gltf.scene);
      setIsLoading(false);
    });

    // 加载动画数据
    fetch('/mouth_animation.json')
      .then(res => res.json())
      .then(data => setFrames(data))
      .catch(err => console.error("Failed to load animation:", err));

    const animate = () => {
      animationFrameRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(animationFrameRef.current);
      renderer.dispose();
      if (containerRef.current) containerRef.current.removeChild(renderer.domElement);
    };
  }, []);

  // 播放逻辑
  const handlePlay = () => {
    if (!audioRef.current || frames.length === 0 || !meshRef.current) return;
    
    setIsPlaying(true);
    audioRef.current.currentTime = 0;
    audioRef.current.play();

    const startTime = performance.now();
    const fps = 60; // A2F 默认 60fps

    const updateAnimation = () => {
      if (!isPlaying) return;
      const elapsed = (performance.now() - startTime) / 1000;
      const frameIdx = Math.floor(elapsed * fps);

      if (frameIdx < frames.length) {
        const frame = frames[frameIdx];
        const mesh = meshRef.current!;
        
        ARKIT_BLENDSHAPES.forEach((name, i) => {
          const morphIdx = morphMapRef.current.get(name);
          if (morphIdx !== undefined) {
            mesh.morphTargetInfluences![morphIdx] = frame[i];
          }
        });
        requestAnimationFrame(updateAnimation);
      } else {
        setIsPlaying(false);
      }
    };
    requestAnimationFrame(updateAnimation);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-zinc-950 p-8">
      <div className="relative w-full max-w-4xl aspect-video bg-zinc-900 rounded-3xl overflow-hidden shadow-2xl border border-zinc-800">
        <div ref={containerRef} className="w-full h-full" />
        
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-zinc-900/80 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-zinc-400 font-medium">加载数字人模型...</p>
            </div>
          </div>
        )}

        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-4 px-6 py-4 bg-zinc-900/90 backdrop-blur-xl rounded-2xl border border-white/10 shadow-2xl">
          <audio ref={audioRef} src="/test_audio.wav" onEnded={() => setIsPlaying(false)} />
          
          <button
            onClick={handlePlay}
            disabled={isPlaying || isLoading}
            className="flex items-center gap-3 px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 text-white rounded-xl font-bold transition-all transform active:scale-95 shadow-lg shadow-blue-500/20"
          >
            {isPlaying ? (
              <>
                <div className="flex gap-1 items-end h-4">
                  <div className="w-1 bg-white animate-bounce" style={{animationDuration: '0.6s'}} />
                  <div className="w-1 bg-white animate-bounce" style={{animationDuration: '0.8s'}} />
                  <div className="w-1 bg-white animate-bounce" style={{animationDuration: '0.5s'}} />
                </div>
                <span>播放中...</span>
              </>
            ) : (
              <>
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
                  <path d="M8 5v14l11-7z" />
                </svg>
                <span>点击预览动画</span>
              </>
            )}
          </button>
          
          <div className="h-8 w-px bg-zinc-800" />
          
          <div className="flex flex-col">
            <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">当前帧数据</span>
            <span className="text-sm text-zinc-300 font-mono">{frames.length} Frames Loaded</span>
          </div>
        </div>
      </div>
      
      <p className="mt-6 text-zinc-500 text-sm">
        数据来源: <code className="text-blue-400">public/mouth_animation.json</code> (A2F+A2E 驱动)
      </p>
    </div>
  );
};

export default A2FStandaloneViewer;
