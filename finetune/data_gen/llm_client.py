"""硅基流动 LLM 客户端 —— 数据生成的教师模型。

教师模型端点解析优先级：
1. 脚本 CLI 参数（--model / --base-url / --api-key）
2. finetune/.env 的 TEACHER_MODEL / TEACHER_BASE_URL / TEACHER_API_KEY
   （用于火山引擎 CodingPlan 等订阅制端点，见 README）
3. backend/.env 的 SILICONFLOW_*（项目现用配置，按量付费）
"""
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

from common import BACKEND_DIR, FINETUNE_DIR

_TEACHER_MODEL = "deepseek-ai/DeepSeek-V3"
FINETUNE_ENV = FINETUNE_DIR / ".env"


def _load_backend_env() -> None:
    """加载 backend/.env（兜底），再加载 finetune/.env（优先覆盖）。"""
    backend_env = BACKEND_DIR / ".env"
    if backend_env.exists():
        load_dotenv(backend_env, override=False)
    if FINETUNE_ENV.exists():
        load_dotenv(FINETUNE_ENV, override=True)


class LLMClient:
    """OpenAI 兼容接口客户端，带并发批处理与重试。"""

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        max_workers: int = 5,
        request_timeout: int = 120,
    ):
        _load_backend_env()
        from openai import OpenAI  # 延迟导入，便于 --help 快速查看参数

        self.model = model or os.getenv("TEACHER_MODEL") or os.getenv("SILICONFLOW_MODEL", _TEACHER_MODEL)
        self.base_url = base_url or os.getenv("TEACHER_BASE_URL") or os.getenv(
            "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"
        )
        self.api_key = api_key or os.getenv("TEACHER_API_KEY") or os.getenv("SILICONFLOW_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                f"未找到 API Key：请在 {BACKEND_DIR / '.env'} 配置 SILICONFLOW_API_KEY，"
                f"或在 {FINETUNE_ENV} 配置 TEACHER_API_KEY（火山引擎 CodingPlan），"
                "或用 --api-key 传入"
            )
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=request_timeout)
        self.max_workers = max_workers
        # 客户端级附加参数（JSON），如豆包模型关闭思考：{"thinking": {"type": "disabled"}}
        extra = os.getenv("TEACHER_EXTRA_BODY", "").strip()
        self.extra_body: Optional[dict] = json.loads(extra) if extra else None

    def chat(
        self,
        user: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
        retries: int = 3,
    ) -> Optional[str]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        for attempt in range(retries):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    extra_body=self.extra_body,
                )
                content = resp.choices[0].message.content
                if content and content.strip():
                    return content.strip()
            except Exception as e:  # noqa: BLE001 - 网络/限流等均重试
                if attempt == retries - 1:
                    print(f"  [重试耗尽] {type(e).__name__}: {str(e)[:200]}")
                    return None
                time.sleep(2 ** attempt * 2)
        return None

    def chat_many(
        self, requests: List[Dict], desc: str = "", max_workers: Optional[int] = None
    ) -> List[Optional[str]]:
        """并发批量调用。requests 元素为 chat() 的关键字参数字典，结果按输入顺序返回。

        字典中下划线开头的键（如 _meta）视为元数据，不传给模型。
        """
        results: List[Optional[str]] = [None] * len(requests)
        workers = max_workers or self.max_workers
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self.chat, **{k: v for k, v in req.items() if not k.startswith("_")}): i
                for i, req in enumerate(requests)
            }
            done = 0
            for future in as_completed(futures):
                i = futures[future]
                results[i] = future.result()
                done += 1
                if desc and done % 10 == 0:
                    print(f"  {desc}: {done}/{len(requests)}")
        return results


def extract_json(text: str) -> Optional[dict]:
    """从模型输出中提取第一个平衡的 JSON 对象（对齐 entity_recognizer 的宽松解析思路）。"""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def normalize_output(text: str) -> str:
    """清理教师输出：去掉思考前缀、多余引号包裹等。"""
    text = text.strip()
    text = re.sub(r"^(好的|以下是|回答如下)[，,：:、\s]*", "", text)
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()
