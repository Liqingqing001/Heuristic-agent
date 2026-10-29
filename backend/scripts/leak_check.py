"""检查 AI 回复里有没有泄露"完整可编译代码"（课题的硬约束）。

扫描库里所有 AI 输出（作业诊断 + 代码剖析记录），按启发式规则判定：

- 出现 `#include` 或 `int main(`：几乎可以确定是完整程序；
- 代码块超过 15 行：疑似完整实现；
- 出现"完整代码如下 / 标准答案如下"：疑似直接给答案。

用法（在 backend 目录下）：

    py scripts\\leak_check.py

输出总回复数、命中数、通过率，以及命中的样例 id。适合放进答辩 PPT。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import get_conn, init_db  # noqa: E402

CODE_BLOCK_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
ANSWER_WORDS_RE = re.compile(r"完整代码如下|标准答案如下|完整实现如下")

RULES = [
    (re.compile(r"#include"), "包含 #include（完整程序）"),
    (re.compile(r"\bint\s+main\s*\("), "包含 int main(（完整程序）"),
]


def scan(text: str) -> list[str]:
    hits: list[str] = []
    for pattern, label in RULES:
        if pattern.search(text):
            hits.append(label)
    for block in CODE_BLOCK_RE.findall(text):
        lines = [line for line in block.splitlines() if line.strip()]
        if len(lines) > 15:
            hits.append(f"代码块 {len(lines)} 行（>15）")
    if ANSWER_WORDS_RE.search(text):
        hits.append("出现「完整代码如下」类表述")
    return hits


def main() -> int:
    init_db()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT 'submission' AS kind, id, ai_result AS text FROM submissions WHERE ai_result != ''"
        ).fetchall()
        rows += conn.execute(
            "SELECT 'analysis' AS kind, id, result AS text FROM code_analyses WHERE result != ''"
        ).fetchall()
    finally:
        conn.close()

    total = len(rows)
    bad = []
    for row in rows:
        hits = scan(row["text"] or "")
        if hits:
            bad.append((row["kind"], row["id"], hits))

    rate = (1 - len(bad) / total) * 100 if total else 100.0
    print(f"扫描 AI 回复：{total} 条")
    print(f"疑似泄露完整代码：{len(bad)} 条")
    print(f"通过率：{rate:.1f}%")
    for kind, row_id, hits in bad[:10]:
        print(f"  - {kind}#{row_id}: {'；'.join(hits)}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
