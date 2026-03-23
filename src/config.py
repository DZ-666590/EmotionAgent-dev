from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    应用全局配置。
    从环境变量（.env文件）加载系统参数，包括模型配置、API密钥等。
    """
    app_name: str = "Emotional Companion API"
    app_env: str = "development"
    
    # LiteLLM/DeepSeek 设置
    litellm_model: str = "deepseek/deepseek-chat"
    api_key: Optional[str] = None
    
    # 提供商设置
    temperature: float = 0.7
    max_tokens: int = 1000

    # 知识库设置
    knowledge_enabled: bool = True
    knowledge_top_k: int = 3
    knowledge_max_excerpt_chars: int = 320
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
