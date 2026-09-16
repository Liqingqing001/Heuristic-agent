"""DeepSeek 大模型客户端封装（OpenAI 兼容接口）。"""
from openai import OpenAI

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

_client: OpenAI | None = None


def get_client() -> OpenAI:
    """懒加载单例，避免导入时立即校验 API key。"""
    global _client
    if _client is None:
        if not DEEPSEEK_API_KEY:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY，请复制 backend/.env.example 为 .env 并填写密钥")
        _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _client


def chat_stream(messages: list[dict], temperature: float = 0.7):
    """流式对话，逐个产出文本增量。"""
    client = get_client()
    stream = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def chat(messages: list[dict], temperature: float = 0.7) -> str:
    """非流式对话，返回完整回复。"""
    client = get_client()
    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=temperature,
        stream=False,
    )
    return resp.choices[0].message.content or ""
