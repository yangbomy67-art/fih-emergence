"""
Config - 配置文件加载和管理

基于 config.yaml
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from fih_emergence.llm import BaseLLMClient, create_llm_client

# 默认配置路径
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


@dataclass
class ModelConfig:
    """模型配置"""

    provider: str = "custom"
    model: str = "glm-4-flash"
    api_url: str = ""  # API 端点 URL
    api_key: str = ""  # API 密钥（支持从环境变量加载）
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class ServerConfig:
    """服务配置"""

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False


@dataclass
class DatabaseConfig:
    """数据库配置"""

    path: str = "./data/fih_blackboard.db"
    auto_init: bool = True


@dataclass
class TaskConfig:
    """任务配置"""

    max_rounds: int = 20
    max_retry_per_round: int = 3
    human_timeout: int = 300


@dataclass
class EIConfig:
    """EI 评估配置"""

    result_ei_threshold: int = 15
    confidence_aggregation_threshold: int = 85
    scores_4d_threshold: int = 7


@dataclass
class InterruptConfig:
    # 弱势方重产: 正方>80% 且 反方<30% 或 反方>80% 且 正方<30%
    dominant_threshold: int = 80
    weak_threshold: int = 30
    no_fact_rounds_threshold: int = 3
    consecutive_same_output_threshold: int = 2


@dataclass
class ValleyConfig:
    """低谷穿越配置"""

    window_size: int = 3
    ei_low_threshold: int = 10
    no_fact_rounds_threshold: int = 3


@dataclass
class LoggingConfig:
    """日志配置"""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "./logs/fih_emergence.log"


@dataclass
class HumanGateConfig:
    """Human Gate 配置"""

    cli_mode: bool = True
    heartbeat_interval: int = 30
    max_reconnect_attempts: int = 5


@dataclass
class Config:
    """全局配置"""

    server: ServerConfig = field(default_factory=ServerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    task: TaskConfig = field(default_factory=TaskConfig)
    models: dict[str, ModelConfig] = field(default_factory=dict)
    ei: EIConfig = field(default_factory=EIConfig)
    interrupt: InterruptConfig = field(default_factory=InterruptConfig)
    valley: ValleyConfig = field(default_factory=ValleyConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    human_gate: HumanGateConfig = field(default_factory=HumanGateConfig)

    @classmethod
    def from_yaml(cls, path: str | Path = None) -> "Config":
        """从 YAML 文件加载配置"""
        if path is None:
            path = os.getenv("FIH_CONFIG_PATH", DEFAULT_CONFIG_PATH)

        path = Path(path)
        if not path.exists():
            # 返回默认配置
            return cls()

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return cls()

        # 解析各部分配置
        config = cls()

        if "server" in data:
            config.server = ServerConfig(**data["server"])

        if "database" in data:
            config.database = DatabaseConfig(**data["database"])

        if "task" in data:
            config.task = TaskConfig(**data["task"])

        if "models" in data:
            config.models = {
                name: ModelConfig(**model_data)
                for name, model_data in data["models"].items()
            }

        if "ei" in data:
            config.ei = EIConfig(**data["ei"])

        if "interrupt" in data:
            ic = data["interrupt"]
            # 展平嵌套结构
            config.interrupt = InterruptConfig(
                dominant_threshold=ic.get("confidence_anomaly", {}).get("dominant_threshold", 80),
                weak_threshold=ic.get("confidence_anomaly", {}).get("weak_threshold", 30),
                no_fact_rounds_threshold=ic.get("output_stagnation", {}).get("no_fact_rounds_threshold", 3),
                consecutive_same_output_threshold=ic.get("output_stagnation", {}).get("consecutive_same_output_threshold", 2),
            )

        if "valley" in data:
            vc = data["valley"]
            config.valley = ValleyConfig(
                window_size=vc.get("window_size", 3),
                ei_low_threshold=vc.get("ei_low_threshold", 10),
                no_fact_rounds_threshold=vc.get("no_fact_rounds_threshold", 3),
            )

        if "logging" in data:
            config.logging = LoggingConfig(**data["logging"])

        if "human_gate" in data:
            config.human_gate = HumanGateConfig(**data["human_gate"])

        return config

    def get_model_client(self, role: str) -> BaseLLMClient:
        """获取角色对应的 LLM 客户端"""
        model_config = self.models.get(role)
        if not model_config:
            # 默认返回 Custom 客户端
            return create_llm_client(provider="custom")

        # api_key 优先使用环境变量
        api_key = os.getenv("LLM_API_KEY", "")
        # 兼容配置文件中空的 api_key
        if not api_key and model_config.api_key:
            api_key = model_config.api_key

        return create_llm_client(
            provider=model_config.provider,
            api_key=api_key,
            base_url=model_config.api_url or os.getenv("LLM_API_URL", ""),
            model=model_config.model,
        )


# 全局配置实例
_config: Config | None = None


def get_config(path: str | Path = None) -> Config:
    """获取全局���置（单例）"""
    global _config
    if _config is None:
        _config = Config.from_yaml(path)
    return _config


def reload_config(path: str | Path = None) -> Config:
    """重新加载配置"""
    global _config
    _config = Config.from_yaml(path)
    return _config
