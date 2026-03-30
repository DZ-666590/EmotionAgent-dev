using UnityEngine;
using System;
using System.Collections.Generic;

/**
 * AvatarManager.cs
 * [Industry Standard ARKit Edition] 
 * 适配 Apple ARKit 52 路行业标准顺序
 */
public class AvatarManager : MonoBehaviour
{
    [Header("Target Rendering")]
    public SkinnedMeshRenderer targetRenderer; 
    
    [Header("Standard ARKit 52 Channels")]
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

    private bool isInitialized = false;
    private Dictionary<string, int> bsIndexMap = new Dictionary<string, int>();
    private float lastUpdateTime = 0f;

    void Start() { InitializeAvatar(); }

    private void InitializeAvatar()
    {
        if (targetRenderer == null) targetRenderer = GetComponentInChildren<SkinnedMeshRenderer>();
        if (targetRenderer != null)
        {
            Mesh sharedMesh = targetRenderer.sharedMesh;
            bsIndexMap.Clear();
            for (int i = 0; i < sharedMesh.blendShapeCount; i++)
            {
                string bsName = sharedMesh.GetBlendShapeName(i);
                string cleanName = bsName.Contains(".") ? bsName.Substring(bsName.LastIndexOf('.') + 1) : bsName;
                bsIndexMap[cleanName] = i;
            }
            isInitialized = true;
            Debug.Log($"[AvatarManager] Industry Standard Initialized. Mapping {sharedMesh.blendShapeCount} shapes.");
        }
    }

    public void UpdateGeometry(string dataString)
    {
        if (!isInitialized) InitializeAvatar();
        if (string.IsNullOrEmpty(dataString)) return;

        try {
            if (dataString.StartsWith("is_bs:1|")) {
                string[] weights = dataString.Substring(8).Split(',');
                lastUpdateTime = Time.time;

                int count = Math.Min(weights.Length, blendShapeNames.Length);
                for (int i = 0; i < count; i++) {
                    if (float.TryParse(weights[i], out float val)) {
                        string targetName = blendShapeNames[i];
                        if (bsIndexMap.TryGetValue(targetName, out int index)) {
                            float targetWeight = val * 100f;
                            float current = targetRenderer.GetBlendShapeWeight(index);
                            targetRenderer.SetBlendShapeWeight(index, Mathf.Lerp(current, targetWeight, 0.6f));
                        }
                    }
                }
            }
        } catch (Exception) {}
    }

    void Update()
    {
        if (Time.time - lastUpdateTime > 0.25f)
        {
            for (int i = 0; i < blendShapeNames.Length; i++) {
                if (bsIndexMap.TryGetValue(blendShapeNames[i], out int index)) {
                    float current = targetRenderer.GetBlendShapeWeight(index);
                    if (current > 0.1f) targetRenderer.SetBlendShapeWeight(index, Mathf.Lerp(current, 0, 0.15f));
                }
            }
        }
    }
}
