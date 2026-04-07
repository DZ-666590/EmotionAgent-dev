import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { useTTSStore } from "../../store/ttsStore";

interface Avatar3DProps {
  className?: string;
}

const ARKIT_BS = [
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
  'cheekSquintLeft', 'cheekSquintRight', 'noseSneerLeft', 'noseSneerRight', 'tongueOut'
];

export const Avatar3D: React.FC<Avatar3DProps> = ({ className = "" }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const meshRef = useRef<THREE.Mesh | null>(null);
  const skeletonRef = useRef<THREE.Skeleton | null>(null);
  const morphMapRef = useRef<Map<string, number>>(new Map());
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const { audioElement, isPlaying, offlineWeights, emotion } = useTTSStore();
  
  // 使用 Ref 同步 Store 状态到渲染循环
  const stateRef = useRef({ isPlaying, offlineWeights, audioElement, emotion });
  stateRef.current.isPlaying = isPlaying;
  stateRef.current.offlineWeights = offlineWeights;
  stateRef.current.audioElement = audioElement;
  stateRef.current.emotion = emotion;

  // 状态变量用于 Idle Animation
  const blinkTimerRef = useRef(0);
  const nextBlinkTimeRef = useRef(Math.random() * 3 + 2);
  const blinkDurationRef = useRef(0.15);

  useEffect(() => {
    if (!containerRef.current) return;
    
    console.log("[Avatar3D] 组件挂载，初始化渲染引擎...");

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x222222);

    const camera = new THREE.PerspectiveCamera(35, width / height, 0.1, 100);
    // 固定用户调整后的理想视角
    camera.position.set(-0.01, 0.84, 0.60);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    
    // 调试用：将变量挂载到全局 (调试完成后可删除)
    (window as any).camera = camera;
    (window as any).scene = scene;

    // 清理旧的 canvas 避免重影 (Strict Mode)
    if (containerRef.current) {
      containerRef.current.innerHTML = "";
      containerRef.current.appendChild(renderer.domElement);
    }

    const controls = new OrbitControls(camera, renderer.domElement);
    (window as any).controls = controls;
    controls.enableDamping = true;
    // 固定用户调整后的目标观察点
    controls.target.set(-0.01, 0.84, 0);

    const ambientLight = new THREE.AmbientLight(0xffffff, 1.5);
    scene.add(ambientLight);
    
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.5);
    dirLight.position.set(5, 5, 5);
    scene.add(dirLight);

    // 添加点光源增强面部立体感
    const pointLight = new THREE.PointLight(0xffffff, 2.0, 10);
    pointLight.position.set(0, 1, 2);
    scene.add(pointLight);

    const loader = new GLTFLoader();
    console.log("[Avatar3D] 开始加载模型...");
    loader.load(
      "/models/avatar.glb",
      (gltf) => {
        console.log("[Avatar3D] 模型文件读取成功！对象结构:", gltf);
        
        gltf.scene.traverse((child) => {
          if ((child as THREE.SkinnedMesh).isSkinnedMesh) {
            const sm = child as THREE.SkinnedMesh;
            if (sm.skeleton) {
              skeletonRef.current = sm.skeleton;
              console.log("[Avatar3D] 发现骨骼:", sm.skeleton.bones.map(b => b.name));
            }
          }
          if ((child as THREE.Mesh).isMesh) {
            console.log("[Avatar3D] 发现网格:", child.name);
            const mesh = child as THREE.Mesh;
            if (mesh.morphTargetDictionary) {
              console.log("[Avatar3D] 发现 MorphTargets:", Object.keys(mesh.morphTargetDictionary).length);
              meshRef.current = mesh;
              ARKIT_BS.forEach((name) => {
                const idx = mesh.morphTargetDictionary![name] || mesh.morphTargetDictionary![name.toLowerCase()];
                if (idx !== undefined) morphMapRef.current.set(name, idx);
              });
            }
          }
        });

        const box = new THREE.Box3().setFromObject(gltf.scene);
        const center = box.getCenter(new THREE.Vector3());
        gltf.scene.position.sub(center);
        scene.add(gltf.scene);
        setLoadingProgress(100);
      },
      (xhr) => {
        setLoadingProgress(Math.round((xhr.loaded / xhr.total) * 100));
      },
      (err) => {
        console.error("Failed to load model:", err);
        setError("模型加载失败");
      }
    );

    let animateId: number;
    const animate = () => {
      animateId = requestAnimationFrame(animate);
      controls.update();

      const time = performance.now() * 0.001;
      const { isPlaying: activePlaying, offlineWeights: activeWeights, audioElement: activeAudio, emotion: activeEmotion } = stateRef.current;

      // --- 0. Skeleton Animation (Nodding & Breathing) ---
      if (skeletonRef.current) {
        // 呼吸感：脊柱微动
        const spine = skeletonRef.current.getBoneByName('Spine') || skeletonRef.current.getBoneByName('spine');
        if (spine) {
          spine.rotation.x = Math.sin(time * 0.8) * 0.01;
          spine.rotation.z = Math.cos(time * 0.5) * 0.005;
        }

        // 点头逻辑：基于口型张开度 (jawOpen) 的程序化反馈
        const neck = skeletonRef.current.getBoneByName('Neck') || skeletonRef.current.getBoneByName('neck');
        const head = skeletonRef.current.getBoneByName('Head') || skeletonRef.current.getBoneByName('head');
        
        if (head || neck) {
          const targetBone = head || neck;
          let nodAmount = 0;
          
          if (activePlaying && meshRef.current?.morphTargetInfluences) {
            const jawOpenIdx = morphMapRef.current.get('jawOpen');
            if (jawOpenIdx !== undefined) {
              const jawOpenVal = meshRef.current.morphTargetInfluences[jawOpenIdx];
              // 当大声说话（嘴张得大）时，产生微弱的头部随动
              nodAmount = jawOpenVal * 0.05 + Math.sin(time * 3) * 0.01 * jawOpenVal;
            }
          }
          
          // 叠加自然的微小头部晃动
          const idleSwayX = Math.sin(time * 1.2) * 0.01;
          const idleSwayY = Math.cos(time * 0.7) * 0.01;
          
          if (targetBone) {
            targetBone.rotation.x = THREE.MathUtils.lerp(targetBone.rotation.x, nodAmount + idleSwayX, 0.1);
            targetBone.rotation.y = THREE.MathUtils.lerp(targetBone.rotation.y, idleSwayY, 0.1);
          }
        }
      }

      if (meshRef.current) {
        // --- 1. Idle Animation & Emotions ---
        // 情感表现逻辑 (简单的 MorphTarget 叠加)
        let happyWeight = 0;
        let sadWeight = 0;
        if (activeEmotion === 'happy' || activeEmotion === 'joy') happyWeight = 0.5;
        if (activeEmotion === 'sad' || activeEmotion === 'sorrow') sadWeight = 0.5;

        const smileLeftIdx = morphMapRef.current.get('mouthSmileLeft');
        const smileRightIdx = morphMapRef.current.get('mouthSmileRight');
        const frownLeftIdx = morphMapRef.current.get('mouthFrownLeft');
        const frownRightIdx = morphMapRef.current.get('mouthFrownRight');

        if (smileLeftIdx !== undefined) meshRef.current.morphTargetInfluences![smileLeftIdx] = happyWeight;
        if (smileRightIdx !== undefined) meshRef.current.morphTargetInfluences![smileRightIdx] = happyWeight;
        if (frownLeftIdx !== undefined) meshRef.current.morphTargetInfluences![frownLeftIdx] = sadWeight;
        if (frownRightIdx !== undefined) meshRef.current.morphTargetInfluences![frownRightIdx] = sadWeight;
        
        // 自动眨眼
        blinkTimerRef.current += 1/60; 
        let blinkWeight = 0;
        if (blinkTimerRef.current > nextBlinkTimeRef.current) {
          const progress = (blinkTimerRef.current - nextBlinkTimeRef.current) / blinkDurationRef.current;
          if (progress < 1.0) {
            blinkWeight = Math.sin(progress * Math.PI);
          } else {
            blinkTimerRef.current = 0;
            // 悲伤时眨眼频率降低
            const baseInterval = Math.random() * 4 + 2;
            nextBlinkTimeRef.current = sadWeight > 0 ? baseInterval * 1.5 : baseInterval;
          }
        }

        const blinkLeftIdx = morphMapRef.current.get('eyeBlinkLeft');
        const blinkRightIdx = morphMapRef.current.get('eyeBlinkRight');
        if (blinkLeftIdx !== undefined) meshRef.current.morphTargetInfluences![blinkLeftIdx] = blinkWeight;
        if (blinkRightIdx !== undefined) meshRef.current.morphTargetInfluences![blinkRightIdx] = blinkWeight;

        // --- 2. 语音驱动逻辑 ---
        if (activePlaying) {
          const audioOffset = (activeAudio?.currentTime || 0) + 0.15; 
          
          if (activeWeights && activeWeights.length > 0) {
            const fps = 30;
            const targetFrameIndex = audioOffset * fps;
            const i1 = Math.floor(targetFrameIndex);
            const i2 = Math.min(i1 + 1, activeWeights.length - 1);
            const alpha = targetFrameIndex - i1;

            if (i1 >= 0 && i1 < activeWeights.length) {
              const f1 = activeWeights[i1];
              const f2 = activeWeights[i2];
              
              ARKIT_BS.forEach((name, i) => {
                if (name === 'eyeBlinkLeft' || name === 'eyeBlinkRight') return;
                // 跳过受情感控制的 MorphTargets，避免冲突
                if (['mouthSmileLeft', 'mouthSmileRight', 'mouthFrownLeft', 'mouthFrownRight'].includes(name)) return;

                const mIdx = morphMapRef.current.get(name);
                if (mIdx !== undefined) {
                  const w1 = f1.weights[i] !== undefined ? f1.weights[i] : 0;
                  const w2 = f2.weights[i] !== undefined ? f2.weights[i] : 0;
                  let interpolated = THREE.MathUtils.lerp(w1, w2, alpha);
                  
                  let gain = 1.0; 
                  // 去掉先前针对特定权重的夸张增益，恢复默认比例
                  /*
                  if (name === 'jawOpen') gain = 1.2;
                  if (name === 'mouthFunnel') gain = 1.1;
                  if (name.includes('mouthLower')) gain = 0.8;
                  */
                  
                  interpolated *= gain;
                  // 移除之前的 breathing 逻辑，现在由骨骼驱动实现更自然的身体微动
                  // if (name === 'jawOpen') interpolated += breathing;

                  interpolated = Math.min(Math.max(interpolated, 0), 1.0);
                  meshRef.current!.morphTargetInfluences![mIdx] = interpolated;
                }
              });
            }
          }
        } else {
          morphMapRef.current.forEach((mIdx, name) => {
            if (name === 'eyeBlinkLeft' || name === 'eyeBlinkRight') return;
            if (meshRef.current!.morphTargetInfluences![mIdx] > 0) {
              meshRef.current!.morphTargetInfluences![mIdx] *= 0.8;
            }
          });
        }
      }

      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!containerRef.current) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      console.log("[Avatar3D] 组件卸载，清理资源...");
      
      // 停止动画循环
      cancelAnimationFrame(animateId);
      
      if (containerRef.current) {
        // 安全清理 DOM，避免 NotFoundError
        if (renderer.domElement && containerRef.current.contains(renderer.domElement)) {
          containerRef.current.removeChild(renderer.domElement);
        }
      }
      
      // 彻底释放内存
      renderer.dispose();
      scene.traverse((object) => {
        if ((object as THREE.Mesh).isMesh) {
          const mesh = object as THREE.Mesh;
          mesh.geometry.dispose();
          if (Array.isArray(mesh.material)) {
            mesh.material.forEach(m => m.dispose());
          } else {
            mesh.material.dispose();
          }
        }
      });
    };
  }, []);


  return (
    <div 
      ref={containerRef}
      className={`relative w-full h-full min-h-[400px] bg-gradient-to-b from-black/20 to-black/40 rounded-3xl overflow-hidden ${className}`}
    />
  );
};

export default Avatar3D;
