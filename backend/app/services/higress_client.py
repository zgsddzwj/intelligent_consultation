"""Higress AI 网关客户端

通过 Higress AI 网关统一转发 LLM 请求，实现：
- 统一认证（API Key）
- 请求限流
- 多模型路由
- 可观测性（日志、监控、链路追踪）
- 负载均衡与故障转移

当 HIGRESS_ENABLED=True 时，LLMService 和视觉模型客户端
会将请求发往 Higress 网关而非直连 SiliconFlow API。
"""
from typing import Optional, Dict, Any
import threading
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class HigressClient:
    """Higress AI 网关客户端（线程安全单例）

    根据 HIGRESS_ENABLED 开关决定是否启用网关模式：
    - 启用：返回 Higress 网关地址和认证信息，OpenAI SDK 走网关
    - 未启用：返回 None，调用方直连原始 Provider
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._gateway_url: Optional[str] = None
        self._api_key: Optional[str] = None
        self._health_status: bool = True  # 网关健康状态
        self._health_check_time: float = 0.0
        self._refresh_config()

    def _refresh_config(self):
        """从配置刷新网关参数"""
        if settings.HIGRESS_ENABLED:
            base = settings.HIGRESS_GATEWAY_URL.rstrip("/")
            self._gateway_url = base
            self._api_key = settings.HIGRESS_API_KEY
            app_logger.info(
                f"Higress AI 网关已启用: gateway_url={self._gateway_url}"
            )
        else:
            self._gateway_url = None
            self._api_key = None
            app_logger.info("Higress AI 网关未启用，LLM 请求直连 Provider")

    @property
    def enabled(self) -> bool:
        """是否启用了 Higress 网关"""
        return settings.HIGRESS_ENABLED

    @property
    def gateway_url(self) -> Optional[str]:
        """Higress 网关基础 URL"""
        return self._gateway_url

    @property
    def chat_url(self) -> Optional[str]:
        """对话接口完整 URL"""
        if not self._gateway_url:
            return None
        return f"{self._gateway_url}{settings.HIGRESS_CHAT_PATH}"

    @property
    def embedding_url(self) -> Optional[str]:
        """嵌入接口完整 URL"""
        if not self._gateway_url:
            return None
        return f"{self._gateway_url}{settings.HIGRESS_EMBEDDING_PATH}"

    @property
    def vision_url(self) -> Optional[str]:
        """视觉模型接口完整 URL"""
        if not self._gateway_url:
            return None
        return f"{self._gateway_url}{settings.HIGRESS_VISION_PATH}"

    @property
    def api_key(self) -> Optional[str]:
        """Higress 网关认证 API Key"""
        return self._api_key

    @property
    def timeout(self) -> int:
        """网关请求超时时间"""
        return settings.HIGRESS_TIMEOUT

    @property
    def max_retries(self) -> int:
        """网关请求最大重试次数"""
        return settings.HIGRESS_MAX_RETRIES

    def get_openai_base_url(self, endpoint_type: str = "chat") -> Optional[str]:
        """获取 OpenAI SDK 兼容的 base_url

        Higress AI 网关兼容 OpenAI API 格式，
        因此只需将 OpenAI SDK 的 base_url 指向网关地址即可。

        Args:
            endpoint_type: "chat" | "embedding" | "vision"

        Returns:
            启用网关时返回网关 URL（去掉路径后缀），未启用时返回 None
        """
        if not self.enabled or not self._gateway_url:
            return None

        # OpenAI SDK 会在 base_url 后自动拼接 /chat/completions
        # 因此我们返回去掉路径后缀的基础 URL
        if endpoint_type == "chat":
            # /ai/chat/completions -> base_url + /ai
            return f"{self._gateway_url}/ai"
        elif endpoint_type == "embedding":
            return f"{self._gateway_url}/ai"
        elif endpoint_type == "vision":
            return f"{self._gateway_url}/ai/vision"
        return self._gateway_url

    def get_auth_headers(self) -> Dict[str, str]:
        """获取 Higress 网关认证请求头"""
        headers = {}
        if self._api_key:
            headers["x-higress-api-key"] = self._api_key
        return headers

    def get_openai_client_config(self, endpoint_type: str = "chat") -> Dict[str, Any]:
        """获取 OpenAI SDK 客户端配置

        用于在 LLMService 和视觉模型客户端中构建 OpenAI 客户端时，
        根据 Higress 是否启用来决定 base_url 和 default_headers。

        Args:
            endpoint_type: "chat" | "embedding" | "vision"

        Returns:
            包含 base_url 和 default_headers 的配置字典。
            如果 Higress 未启用，返回空字典（调用方使用原始配置）。
        """
        if not self.enabled:
            return {}

        base_url = self.get_openai_base_url(endpoint_type)
        if not base_url:
            return {}

        config: Dict[str, Any] = {
            "base_url": base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }

        auth_headers = self.get_auth_headers()
        if auth_headers:
            config["default_headers"] = auth_headers

        app_logger.debug(
            f"Higress OpenAI 客户端配置: endpoint={endpoint_type}, base_url={base_url}"
        )
        return config

    def update_health_status(self, healthy: bool):
        """更新网关健康状态"""
        import time
        old_status = self._health_status
        self._health_status = healthy
        self._health_check_time = time.time()
        if old_status != healthy:
            level = app_logger.info if healthy else app_logger.warning
            level(f"Higress 网关健康状态变更: {'健康' if healthy else '异常'}")

    @property
    def is_healthy(self) -> bool:
        """网关是否健康"""
        return self._health_status

    def reset(self):
        """重置配置（用于测试或配置热更新）"""
        self._refresh_config()


# 全局单例
higress_client = HigressClient()
