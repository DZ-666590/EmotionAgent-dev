import React, { useCallback, useEffect } from "react";
import { Unity, useUnityContext } from "react-unity-webgl";
import { useA2FWebSocket } from "../../hooks/useA2FWebSocket";

interface Avatar3DProps {
  className?: string;
  /** Unity 构建包的基础路径 (e.g. "/unity/build") */
  buildPath?: string;
}

/**
 * Unity 驱动的 3D 数字人组件
 * 替换了原有的 Three.js 点云方案，支持更真实的面部渲染
 */
export const Avatar3D: React.FC<Avatar3DProps> = ({
  className = "",
  buildPath = "/unity/build",
}) => {
  const { unityProvider, sendMessage, isLoaded, progression } = useUnityContext({
    loaderUrl: `${buildPath}/project.loader.js`,
    dataUrl: `${buildPath}/project.data`,
    frameworkUrl: `${buildPath}/project.framework.js`,
    codeUrl: `${buildPath}/project.wasm`,
  });

  // 处理从 A2F 接收到的数据并转发给 Unity
  const handleFrame = useCallback(
    (frame: { geometry: number[]; is_blendshape?: boolean }) => {
      if (isLoaded) {
        // 构造新协议：is_bs:1|0.1,0.2... 或 is_bs:0|x,y,z...
        const prefix = `is_bs:${frame.is_blendshape ? "1" : "0"}|`;
        const dataString = prefix + frame.geometry.join(",");
        sendMessage("AvatarManager", "UpdateGeometry", dataString);
      }
    },
    [isLoaded, sendMessage]
  );

  const { isConnected } = useA2FWebSocket({
    autoConnect: true,
    onFrame: handleFrame,
  });

  return (
    <div className={`relative w-full h-full min-h-[400px] flex items-center justify-center bg-black/20 rounded-lg overflow-hidden ${className}`}>
      {!isLoaded && (
        <div className="absolute inset-0 flex flex-col items-center justify-center z-20 bg-gray-900/80">
          <div className="w-48 h-2 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-500 transition-all duration-300" 
              style={{ width: `${Math.round(progression * 100)}%` }}
            />
          </div>
          <p className="mt-4 text-white text-sm font-medium">
            Loading Unity Digital Human... {Math.round(progression * 100)}%
          </p>
        </div>
      )}

      <Unity
        unityProvider={unityProvider}
        style={{ width: "100%", height: "100%" }}
        devicePixelRatio={window.devicePixelRatio}
      />

      {/* 状态指示器 */}
      <div className="absolute top-3 right-3 flex items-center gap-2 px-2 py-1 bg-black/40 rounded-full backdrop-blur-md z-10">
        <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500 animate-pulse"}`} />
        <span className="text-[10px] text-white/80 font-mono uppercase tracking-wider">
          {isConnected ? "Stream Active" : "Waiting for A2F"}
        </span>
      </div>
    </div>
  );
};

export default Avatar3D;
