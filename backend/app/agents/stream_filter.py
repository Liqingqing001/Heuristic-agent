"""把模型输出末尾的结构化诊断块从流式文本里剥离出来。

模型按提示在回复最后追加：

    <<<DIAG
    {"error_types": [...], ...}
    DIAG>>>

前端不应该看到这个块，所以边接收边过滤：哨兵之前的内容照常流式转发，
哨兵之后的内容先攒着，等流结束后解析成 JSON。
"""
from __future__ import annotations

START = "<<<DIAG"
END = "DIAG>>>"


class DiagnosisStreamFilter:
    def __init__(self) -> None:
        self._buffer = ""
        self._payload = ""
        self._seen_start = False

    def feed(self, chunk: str) -> str:
        """喂入一个增量，返回可以展示给用户的文本（可能为空）。"""
        if not chunk:
            return ""
        if self._seen_start:
            self._payload += chunk
            return ""

        self._buffer += chunk
        index = self._buffer.find(START)
        if index != -1:
            visible = self._buffer[:index]
            self._payload = self._buffer[index + len(START):]
            self._buffer = ""
            self._seen_start = True
            return visible

        # 末尾可能是半个哨兵，先扣住不输出，避免把 "<<<DI" 漏给学生
        keep = len(START) - 1
        if len(self._buffer) > keep:
            visible = self._buffer[:-keep]
            self._buffer = self._buffer[-keep:]
            return visible
        return ""

    def finish(self) -> tuple[str, str]:
        """返回 (剩余可见文本, 诊断块原文)。"""
        if self._seen_start:
            payload = self._payload
            end = payload.find(END)
            if end != -1:
                payload = payload[:end]
            self._payload = ""
            return "", payload.strip()
        tail, self._buffer = self._buffer, ""
        return tail, ""
