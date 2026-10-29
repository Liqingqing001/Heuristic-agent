"""结构化诊断：解析模型输出的 JSON，并做字段校验与兜底。

落库格式（submissions.diagnosis / code_analyses.diagnosis）::

    {
      "error_types": ["断链"],
      "kp_ids": ["ds-01-02"],
      "severity": "medium",
      "hint_level_reached": 2,
      "next_question": "……",
      "source": "model"        # model | heuristic
    }
"""
from __future__ import annotations

import json
import re

from app.agents.prompts import ERROR_TYPES

_KP_ID_RE = re.compile(r"^ds-\d{2}-\d{2}$")
_SEVERITIES = {"low", "medium", "high"}


def parse(payload: str) -> dict | None:
    """从诊断块原文里解析 JSON；解析不出来返回 None。"""
    if not payload:
        return None
    text = payload.strip()
    # 容忍模型加了 ```json 围栏
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    return normalize(data)


def normalize(data: dict) -> dict:
    """把模型给的字段裁到合法范围。"""
    error_types = [
        str(item).strip()
        for item in (data.get("error_types") or [])
        if str(item).strip()
    ]
    error_types = [item for item in error_types if item in ERROR_TYPES][:6]

    kp_ids = [
        str(item).strip()
        for item in (data.get("kp_ids") or [])
        if _KP_ID_RE.match(str(item).strip())
    ][:6]

    severity = str(data.get("severity") or "").strip().lower()
    if severity not in _SEVERITIES:
        severity = "medium"

    hint = data.get("hint_level_reached")
    if isinstance(hint, str) and hint.isdigit():
        hint = int(hint)
    if not isinstance(hint, int) or not 1 <= hint <= 3:
        hint = None

    next_question = str(data.get("next_question") or "").strip()[:200]

    return {
        "error_types": error_types,
        "kp_ids": kp_ids,
        "severity": severity,
        "hint_level_reached": hint,
        "next_question": next_question,
        "source": "model",
    }


def heuristic(code: str, clues: dict | None = None) -> dict:
    """模型没按格式输出时的兜底：用静态线索粗分类，保证看板有数据可用。"""
    clues = clues or {}
    error_types: list[str] = []
    if clues.get("可能的树旋转"):
        error_types.append("树旋转失衡")
    if clues.get("可能的递归"):
        error_types.append("递归基线缺失")
    if clues.get("内存操作"):
        if re.search(r"\b(free|delete)\b", code):
            error_types.append("内存泄漏")
    if not error_types:
        error_types.append("其他")
    return {
        "error_types": error_types[:3],
        "kp_ids": [],
        "severity": "medium",
        "hint_level_reached": None,
        "next_question": "",
        "source": "heuristic",
    }
