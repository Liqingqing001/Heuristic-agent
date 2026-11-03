"""Shared, bounded Markdown corpus for vector and lexical retrieval.

A snapshot is published only after every source has been read and validated. File
stat signatures invalidate the in-process cache; content hashes version indexes.
"""
from __future__ import annotations

import hashlib
import math
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from app import config
from app.utils import kp_meta

CHUNK_TOKENS = 350
CHUNKER_VERSION = "markdown-v2"
_CATEGORIES = ("lecture", "solutions", "buglib", "kp")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_ANSWER = re.compile(r"标准答案|参考答案|完整解法|参考解法|完整代码|完整实现|参考实现|参考代码|答案解析")
_lock = threading.RLock()
_cache_key = None
_cache = None


@dataclass(frozen=True)
class CorpusSnapshot:
    chunks: tuple[dict, ...]
    version: str
    files: tuple[dict, ...]


def estimate_tokens(text: str) -> int:
    """Conservative local estimate, not a model tokenizer: CJK=1, ASCII≈3 chars."""
    return sum(math.ceil(len(token) / 3) if token.isascii() else 1
               for token in re.findall(r"[A-Za-z0-9_]+|[^\s]", text))


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _truncate(text: str, budget: int) -> str:
    if estimate_tokens(text) <= budget:
        return text
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        if estimate_tokens(text[:mid]) <= budget:
            low = mid
        else:
            high = mid - 1
    return text[:low]


def _sections(text: str):
    """Recognize headings outside fences and retain their ancestry."""
    path, body, fence = [], [], None
    for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        marker = _FENCE.match(line)
        if marker:
            if fence is None:
                fence = marker.group(1)
            elif marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence) and not marker.group(2).strip():
                fence = None
            body.append(line)
            continue
        heading = _HEADING.match(line) if fence is None else None
        if heading:
            if any(part.strip() for part in body):
                yield " / ".join(name for _, name in path), "\n".join(body).strip()
            level, title = len(heading.group(1)), heading.group(2)
            path = [(depth, name) for depth, name in path if depth < level]
            path.append((level, title))
            body = []
        else:
            body.append(line)
    if any(part.strip() for part in body):
        yield " / ".join(name for _, name in path), "\n".join(body).strip()


def _blocks(text: str):
    paragraph, code, marker, language = [], [], None, ""
    for line in text.splitlines():
        matched = _FENCE.match(line)
        if marker:
            if matched and matched.group(1)[0] == marker[0] and len(matched.group(1)) >= len(marker) and not matched.group(2).strip():
                yield "\n".join(code), marker, language
                code, marker = [], None
            else:
                code.append(line)
        elif matched:
            if paragraph:
                yield "\n".join(paragraph), None, ""
                paragraph = []
            marker, language = matched.group(1), matched.group(2).strip()
        elif not line.strip():
            if paragraph:
                yield "\n".join(paragraph), None, ""
                paragraph = []
        else:
            paragraph.append(line)
    if marker:
        # A source with an unfinished fence is made structurally safe for prompts.
        yield "\n".join(code), marker, language
    elif paragraph:
        yield "\n".join(paragraph), None, ""


def _pieces(text: str, budget: int):
    while text:
        piece = _truncate(text, budget)
        if not piece:
            raise ValueError("Chunk budget cannot hold one character")
        if len(piece) < len(text):
            # Prefer line/sentence boundaries, but never exceed the budget.
            cut = max(piece.rfind("\n"), piece.rfind("。") + 1, piece.rfind(" "))
            if cut > len(piece) // 2:
                piece = piece[:cut]
        yield piece
        text = text[len(piece):].lstrip("\r\n")


