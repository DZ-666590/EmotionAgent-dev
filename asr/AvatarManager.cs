using UnityEngine;
using System;
using System.Collections.Generic;

/**
 * AvatarManager.cs
 * 挂载在 Unity 场景中的一个 GameObject 上（名称必须为 "AvatarManager"）
 * 支持两种驱动模式：
 * 1. Blendshape 模式 (推荐)：驱动 ARKit 52 个表情基
 * 2. Vertex 模式：直接更新 Mesh 顶点（需顶点数匹配）
 */
public class AvatarManager : MonoBehaviour
{
    [Header("Target Mesh Configuration")]
    public SkinnedMeshRenderer targetRenderer; // 拖入数字人的 SkinnedMeshRenderer
    
    [Header("Coordinate Mapping (Vertex Mode Only)")]
    public bool flipZ = true;  
    public bool flipX = false; 

    [Header("Blendshape Mapping")]
    [Tooltip("ARKit 52 个表情基的名字列表，需与后端顺序一致")]
    public string[] blendShapeNames = new string[] {
        "eyeBlinkLeft", "eyeLookDownLeft", "eyeLookInLeft", "eyeLookOutLeft", "eyeLookUpLeft",
        "eyeSquintLeft", "eyeWideLeft", "eyeBlinkRight", "eyeLookDownRight", "eyeLookInRight",
        "eyeLookOutRight", "eyeLookUpRight", "eyeSquintRight", "eyeWideRight", "jawForward",
        "jawLeft", "jawRight", "jawOpen", "mouthClose", "mouthFunnel", "mouthPucker",
        "mouthLeft", "mouthRight", "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft",
        "mouthFrownRight", "mouthDimpleLeft", "mouthDimpleRight", "mouthStretchLeft",
        "mouthStretchRight", "mouthRollLower", "mouthRollUpper", "mouthShrugLower",
        "mouthShrugUpper", "mouthPressLeft", "mouthPressRight", "mouthLowerDownLeft",
        "mouthLowerDownRight", "mouthUpperUpLeft", "mouthUpperUpRight", "browDownLeft",
        "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight", "cheekPuff",
        "cheekSquintLeft", "cheekSquintRight", "noseSneerLeft", "noseSneerRight", "tongueOut"
    };

    private Mesh deformingMesh;
    private Vector3[] vertices;
    private bool isInitialized = false;
    private Dictionary<string, int> bsIndexMap = new Dictionary<string, int>();

    void Start()
    {
        InitializeAvatar();
    }

    private void InitializeAvatar()
    {
        if (targetRenderer == null)
        {
            targetRenderer = GetComponentInChildren<SkinnedMeshRenderer>();
        }

        if (targetRenderer != null)
        {
            try 
            {
                // 初始化 Blendshape 索引映射
                Mesh sharedMesh = targetRenderer.sharedMesh;
                bsIndexMap.Clear();
                for (int i = 0; i < sharedMesh.blendShapeCount; i++)
                {
                    string bsName = sharedMesh.GetBlendShapeName(i);
                    // 某些模型可能有前缀 (e.g. "Body.jawOpen")，这里取后半部分
                    string cleanName = bsName.Contains(".") ? bsName.Substring(bsName.LastIndexOf('.') + 1) : bsName;
                    
                    // 1. 直接匹配
                    bsIndexMap[cleanName] = i;
                    
                    // 2. 模糊匹配 (处理 Arnold 模型的 _L / _R 后缀)
                    // ARKit "eyeBlinkLeft" -> Arnold "eyeBlink_L"
                    if (cleanName.EndsWith("_L")) bsIndexMap[cleanName.Replace("_L", "Left")] = i;
                    if (cleanName.EndsWith("_R")) bsIndexMap[cleanName.Replace("_R", "Right")] = i;
                    
                    // 3. 处理首字母大小写 (ARKit "jawOpen" -> Arnold "JawOpen")
                    string camelName = char.ToLower(cleanName[0]) + cleanName.Substring(1);
                    if (!bsIndexMap.ContainsKey(camelName)) bsIndexMap[camelName] = i;
                }

                // 初始化 Vertex 模式所需的副本
                deformingMesh = Instantiate(sharedMesh);
                deformingMesh.name = "A2F_Dynamic_Mesh";
                targetRenderer.sharedMesh = deformingMesh;
                vertices = deformingMesh.vertices;
                
                isInitialized = true;
                Debug.Log($"[AvatarManager] Initialized. BS Count: {sharedMesh.blendShapeCount}, Vertex Count: {vertices.Length}");
            }
            catch (Exception e)
            {
                Debug.LogError("[AvatarManager] Initialization failed: " + e.Message);
            }
        }
        else
        {
            Debug.LogError("[AvatarManager] SkinnedMeshRenderer not found!");
        }
    }

    /**
     * 由 React 通过 sendMessage("AvatarManager", "UpdateGeometry", dataString) 调用
     * @param dataString: "is_bs:1|0.1,0.2,..." 或 "is_bs:0|x1,y1,z1..."
     */
    public void UpdateGeometry(string dataString)
    {
        if (!isInitialized)
        {
            InitializeAvatar();
            if (!isInitialized) return;
        }

        if (string.IsNullOrEmpty(dataString)) return;

        try
        {
            // 解析协议格式
            bool isBlendshape = dataString.StartsWith("is_bs:1|");
            string content = isBlendshape ? dataString.Substring(8) : (dataString.StartsWith("is_bs:0|") ? dataString.Substring(8) : dataString);
            string[] parts = content.Split(',');

            if (isBlendshape)
            {
                UpdateBlendshapes(parts);
            }
            else
            {
                UpdateVertices(parts);
            }
        }
        catch (Exception)
        {
            // 避免高频报错
        }
    }

    private void UpdateBlendshapes(string[] weights)
    {
        int count = Math.Min(weights.Length, blendShapeNames.Length);
        for (int i = 0; i < count; i++)
        {
            float weight = float.Parse(weights[i]) * 100f; // Unity 使用 0-100
            string bsName = blendShapeNames[i];
            
            if (bsIndexMap.TryGetValue(bsName, out int index))
            {
                targetRenderer.SetBlendShapeWeight(index, weight);
            }
        }
    }

    private void UpdateVertices(string[] parts)
    {
        int incomingVertexCount = parts.Length / 3;
        int processCount = Math.Min(incomingVertexCount, vertices.Length);

        for (int i = 0; i < processCount; i++)
        {
            float x = float.Parse(parts[i * 3]);
            float y = float.Parse(parts[i * 3 + 1]);
            float z = float.Parse(parts[i * 3 + 2]);
            
            float finalX = flipX ? -x : x;
            float finalZ = flipZ ? -z : z;
            
            vertices[i] = new Vector3(finalX, y, finalZ);
        }

        deformingMesh.vertices = vertices;
        deformingMesh.UploadMeshData(false);
    }
}
