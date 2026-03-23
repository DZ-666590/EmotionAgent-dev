from litellm import completion, acompletion
from ..config import settings
import json

class LiteLLMClient:
    """ 
    LLM 交互客户端。
    基于 LiteLLM 封装，提供对多模型后端的统一个调用接口，支持结构化输出和流式生成。
    """
    @classmethod
    async def acompletion_structured(cls, messages: list, response_format: dict) -> dict:
        """
        获取结构化 JSON 响应。
        
        Args:
            messages (list): 提示词内容列表。
            response_format (dict): 指定输出格式为 json_object。
            
        Returns:
            dict: 反序列化后的 JSON 字典。
        """                                                                              
        try:
            response = await acompletion(
                model=settings.litellm_model,
                messages=messages,
                api_key=settings.api_key,
                temperature=0.1,  # 降低随机性以获取稳定的结构化输出
                max_tokens=settings.max_tokens,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            # 运行时异常捕获
            raise RuntimeError(f"Failed structured completion: {str(e)}")

    @classmethod
    async def astream(cls, messages: list):
        """
        异步流式 Token 生成。
        
        Args:
            messages (list): 提示词内容列表。
            
        Yields:
            str: 逐个生成的文本令牌。
        """
        try:
            response = await acompletion(
                model=settings.litellm_model,
                messages=messages,
                api_key=settings.api_key,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
                stream=True
         )
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"Failed streaming completion: {str(e)}")