def _chunks(text: str, title: str, max_tokens: int):
    if max_tokens < 32:
        raise ValueError("max_tokens must be at least 32")
    for section, body in _sections(text):
        heading = "｜".join(dict.fromkeys(part for part in (title, section) if part))
        prefix = _truncate(heading, max_tokens // 4)
        prefix = prefix + "\n" if prefix else ""
        budget = max_tokens - estimate_tokens(prefix)
        pending = ""
        for block, marker, language in _blocks(body):
            if marker:
                language = _truncate(language, 12)
                opening, closing = marker + language + "\n", "\n" + marker
                overhead = estimate_tokens(opening + closing)
                for piece in _pieces(block, budget - overhead):
                    rendered = opening + piece + closing
                    if pending:
                        yield section, prefix + pending
                        pending = ""
                    yield section, prefix + rendered
            else:
                for piece in _pieces(block, budget):
                    candidate = (pending + "\n\n" + piece).strip()
                    if pending and estimate_tokens(candidate) > budget:
                        yield section, prefix + pending
                        pending = piece
                    else:
                        pending = candidate
        if pending:
            yield section, prefix + pending


def split_markdown(text: str, max_tokens: int = CHUNK_TOKENS) -> list[str]:
    """Bound by estimated tokens, retain heading paths and balanced code fences."""
    return [chunk for _, chunk in _chunks(text, "", max_tokens)]


def snapshot() -> CorpusSnapshot:
    """Return cached source chunks, invalidating on file add/edit/delete.

    Treat returned dictionaries as read-only. Parsing errors never replace the
    previously cached snapshot, allowing the caller to retain an active index.
    """
    global _cache_key, _cache
    root = Path(config.KNOWLEDGE_DIR)
    with _lock:
        paths = sorted(path for category in _CATEGORIES for path in (root / category).glob("*.md")
                       if not path.name.startswith("_") and path.name.lower() != "readme.md")
        signatures = tuple((str(path), path.stat().st_mtime_ns, path.stat().st_size) for path in paths)
        key = (str(root.resolve()), CHUNKER_VERSION, CHUNK_TOKENS, signatures)
        if key == _cache_key and _cache is not None:
            return _cache
        chunks, files = [], []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            category, title, body = path.parent.name, path.stem, text
            document_id = path.relative_to(root).as_posix()
            base = {"kp_id": None, "chapter": None, "difficulty": None}
            if category == "kp":
                meta, body = kp_meta.parse_front_matter(text)
                if not kp_meta.KP_ID_RE.fullmatch(str(meta.get("id", ""))) or not meta.get("title"):
                    raise kp_meta.KpFormatError(f"{path.name}: missing/invalid id or title")
                try:
                    chapter, difficulty = int(meta["chapter"]), int(meta["difficulty"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise kp_meta.KpFormatError(f"{path.name}: invalid chapter/difficulty") from exc
                title = str(meta["title"])
                base = {"kp_id": str(meta["id"]), "chapter": chapter, "difficulty": difficulty}
            else:
                first_heading = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
                if first_heading:
                    title = first_heading.group(1).strip()
            document_hash = _digest(text)
            files.append({"document_id": document_id, "content_hash": document_hash,
                          "source": path.name, "category": category})
            occurrences = {}
            for section, chunk in _chunks(body, title, CHUNK_TOKENS):
                content_hash = _digest(chunk)
                stable = document_id + "\n" + section + "\n" + content_hash
                occurrence = occurrences.get(stable, 0)
                occurrences[stable] = occurrence + 1
                chunks.append({"chunk_id": _digest(stable + f"\n{occurrence}"),
                               "document_id": document_id, "content_hash": content_hash,
                               "category": category, "source": path.name, "title": title,
                               "section": section, "text": chunk,
                               "audience": "solution" if category == "solutions" or _ANSWER.search(section) else "hint",
                               **base})
        # Retry on a concurrent edit instead of caching an inconsistent signature.
        after = tuple((str(path), path.stat().st_mtime_ns, path.stat().st_size) for path in paths)
        if after != signatures:
            raise RuntimeError("Knowledge sources changed during snapshot; retry ingestion")
        version = _digest(CHUNKER_VERSION + f":{CHUNK_TOKENS}\n" + "\n".join(f"{f['document_id']}:{f['content_hash']}" for f in files))
        candidate = CorpusSnapshot(tuple(chunks), version, tuple(files))
        _cache_key, _cache = key, candidate
        return candidate
