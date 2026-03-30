import React, { useRef, useEffect, useCallback, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { useA2FWebSocket, BlendshapeFrame } from '../../hooks/useA2FWebSocketNew';

// ARKit 52 Blendshape 标准顺序 (与 SDK 输出一致)
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

interface DigitalHumanProps {
  className?: string;
  /** GLB/GLTF 模型路径 (需要包含 ARKit morph targets) */
  modelUrl?: string;
  /** 是否显示调试信息 */
  debug?: boolean;
}

/**
 * Three.js 驱动的数字人组件
 * 通过 WebSocket 接收 A2F blendshape 权重，实时驱动面部动画
 */
export const DigitalHuman: React.FC<DigitalHumanProps> = ({
  className = '',
  modelUrl = '/models/avatar.glb',
  debug = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const meshRef = useRef<THREE.SkinnedMesh | null>(null);
  const frameIdRef = useRef<number>(0);
  const morphTargetMapRef = useRef<Map<string, number>>(new Map());

  const [isLoading, setIsLoading] = useState(true);
  const [loadProgress, setLoadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [morphTargetCount, setMorphTargetCount] = useState(0);

  // 处理 blendshape 帧
  const handleFrame = useCallback((frame: BlendshapeFrame) => {
    const mesh = meshRef.current;
    if (!mesh?.morphTargetInfluences || !mesh.morphTargetDictionary) return;

    const influences = mesh.morphTargetInfluences;
    const dictionary = mesh.morphTargetDictionary;
    const map = morphTargetMapRef.current;

    // 应用权重到对应的 morph targets
    frame.weights.forEach((weight, index) => {
      if (index >= ARKIT_BLENDSHAPES.length) return;

      const shapeName = ARKIT_BLENDSHAPES[index];
      
      // 使用缓存的映射
      let morphIndex = map.get(shapeName);
      if (morphIndex === undefined) {
        // 尝试查找匹配的 morph target (支持不同命名约定)
        morphIndex = dictionary[shapeName] 
          ?? dictionary[shapeName.toLowerCase()]
          ?? dictionary[`blendShape.${shapeName}`]
          ?? dictionary[`ARKit_${shapeName}`];
        
        if (morphIndex !== undefined) {
          map.set(shapeName, morphIndex);
        }
      }

      if (morphIndex !== undefined && morphIndex < influences.length) {
        // 平滑插值，避免抖动
        influences[morphIndex] = THREE.MathUtils.lerp(
          influences[morphIndex],
          Math.max(0, Math.min(1, weight)),  // clamp to [0, 1]
          0.5  // 插值系数
        );
      }
    });
  }, []);

  const { isConnected } = useA2FWebSocket({
    autoConnect: true,
    onFrame: handleFrame,
  });

  // 初始化 Three.js 场景
  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // 场景
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    sceneRef.current = scene;

    // 相机
    const camera = new THREE.PerspectiveCamera(35, width / height, 0.1, 100);
    camera.position.set(0, 0.1, 0.8);  // 适合面部特写
    cameraRef.current = camera;

    // 渲染器
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 轨道控制器
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 0.3;
    controls.maxDistance = 2;
    controls.enablePan = false;
    controlsRef.current = controls;

    // 光照
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
    keyLight.position.set(1, 1, 1);
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0xffffff, 0.4);
    fillLight.position.set(-1, 0.5, 0.5);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0xaaccff, 0.3);
    rimLight.position.set(0, 0.5, -1);
    scene.add(rimLight);

    // 加载模型
    const loader = new GLTFLoader();
    loader.load(
      modelUrl,
      (gltf) => {
        // 查找带有 morph targets 的 mesh
        gltf.scene.traverse((child) => {
          if (child instanceof THREE.SkinnedMesh && child.morphTargetDictionary) {
            meshRef.current = child;
            setMorphTargetCount(Object.keys(child.morphTargetDictionary).length);
            
            if (debug) {
              console.log('[DigitalHuman] Morph targets found:', Object.keys(child.morphTargetDictionary));
            }
          }
        });

        // 居中模型
        const box = new THREE.Box3().setFromObject(gltf.scene);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        
        gltf.scene.position.sub(center);
        gltf.scene.position.y += size.y * 0.3;  // 略微上移，聚焦面部

        scene.add(gltf.scene);
        setIsLoading(false);
      },
      (progress) => {
        if (progress.total > 0) {
          setLoadProgress(Math.round((progress.loaded / progress.total) * 100));
        }
      },
      (err) => {
        console.error('[DigitalHuman] Model load error:', err);
        setError('无法加载 3D 模型');
        setIsLoading(false);
      }
    );

    // 动画循环
    const animate = () => {
      frameIdRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // 窗口大小变化
    const handleResize = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // 清理
    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(frameIdRef.current);
      controls.dispose();
      renderer.dispose();
      container.removeChild(renderer.domElement);
    };
  }, [modelUrl, debug]);

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full min-h-[300px] bg-gradient-to-b from-slate-900 to-slate-800 rounded-xl overflow-hidden ${className}`}
    >
      {/* 加载状态 */}
      {isLoading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center z-20 bg-slate-900/90 backdrop-blur-sm">
          <div className="w-48 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-300 ease-out"
              style={{ width: `${loadProgress}%` }}
            />
          </div>
          <p className="mt-3 text-white/80 text-sm font-medium">
            加载数字人模型... {loadProgress}%
          </p>
        </div>
      )}

      {/* 错误状态 */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center z-20 bg-slate-900/90">
          <div className="text-center">
            <p className="text-red-400 text-sm">{error}</p>
            <p className="text-white/50 text-xs mt-2">请确保模型文件存在于 public/models/</p>
          </div>
        </div>
      )}

      {/* 状态指示器 */}
      <div className="absolute top-3 right-3 flex items-center gap-2 px-3 py-1.5 bg-black/50 rounded-full backdrop-blur-md z-10">
        <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-amber-500 animate-pulse'}`} />
        <span className="text-[10px] text-white/80 font-mono uppercase tracking-wider">
          {isConnected ? 'A2F Active' : 'Waiting'}
        </span>
      </div>

      {/* 调试信息 */}
      {debug && !isLoading && (
        <div className="absolute bottom-3 left-3 px-3 py-2 bg-black/60 rounded-lg text-xs text-white/70 font-mono z-10">
          <div>Morph Targets: {morphTargetCount}</div>
          <div>WebSocket: {isConnected ? 'Connected' : 'Disconnected'}</div>
        </div>
      )}
    </div>
  );
};

export default DigitalHuman;
