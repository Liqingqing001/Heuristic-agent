"""C/C++ 代码静态线索粗提取。

只做启发式、非精确的粗解析，产出"可能相关"的行号与语句，作为额外上下文
喂给 LLM，让诊断聚焦在断链/内存/旋转等痛点上，而非泛泛而谈。
"""
import re

# 控制流关键字，避免被误识别为函数定义
_KEYWORDS = {"if", "while", "for", "switch", "else", "return", "sizeof", "case", "catch"}


def _extract_func_names(code: str) -> set[str]:
    """提取"名字(...) {"形式的函数定义名，排除控制流关键字。"""
    names = set()
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{", code):
        name = m.group(1)
        if name not in _KEYWORDS:
            names.add(name)
    return names


def analyze(code: str) -> dict:
    """返回结构化线索：内存操作 / 指针链操作 / 可能的树旋转 / 可能的递归。"""
    clues: dict[str, list[str]] = {
        "内存操作": [],
        "指针链操作": [],
        "可能的树旋转": [],
        "可能的递归": [],
    }

    lines = code.splitlines()
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s:
            continue
        if re.search(r"\b(malloc|calloc|realloc|new|free|delete)\b", s):
            clues["内存操作"].append(f"L{i}: {s}")
        if "->next" in s or "->prev" in s or "->left" in s or "->right" in s:
            clues["指针链操作"].append(f"L{i}: {s}")
        if re.search(r"\b(leftRotate|rightRotate|rotate|rotation)\b", s, re.IGNORECASE):
            clues["可能的树旋转"].append(f"L{i}: {s}")

    # 递归：函数名在代码中出现超过 1 次（定义 1 次 + 疑似自调用）
    for fn in _extract_func_names(code):
        if len(re.findall(rf"\b{re.escape(fn)}\b", code)) > 1:
            clues["可能的递归"].append(f"函数 {fn} 疑似存在自调用")

    return {k: v for k, v in clues.items() if v}
