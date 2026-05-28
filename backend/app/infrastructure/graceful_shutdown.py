"""优雅关闭管理器 - 确保应用关闭时资源正确释放"""
import asyncio
import signal
import time
from typing import List, Callable, Optional
from app.utils.logger import app_logger


class GracefulShutdownManager:
    """
    优雅关闭管理器

    功能：
    - 注册关闭钩子
    - 处理SIGTERM/SIGINT信号
    - 设置关闭超时
    - 记录关闭过程
    """

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._handlers: List[Callable] = []
        self._is_shutting_down = False
        self._shutdown_start_time: Optional[float] = None

    def register(self, handler: Callable, name: str = None):
        """注册关闭钩子"""
        handler_name = name or getattr(handler, '__name__', 'unknown')
        self._handlers.append((handler_name, handler))
        app_logger.debug(f"注册关闭钩子: {handler_name}")

    def setup_signal_handlers(self):
        """设置信号处理器"""
        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_event_loop().add_signal_handler(
                sig, lambda s=sig: asyncio.create_task(self._handle_signal(s))
            )
        app_logger.info("优雅关闭信号处理器已设置")

    async def _handle_signal(self, sig: signal.Signals):
        """处理关闭信号"""
        app_logger.info(f"收到信号 {sig.name}，开始优雅关闭...")
        await self.shutdown()

    async def shutdown(self):
        """执行优雅关闭"""
        if self._is_shutting_down:
            app_logger.warning("关闭已在进行中，忽略重复请求")
            return

        self._is_shutting_down = True
        self._shutdown_start_time = time.time()

        app_logger.info(f"开始优雅关闭，超时: {self.timeout}秒，共 {len(self._handlers)} 个钩子")

        # 并行执行所有关闭钩子（带超时）
        tasks = []
        for name, handler in self._handlers:
            if asyncio.iscoroutinefunction(handler):
                task = asyncio.create_task(self._run_handler(name, handler))
            else:
                task = asyncio.create_task(asyncio.to_thread(handler))
            tasks.append(task)

        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self._get_remaining_time()
                )
            except asyncio.TimeoutError:
                app_logger.error("优雅关闭超时，强制退出")

        elapsed = time.time() - self._shutdown_start_time
        app_logger.info(f"优雅关闭完成，耗时 {elapsed:.2f}秒")

    async def _run_handler(self, name: str, handler: Callable):
        """运行单个关闭钩子"""
        start = time.time()
        try:
            await handler()
            elapsed = time.time() - start
            app_logger.info(f"✓ 关闭钩子完成: {name} ({elapsed:.2f}s)")
        except Exception as e:
            elapsed = time.time() - start
            app_logger.error(f"✗ 关闭钩子失败: {name} ({elapsed:.2f}s) - {e}")

    def _get_remaining_time(self) -> float:
        """获取剩余关闭时间"""
        if self._shutdown_start_time is None:
            return self.timeout
        elapsed = time.time() - self._shutdown_start_time
        return max(0.1, self.timeout - elapsed)

    @property
    def is_shutting_down(self) -> bool:
        """是否正在关闭"""
        return self._is_shutting_down


# 全局关闭管理器实例
shutdown_manager = GracefulShutdownManager()
