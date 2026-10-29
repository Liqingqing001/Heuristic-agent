"""知识点 Markdown 的解析工具：front matter + 固定小节。

零第三方依赖（不装 PyYAML 也能跑），供两处使用：
- ``backend/scripts/check_kp.py`` 校验知识点文件；
- 后续 RAG 建库时读取 ``kp_id`` / 章节 / 难度 / 前置，写进向量库 metadata。

文件结构约定见 ``data/knowledge/kp/README.md``。
"""
from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------- 常量

#: 知识点编号：ds-<两位章节号>-<两位序号>
KP_ID_RE = re.compile(r"^ds-(\d{2})-(\d{2})$")

#: 章节号 -> 章节名（与 lecture/ 下的编号保持一致）
CHAPTER_TITLES: dict[int, str] = {
    1: "链表",
    2: "栈与队列",
    3: "二叉树与BST",
    4: "AVL树",
    5: "排序",
    6: "查找",
    7: "图",
    8: "线性表",
}

#: 知识点类型 -> 中文名
KP_TYPE_TITLES: dict[str, str] = {
    "concept": "概念",
    "operation": "操作",
    "algorithm": "算法",
    "application": "应用",
}

#: 必填的正文小节（H2）
REQUIRED_SECTIONS: tuple[str, ...] = ("概念", "典型错误", "分级练习")

#: 必填的 front matter 字段
REQUIRED_META: tuple[str, ...] = (
    "id",
    "chapter",
    "title",
    "difficulty",
    "type",
    "tags",
    "prereq",
    "objectives",
    "source",
)

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_BLOCK_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)


class KpFormatError(ValueError):
    """front matter 语法错误（不是内容错误）。"""


# ---------------------------------------------------------------- 解析

def _parse_scalar(raw: str):
    """把一个 YAML 标量转成 Python 值；只处理本项目用得到的子集。"""
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value in ("null", "~"):
        return None
    return value


def _parse_value(raw: str):
    """解析 ``key: value`` 右边，支持 ``[a, b]`` 行内列表。"""
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        # 中英文逗号都认，标签里不会出现逗号
        return [_parse_scalar(part) for part in re.split(r"[,，]", inner) if part.strip()]
    return _parse_scalar(value)


def parse_front_matter(text: str) -> tuple[dict, str]:
    """拆出 front matter 与正文。

    返回 ``(meta, body)``；文件不以 ``---`` 开头或没有结束分隔符时抛
    :class:`KpFormatError`。
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized.startswith("\ufeff"):
        normalized = normalized[1:]

    lines = normalized.split("\n")
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start >= len(lines) or lines[start].strip() != "---":
        raise KpFormatError("文件必须以 front matter（---）开头")

    end = None
    for idx in range(start + 1, len(lines)):
        if lines[idx].strip() == "---":
            end = idx
            break
    if end is None:
        raise KpFormatError("front matter 缺少结束分隔符 ---")

    meta: dict = {}
    current_key: str | None = None
    for raw in lines[start + 1 : end]:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if current_key is None:
                raise KpFormatError(f"列表项没有对应的字段：{stripped}")
            meta[current_key].append(_parse_scalar(stripped[2:]))
            continue
        matched = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", stripped)
        if not matched:
            raise KpFormatError(f"无法解析的元数据行：{raw!r}")
        key = matched.group(1)
        rest = matched.group(2).strip()
        if rest == "":
            meta[key] = []  # 后面可能跟 block 列表
            current_key = key
        else:
            meta[key] = _parse_value(rest)
            current_key = None

    body = "\n".join(lines[end + 1 :])
    return meta, body


def split_sections(body: str) -> dict[str, str]:
    """按 ``## 标题`` 切成有序字典（Python 3.7+ 保序）。"""
    sections: dict[str, str] = {}
    matches = list(_SECTION_RE.finditer(body))
    for i, matched in enumerate(matches):
        start = matched.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[matched.group(1).strip()] = body[start:end].strip()
    return sections


def split_blocks(section_text: str) -> list[tuple[str, str]]:
    """按 ``### 小标题`` 切块，返回 ``[(标题, 正文), ...]``。"""
    matches = list(_BLOCK_RE.finditer(section_text))
    blocks: list[tuple[str, str]] = []
    for i, matched in enumerate(matches):
        start = matched.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section_text)
        blocks.append((matched.group(1).strip(), section_text[start:end].strip()))
    return blocks


# ---------------------------------------------------------------- 读取

def load_kp(path: str | Path) -> dict:
    """读取一个知识点文件，返回 ``{path, meta, body, sections}``。"""
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)
    return {
        "path": file_path,
        "meta": meta,
        "body": body,
        "sections": split_sections(body),
    }


def iter_kp_files(kp_dir: str | Path) -> list[Path]:
    """列出目录下参与校验的文件：``*.md``，跳过 ``_`` 开头与 README。"""
    directory = Path(kp_dir)
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.glob("*.md")
        if not path.name.startswith("_") and path.name.lower() != "readme.md"
    )


def id_from_filename(path: str | Path) -> str | None:
    """从 ``ds-01-02-xxx.md`` 取出 ``ds-01-02``；不符合命名返回 None。"""
    matched = re.match(r"^(ds-\d{2}-\d{2})(?:-|$)", Path(path).stem)
    return matched.group(1) if matched else None


def to_vector_metadata(kp: dict) -> dict:
    """转成 ChromaDB 能存的扁平 metadata（只允许 str/int/float/bool）。"""
    meta = kp["meta"]
    prereq = meta.get("prereq") or []
    tags = meta.get("tags") or []
    return {
        "kp_id": str(meta.get("id", "")),
        "chapter": int(meta.get("chapter") or 0),
        "title": str(meta.get("title", "")),
        "difficulty": int(meta.get("difficulty") or 0),
        "type": str(meta.get("type", "")),
        "tags": ",".join(str(item) for item in tags),
        "prereq": ",".join(str(item) for item in prereq),
        "source": str(meta.get("source", "")),
    }
