"""Higress 网关健康检查模块

定时检查 Higress AI 网关的健康状态，
更新 HigressClient 的健康标记，
并在网关异常时记录告警日志。

可通过后台任务或定时触发器调用。
"""
import time
import threading
import httpx
from typing import Optional
from app.config import get_settings
from app.services.higress_client import higress_client
from app.utils.logger import app_logger

settings = get_settings()


class HigressHealthChecker:
    """Higress 网关健康检查器（线程安全单例）

    使用方法：
    1. 启动后台线程定时检查：
       checker = HigressHealthChecker()
       checker.start_background_check()

    2. 手动触发一次检查：
       checker.check_once()

    3. 停止后台检查：
       checker.stop_background_check()
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
        self._bg_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._consecutive_failures = 0
        self._max_failures = 3  # 连续失败 N 次标记为不健康

    @property
    def check_url(self) -> Optional[str]:
        """健康检查 URL"""
        if not higress_client.enabled:
            return None
        # Higress 网关管理端口暴露 /ready
        base = settings.HIGRESS_GATEWAY_URL.rstrip("/")
        return f"{base}/ai/health"

    def check_once(self) -> bool:
        """执行一次健康检查

        Returns:
            True 如果网关健康，False 如果不健康或不可达
        """
        if not higress_client.enabled:
            return True  # 未启用时视为健康

        url = self.check_url
        if not url:
            return True

        try:
            headers = higress_client.get_auth_headers()
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url, headers=headers)

            if response.status_code == 200:
                self._consecutive_failures = 0
                higress_client.update_health_status(True)
                app_logger.debug("Higress 网关健康检查通过")
                return True
            else:
                self._consecutive_failures += 1
                app_logger.warning(
                    f"Higress 网关健康检查异常: HTTP {response.status_code}, "
                    f"连续失败 {self._consecutive_failures}/{self._max_failures}"
                )

                if self._consecutive_failures >= self._max_failures:
                    higress_client.update_health_status(False)

                return False

        except Exception as e:
            self._consecutive_failures += 1
            app_logger.warning(
                f"Higress 网关健康检查失败: {e}, "
                f"连续失败 {self._consecutive_failures}/{self._max_failures}"
            )

            if self._consecutive_failures >= self._max_failures:
                higress_client.update_health_status(False)

            return False

    def start_background_check(self):
        """启动后台健康检查线程"""
        if not higress_client.enabled:
            app_logger.info("Higress 网关未启用，跳过健康检查")
            return

        if self._bg_thread and self._bg_thread.is_alive():
            app_logger.warning("Higress 健康检查线程已在运行")
            return

        self._stop_event.clear()
        self._bg_thread = threading.Thread(
            target=self._bg_check_loop,
            daemon=True,
            name="higress-health-checker"
        )
        self._bg_thread.start()
        app_logger.info(
            f"Higress 健康检查线程已启动，检查间隔: {settings.HIGRESS_HEALTH_CHECK_INTERVAL}s"
        )

    def stop_background_check(self):
        """停止后台健康检查线程"""
        if self._bg_thread and self._bg_thread.is_alive():
            self._stop_event.set()
            self._bg_thread.join(timeout=10)
            app_logger.info("Higress 健康检查线程已停止")

    def _bg_check_loop(self):
        """后台健康检查循环"""
        interval = settings.HIGRESS_HEALTH_CHECK_INTERVAL
        while not self._stop_event.is_set():
            try:
                self.check_once()
            except Exception as e:
                app_logger.error(f"Higress 健康检查循环异常: {e}")

            # 使用 Event.wait 代替 time.sleep，支持快速停止
            self._stop_event.wait(timeout=interval)

    def get_status(self) -> dict:
        """获取健康检查状态摘要"""
        return {
            "enabled": higress_client.enabled,
            "is_healthy": higress_client.is_healthy,
            "consecutive_failures": self._consecutive_failures,
            "max_failures": self._max_failures,
            "check_interval": settings.HIGRESS_HEALTH_CHECK_INTERVAL,
            "check_url": self.check_url,
            "bg_thread_alive": self._bg_thread is not None and self._bg_thread.is_alive(),
        }


# 全局单例
higress_health_checker = HigressHealthChecker()
