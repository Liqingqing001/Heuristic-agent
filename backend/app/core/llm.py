"""大模型客户端封装（OpenAI 兼容接口，支持 BYOK 透传）。

BYOK：前端把使用者自己的 key 放在请求头里传上来，后端只用于本次调用，
不落库、不写日志；没有传 key 时回退到服务端 ``.env`` 里的公共 key。
"""
from __future__ import annotations

from openai import OpenAI

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

_default_client: OpenAI | None = None


def _client(api_key: str | None = None) -> OpenAI:
    key = (api_key or "").strip() or DEEPSEEK_API_KEY
    if not key:
        raise RuntimeError("未配置模型密钥：请在页面右上角「模型设置」里填写你自己的 API Key")
    if key == DEEPSEEK_API_KEY:
        global _default_client
        if _default_client is None:
            _default_client = OpenAI(
                api_key=key, base_url=DEEPSEEK_BASE_URL, timeout=120, max_retries=1
            )
        return _default_client
    # 使用者自带的 key：每次请求单独建客户端，避免缓存别人的密钥
    return OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL, timeout=120, max_retries=0)


def chat_stream(messages: list[dict], temperature: float = 0.7, api_key: str | None = None):
    """流式对话，逐个产出文本增量。"""
    client = _client(api_key)
    stream = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def chat(messages: list[dict], temperature: float = 0.7, api_key: str | None = None) -> str:
    """非流式对话，返回完整回复。"""
    client = _client(api_key)
    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=temperature,
        stream=False,
    )
    return resp.choices[0].message.content or ""


def status() -> dict:
    """给前端状态横幅用：只暴露"有没有服务端 key"，绝不返回 key 本身。"""
    return {
        "provider": "deepseek",
        "model": DEEPSEEK_MODEL,
        "server_key": bool(DEEPSEEK_API_KEY),
        "byok_supported": True,
    }
