"""校验知识点 Markdown（front matter + 固定小节 + 不泄题红线）。

用法（在 backend/ 目录下）：

    py scripts\\check_kp.py             # 校验并打印覆盖矩阵
    py scripts\\check_kp.py --strict    # 警告也算失败，提交前跑
    py scripts\\check_kp.py --json      # 机器可读（给 CI / 前端用）

退出码：0 通过；1 有错误（或 --strict 下有警告）；2 脚本自身异常。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.utils import kp_meta  # noqa: E402

DEFAULT_KP_DIR = BACKEND_DIR / "data" / "knowledge" / "kp"

# ---------------------------------------------------------------- 检查规则

CODE_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
LEAK_PATTERNS = (
    ("int main(", "疑似完整程序入口 int main("),
    ("#include", "疑似完整可编译程序 #include"),
)
LEAK_WORDS_RE = re.compile(r"完整代码如下|标准答案如下|完整实现如下")

ERROR_FIELDS = {
    "现象": re.compile(r"^\s*[-*]\s*\**现象\**\s*[:：]", re.M),
    "原因": re.compile(r"^\s*[-*]\s*\**原因\**\s*[:：]", re.M),
    "引导问题": re.compile(r"^\s*[-*]\s*\**引导问题\**\s*[:：]", re.M),
}
EXERCISE_FIELDS = {
    "题面": re.compile(r"^\s*[-*]\s*\**题面\**\s*[:：]", re.M),
    "一阶提示": re.compile(r"^\s*[-*]\s*.*一阶提示", re.M),
    "二阶提示": re.compile(r"^\s*[-*]\s*.*二阶提示", re.M),
    "三阶提示": re.compile(r"^\s*[-*]\s*.*三阶提示", re.M),
    "验收点": re.compile(r"^\s*[-*]\s*\**验收点\**\s*[:：]", re.M),
}
EXERCISE_DIFFICULTY_RE = re.compile(r"难度\s*[:：]\s*(\d)")


def _width(text: str) -> int:
    """中文字符占两列的显示宽度。"""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _width(text))


def _issue(level: str, code: str, message: str) -> dict:
    return {"level": level, "code": code, "message": message}


# ---------------------------------------------------------------- 单文件检查

def check_meta(kp: dict, issues: list[dict]) -> dict | None:
    """检查 front matter，返回解析出的 (kp_id, chapter) 供全局使用。"""
    meta = kp["meta"]
    present = set(meta)

    for key in kp_meta.REQUIRED_META:
        if key not in present or meta[key] is None or meta[key] == "":
            issues.append(_issue("ERR", "M01", f"缺少必填字段 {key}"))

    kp_id = str(meta.get("id", "")).strip()
    matched = kp_meta.KP_ID_RE.match(kp_id)
    if "id" in present and not matched:
        issues.append(_issue("ERR", "M02", f"id「{kp_id or '空'}」不是 ds-章-序 格式（如 ds-01-02）"))

    expected = kp_meta.id_from_filename(kp["path"])
    if expected is None:
        issues.append(_issue("ERR", "M03", "文件名不符合「ds-01-02-名称.md」命名"))
    elif matched and kp_id != expected:
        issues.append(_issue("ERR", "M04", f"文件名开头是 {expected}，但 id 写的是 {kp_id}"))

    chapter = meta.get("chapter")
    if "chapter" in present and not isinstance(chapter, int):
        issues.append(_issue("ERR", "M05", f"chapter 必须是整数，当前是 {chapter!r}"))
        chapter = None
    elif "chapter" in present and chapter not in kp_meta.CHAPTER_TITLES:
        issues.append(_issue("ERR", "M06", f"chapter={chapter} 超出 1-8"))
        chapter = None
    elif "chapter" in present and matched and int(matched.group(1)) != chapter:
        issues.append(_issue("ERR", "M07", f"chapter={chapter} 与 id 里的章号 {matched.group(1)} 不一致"))

    title = meta.get("title")
    if "title" in present:
        if not isinstance(title, str) or not title.strip():
            issues.append(_issue("ERR", "M09", "title 不能为空"))
        elif len(title) > 60:
            issues.append(_issue("WARN", "M08", f"title 有 {len(title)} 字，建议 ≤60"))

    difficulty = meta.get("difficulty")
    if "difficulty" in present and (not isinstance(difficulty, int) or not 1 <= difficulty <= 5):
        issues.append(_issue("ERR", "M10", f"difficulty 必须是 1-5 的整数，当前是 {difficulty!r}"))

    kp_type = meta.get("type")
    if "type" in present and kp_type not in kp_meta.KP_TYPE_TITLES:
        issues.append(_issue("ERR", "M11", f"type 必须是 {sorted(kp_meta.KP_TYPE_TITLES)} 之一，当前是 {kp_type!r}"))

    tags = meta.get("tags")
    if "tags" in present:
        if not isinstance(tags, list):
            issues.append(_issue("ERR", "M14", "tags 必须是列表，如 [链表, 指针]"))
        else:
            if not 2 <= len(tags) <= 5:
                issues.append(_issue("WARN", "M12", f"tags 有 {len(tags)} 个，建议 2-5 个"))
            long_tags = [str(tag) for tag in tags if len(str(tag)) > 12]
            if long_tags:
                issues.append(_issue("WARN", "M13", f"tags 过长：{'、'.join(long_tags)}"))

    prereq = meta.get("prereq")
    if "prereq" in present:
        if not isinstance(prereq, list):
            issues.append(_issue("ERR", "M17", "prereq 必须是列表，没有前置就写 []"))
        else:
            if kp_id in prereq:
                issues.append(_issue("ERR", "M15", "prereq 不能包含自己"))
            for item in prereq:
                if not kp_meta.KP_ID_RE.match(str(item)):
                    issues.append(_issue("ERR", "M16", f"prereq 里的「{item}」不是合法 id"))

    objectives = meta.get("objectives")
    if "objectives" in present:
        if not isinstance(objectives, list):
            issues.append(_issue("ERR", "M20", "objectives 必须是列表"))
        else:
            if not objectives:
                issues.append(_issue("ERR", "M18", "objectives 至少写 1 条"))
            short = [str(item) for item in objectives if len(str(item).strip()) < 6]
            if short:
                issues.append(_issue("ERR", "M19", f"objectives 有条目过短（<6 字）：{short[0]}"))

    source = meta.get("source")
    if "source" in present and source != "" and not isinstance(source, str):
        issues.append(_issue("ERR", "M21", "source 必须是字符串（自编 / OI Wiki / 教材章节号）"))

    return {"id": kp_id if matched else None, "chapter": chapter}


def check_sections(kp: dict, issues: list[dict]) -> None:
    sections = kp["sections"]

    for name in kp_meta.REQUIRED_SECTIONS:
        if name not in sections:
            issues.append(_issue("ERR", "S01", f"缺少小节「## {name}」"))

    concept = sections.get("概念")
    if concept is not None:
        length = len(re.sub(r"\s", "", concept))
        if length < 120:
            issues.append(_issue("ERR", "S02", f"「概念」只有 {length} 字，至少要 120 字"))

    errors_text = sections.get("典型错误")
    if errors_text is not None:
        blocks = kp_meta.split_blocks(errors_text)
        error_blocks = [block for block in blocks if block[0].startswith("错误")]
        if not blocks:
            issues.append(_issue("ERR", "S03", "「典型错误」里没有用「### 错误 1：…」分条"))
        elif not error_blocks:
            issues.append(_issue("ERR", "S04", "「典型错误」的小标题要以「错误」开头，例如「### 错误 1：…」"))
        elif len(error_blocks) < 2:
            issues.append(_issue("ERR", "S05", f"「典型错误」只有 {len(error_blocks)} 条，至少 2 条"))
        for title, content in error_blocks:
            missing = [name for name, pattern in ERROR_FIELDS.items() if not pattern.search(content)]
            if missing:
                issues.append(_issue("ERR", "S06", f"「{title}」缺少：{'、'.join(missing)}"))

    exercises_text = sections.get("分级练习")
    if exercises_text is not None:
        blocks = kp_meta.split_blocks(exercises_text)
        exercises = [block for block in blocks if block[0].startswith("练习")]
        if not exercises:
            issues.append(_issue("ERR", "S07", "「分级练习」里没有用「### 练习 1：…」分题"))
        elif len(exercises) < 2:
            issues.append(_issue("ERR", "S08", f"「分级练习」只有 {len(exercises)} 道，至少 2 道"))

        difficulties: list[int] = []
        for title, content in exercises:
            missing = [name for name, pattern in EXERCISE_FIELDS.items() if not pattern.search(content)]
            if missing:
                issues.append(_issue("ERR", "S09", f"「{title}」缺少：{'、'.join(missing)}"))
            found = EXERCISE_DIFFICULTY_RE.search(title)
            if not found:
                issues.append(_issue("WARN", "S10", f"「{title}」没有标注难度（难度：N）"))
                continue
            level = int(found.group(1))
            if not 1 <= level <= 5:
                issues.append(_issue("ERR", "S11", f"「{title}」难度 {level} 超出 1-5"))
            else:
                difficulties.append(level)

        if difficulties and max(difficulties) <= 2:
            issues.append(_issue("WARN", "S12", "所有练习难度都 ≤2，建议至少有一道 3 分以上的拔高题"))


def check_no_leak(kp: dict, issues: list[dict]) -> None:
    body = kp["body"]
    for code in CODE_FENCE_RE.findall(body):
        for needle, label in LEAK_PATTERNS:
            if needle in code:
                issues.append(_issue("ERR", "L01", f"代码块里有 {label}，违反「不泄题」约束"))
        lines = [line for line in code.splitlines() if line.strip()]
        if len(lines) > 15:
            issues.append(_issue("WARN", "L02", f"代码块有 {len(lines)} 行，建议 ≤15 行"))
    if LEAK_WORDS_RE.search(body):
        issues.append(_issue("WARN", "L03", "出现「完整代码如下」这类表述，确认没有直接给答案"))


def check_file(kp: dict) -> tuple[list[dict], dict | None]:
    issues: list[dict] = []
    info = check_meta(kp, issues)
    check_sections(kp, issues)
    check_no_leak(kp, issues)
    return issues, info


# ---------------------------------------------------------------- 全局检查

def check_global(loaded: list[dict]) -> list[dict]:
    """重复 id、前置缺失、成环。"""
    issues: list[dict] = []

    seen: dict[str, int] = {}
    for kp in loaded:
        kp_id = kp["meta"].get("id")
        if not isinstance(kp_id, str):
            continue
        seen[kp_id] = seen.get(kp_id, 0) + 1
    for kp_id, count in sorted(seen.items()):
        if count > 1:
            issues.append(_issue("ERR", "G01", f"id {kp_id} 重复出现了 {count} 次"))

    known = set(seen)
    graph: dict[str, list[str]] = {}
    for kp in loaded:
        kp_id = kp["meta"].get("id")
        prereq = kp["meta"].get("prereq")
        if not isinstance(kp_id, str) or not isinstance(prereq, list):
            continue
        graph[kp_id] = [str(item) for item in prereq]
        for item in prereq:
            if str(item) not in known:
                issues.append(_issue("ERR", "G02", f"{kp_id} 的前置 {item} 不存在"))

    for cycle in _find_cycles(graph):
        issues.append(_issue("ERR", "G03", f"前置关系成环：{' → '.join(cycle)}"))
    return issues


def _find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """DFS 找环，返回若干条环路径（首尾相同）。"""
    white, gray, black = 0, 1, 2
    color: dict[str, int] = {}
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        color[node] = gray
        stack.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in graph:
                continue
            state = color.get(neighbor, white)
            if state == white:
                visit(neighbor)
            elif state == gray:
                start = stack.index(neighbor)
                cycle = stack[start:] + [neighbor]
                if cycle not in cycles:
                    cycles.append(cycle)
        stack.pop()
        color[node] = black

    for node in graph:
        if color.get(node, white) == white:
            visit(node)
    return cycles


def load_plan(kp_dir: Path) -> list[str]:
    """从 README.md 的表格里读出计划中的知识点编号。"""
    readme = kp_dir / "README.md"
    if not readme.exists():
        return []
    text = readme.read_text(encoding="utf-8")
    return re.findall(r"\|\s*(ds-\d{2}-\d{2})\s*\|", text)


# ---------------------------------------------------------------- 输出

def render(
    kp_dir: Path,
    results: list[dict],
    global_issues: list[dict],
    plan: list[str],
    written: set[str],
) -> str:
    lines: list[str] = []
    lines.append(f"知识点库校验 · {kp_dir}")
    lines.append("=" * 78)

    for item in results:
        name = item["path"].name
        issues = item["issues"]
        if not issues:
            lines.append(f"[OK]   {name}")
            continue
        has_error = any(issue["level"] == "ERR" for issue in issues)
        lines.append(f"[{'ERR' if has_error else 'WARN'}] {name}")
        for issue in issues:
            lines.append(f"       · {issue['code']} {issue['message']}")

    if global_issues:
        lines.append("")
        lines.append("全局问题")
        for issue in global_issues:
            lines.append(f"  [{issue['level']}] {issue['code']} {issue['message']}")

    err_count = sum(
        1 for item in results for issue in item["issues"] if issue["level"] == "ERR"
    ) + sum(1 for issue in global_issues if issue["level"] == "ERR")
    warn_count = sum(
        1 for item in results for issue in item["issues"] if issue["level"] == "WARN"
    ) + sum(1 for issue in global_issues if issue["level"] == "WARN")
    failed = sum(1 for item in results if any(issue["level"] == "ERR" for issue in item["issues"]))

    lines.append("")
    lines.append("-" * 78)
    lines.append(
        f"文件 {len(results)} · 通过 {len(results) - failed} · 错误 {err_count} · 警告 {warn_count}"
    )

    # 章节覆盖
    lines.append("")
    lines.append("章节覆盖")
    header = f"  {_pad('章节', 16)}{_pad('知识点', 8)}{_pad('概念', 6)}{_pad('操作', 6)}{_pad('算法', 6)}{_pad('应用', 6)}平均难度"
    lines.append(header)
    for chapter in sorted(kp_meta.CHAPTER_TITLES):
        items = [item for item in results if item["info"] and item["info"]["chapter"] == chapter]
        counts = {key: 0 for key in kp_meta.KP_TYPE_TITLES}
        difficulties: list[int] = []
        for item in items:
            kp_type = item["meta"].get("type")
            if kp_type in counts:
                counts[kp_type] += 1
            value = item["meta"].get("difficulty")
            if isinstance(value, int) and 1 <= value <= 5:
                difficulties.append(value)
        average = f"{sum(difficulties) / len(difficulties):.1f}" if difficulties else "-"
        label = f"{chapter} {kp_meta.CHAPTER_TITLES[chapter]}"
        lines.append(
            f"  {_pad(label, 16)}{_pad(str(len(items)), 8)}"
            f"{_pad(str(counts['concept']), 6)}{_pad(str(counts['operation']), 6)}"
            f"{_pad(str(counts['algorithm']), 6)}{_pad(str(counts['application']), 6)}{average}"
        )

    # 计划覆盖
    if plan:
        done = [kp_id for kp_id in plan if kp_id in written]
        missing = [kp_id for kp_id in plan if kp_id not in written]
        percent = len(done) * 100 // len(plan)
        lines.append("")
        lines.append(f"计划覆盖（README.md）：已写 {len(done)} / {len(plan)}（{percent}%）")
        if missing:
            lines.append("未写：" + "、".join(missing))

    extra = sorted(written - set(plan)) if plan else []
    if extra:
        lines.append("计划外新增：" + "、".join(extra))

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    # Windows 控制台默认 GBK，统一按 UTF-8 输出，避免中文乱码
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass

    parser = argparse.ArgumentParser(description="校验知识点 Markdown")
    parser.add_argument("--dir", default=str(DEFAULT_KP_DIR), help="知识点目录（默认 data/knowledge/kp）")
    parser.add_argument("--strict", action="store_true", help="警告也视为失败")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    kp_dir = Path(args.dir)
    if not kp_dir.is_dir():
        print(f"目录不存在：{kp_dir}", file=sys.stderr)
        return 2

    files = kp_meta.iter_kp_files(kp_dir)
    if not files:
        print(f"没有找到知识点文件：{kp_dir}", file=sys.stderr)
        return 2

    loaded: list[dict] = []
    results: list[dict] = []
    for path in files:
        try:
            kp = kp_meta.load_kp(path)
        except kp_meta.KpFormatError as exc:
            results.append({
                "path": path,
                "meta": {},
                "info": None,
                "issues": [_issue("ERR", "F01", f"front matter 解析失败：{exc}")],
            })
            continue
        except UnicodeDecodeError as exc:
            results.append({
                "path": path,
                "meta": {},
                "info": None,
                "issues": [_issue("ERR", "F02", f"文件不是 UTF-8 编码：{exc}")],
            })
            continue

        issues, info = check_file(kp)
        item = {
            "path": path,
            "meta": kp["meta"],
            "info": info,
            "issues": issues,
        }
        results.append(item)
        loaded.append(kp)

    written = {
        kp["meta"]["id"]
        for kp in loaded
        if isinstance(kp["meta"].get("id"), str)
    }
    global_issues: list[dict] = []
    if loaded:
        global_issues = check_global(loaded)

    plan = load_plan(kp_dir)

    if args.json:
        payload = {
            "directory": str(kp_dir),
            "files": [
                {
                    "file": item["path"].name,
                    "id": item["meta"].get("id"),
                    "issues": item["issues"],
                }
                for item in results
            ],
            "global": global_issues,
            "plan": {"total": len(plan), "written": sorted(set(plan) & written)},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render(kp_dir, results, global_issues, plan, written))

    has_error = any(issue["level"] == "ERR" for issue in global_issues) or any(
        issue["level"] == "ERR" for item in results for issue in item["issues"]
    )
    has_warn = any(issue["level"] == "WARN" for issue in global_issues) or any(
        issue["level"] == "WARN" for item in results for issue in item["issues"]
    )
    if has_error or (args.strict and has_warn):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
