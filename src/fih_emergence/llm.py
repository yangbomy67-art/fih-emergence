"""
LLM Client - 大语言模型客户端封装

支持多种模型提供商：
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini/GLM)
- Moonshot (Kimi)
- 本地模型 (Ollama)

配置优先级：
1. 环境变量
2. .env 文件
3. 默认值
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


@dataclass
class LLMResponse:
    """LLM 响应"""

    content: str
    model: str
    usage: dict = None
    raw_response: dict = None


class BaseLLMClient(ABC):
    """LLM 客户端基类"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "")
        self.model = model or os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """发送聊天请求"""
        pass

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """发送补全请求"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI 客户端"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = "gpt-3.5-turbo"):
        super().__init__(api_key, base_url, model)
        self.base_url = base_url or "https://api.openai.com/v1"

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048, **kwargs) -> LLMResponse:
        # 简化实现
        return LLMResponse(content="[Mock] OpenAI Response", model=self.model)

    async def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs) -> LLMResponse:
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, temperature, max_tokens, **kwargs)


class AnthropicClient(BaseLLMClient):
    """Anthropic (Claude) 客户端"""

    def __init__(self, api_key: str = None, model: str = "claude-3-haiku-20240307"):
        super().__init__(api_key, model=model)

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048, **kwargs) -> LLMResponse:
        return LLMResponse(content="[Mock] Claude Response", model=self.model)

    async def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs) -> LLMResponse:
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, temperature, max_tokens, **kwargs)


class MoonshotClient(BaseLLMClient):
    """Moonshot (Kimi) 客户端"""

    def __init__(self, api_key: str = None, model: str = "moonshot-v1-8k"):
        super().__init__(api_key, model=model)
        self.base_url = os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048, **kwargs) -> LLMResponse:
        return LLMResponse(content="[Mock] Kimi Response", model=self.model)

    async def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs) -> LLMResponse:
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, temperature, max_tokens, **kwargs)


class CustomClient(BaseLLMClient):
    """自定义 API 客户端（兼容 OpenAI 格式）"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        super().__init__(api_key, base_url, model)

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048, **kwargs) -> LLMResponse:
        """调用自定义 API"""
        import aiohttp
        
        if not self.api_key:
            return LLMResponse(content="[Mock] No API Key", model=self.model)
        
        if not self.base_url:
            return LLMResponse(content="[Mock] No API URL", model=self.model)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return LLMResponse(
                            content=f"[API Error {response.status}] {error_text[:200]}",
                            model=self.model,
                        )
                    
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    
                    return LLMResponse(
                        content=content,
                        model=self.model,
                        usage=usage,
                        raw_response=data,
                    )
        except Exception as e:
            return LLMResponse(content=f"[Error] {str(e)[:200]}", model=self.model)

    async def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs) -> LLMResponse:
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, temperature, max_tokens, **kwargs)


# 客户端工厂
LLM_PROVIDERS = {
    "openai": OpenAIClient,
    "anthropic": AnthropicClient,
    "moonshot": MoonshotClient,
    "custom": CustomClient,
}


def create_llm_client(
    provider: str = None,
    api_key: str = None,
    base_url: str | None = None,
    model: str = None,
) -> BaseLLMClient:
    """
    创建 LLM 客户端

    Args:
        provider: 提供商 (openai/anthropic/moonshot/custom)
        api_key: API 密钥
        base_url: API 地址
        model: 模型名称

    Returns:
        LLM 客户端实例
    """
    # 自动检测 provider
    if not provider:
        # 优先使用环境变量
        provider = os.getenv("LLM_PROVIDER", "custom")

    # 获取客户端类
    client_class = LLM_PROVIDERS.get(provider.lower())
    if not client_class:
        raise ValueError(f"Unknown provider: {provider}")

    return client_class(api_key=api_key, base_url=base_url, model=model)


# 预配置的客户端（用于不同角色）
def get_manager_client() -> BaseLLMClient:
    """Manager 角色使用的 LLM 客户端"""
    return create_llm_client(
        provider=os.getenv("MANAGER_PROVIDER", "custom"),
        model=os.getenv("MANAGER_MODEL", "glm-4-flash"),
    )


def get_proposer_client() -> BaseLLMClient:
    """Proposer 角色使用的 LLM 客户端"""
    return create_llm_client(
        provider=os.getenv("PROPOSER_PROVIDER", "custom"),
        model=os.getenv("PROPOSER_MODEL", "glm-4-flash"),
    )


def get_worker_client(worker_id: str = None) -> BaseLLMClient:
    """Worker 角色使用的 LLM 客户端"""
    # Worker_P 使用 glm-5.1, Worker_N 使用其他
    model = os.getenv("WORKER_MODEL", "glm-5.1")
    return create_llm_client(
        provider=os.getenv("WORKER_PROVIDER", "custom"),
        model=model,
    )


def get_auditor_client() -> BaseLLMClient:
    """Auditor 角色使用的 LLM 客户端"""
    return create_llm_client(
        provider=os.getenv("AUDITOR_PROVIDER", "custom"),
        model=os.getenv("AUDITOR_MODEL", "Qwen3-235B-A22B"),
    )
