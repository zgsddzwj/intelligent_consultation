"""BaseAgent 工具执行与重试机制测试"""

import pytest

import app.agents.base as base_module
from app.agents.base import BaseAgent


class _DummyAgent(BaseAgent):
    """最小可实例化的 Agent 桩"""

    def get_system_prompt(self) -> str:
        return "test"

    def process(self, input_data):
        return {"ok": True}


class _FlakyTool:
    """前 fail_times 次抛错、之后成功的工具"""

    def __init__(self, fail_times: int, error: Exception):
        self.name = "flaky_tool"
        self.description = "test tool"
        self.fail_times = fail_times
        self.error = error
        self.calls = 0

    def execute(self, **kwargs):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.error
        return {"done": True}


@pytest.fixture(autouse=True)
def _fast_retry(monkeypatch):
    # 重试延迟 0.5*(attempt+1)，测试中跳过等待。
    # 仅替换 base 模块可见的 time 引用，不影响工具内部使用的真实 time 模块
    import time as real_time
    import types

    fake_time = types.SimpleNamespace(sleep=lambda *_: None, time=real_time.time)
    monkeypatch.setattr(base_module, "time", fake_time)


def test_execute_tool_retries_on_exception():
    """工具抛普通异常时应触发重试并最终成功（而非 NameError 中断）"""
    agent = _DummyAgent(name="test_agent", description="test")
    tool = _FlakyTool(fail_times=2, error=ValueError("boom"))
    agent.add_tool(tool)

    result = agent.execute_tool("flaky_tool", max_retries=2, timeout=5)

    assert result == {"done": True}
    assert tool.calls == 3
    assert agent.stats["tools_usage"]["test_agent.flaky_tool"] == 1


def test_execute_tool_raises_original_error_after_retries():
    """重试耗尽后应抛出原始异常并记录失败统计"""
    agent = _DummyAgent(name="test_agent_fail", description="test")
    tool = _FlakyTool(fail_times=99, error=ValueError("always fails"))
    agent.add_tool(tool)

    with pytest.raises(ValueError, match="always fails"):
        agent.execute_tool("flaky_tool", max_retries=1, timeout=5)

    assert tool.calls == 2
    assert agent.stats["tool_failures"]["flaky_tool:ValueError"] == 2


def test_execute_tool_retries_on_timeout():
    """工具执行超时应走超时分支并触发重试"""
    import time as real_time_module

    agent = _DummyAgent(name="test_agent_timeout", description="test")
    tool = _FlakyTool(fail_times=0, error=None)

    def _slow_first_call(**kwargs):
        # 首次执行超过 1s 超时窗口，重试时立即返回
        tool.calls += 1
        if tool.calls > 1:
            return {"done": True}
        real_time_module.sleep(2)
        return {"done": True}

    tool.execute = _slow_first_call
    agent.add_tool(tool)

    result = agent.execute_tool("flaky_tool", max_retries=1, timeout=1)
    assert result == {"done": True}
    assert tool.calls == 2
