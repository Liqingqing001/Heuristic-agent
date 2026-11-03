"""Regression coverage for source identity, bounded chunks and cache publication."""
from pathlib import Path

import pytest

from app.core import corpus


def write(root: Path, name: str, text: str):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def kp(title="链表", body="## 概念\n\n指针连接节点。"):
    return f"---\nid: ds-01-01\nchapter: 1\ntitle: {title}\ndifficulty: 2\n---\n{body}"


def test_bounded_heading_paths_and_chinese():
    chunks = corpus.split_markdown("# 数据结构\n\n## 链表\n\n" + "指针和结点。" * 250, max_tokens=90)
    assert len(chunks) > 5
    assert all(corpus.estimate_tokens(chunk) <= 90 for chunk in chunks)
    assert all("数据结构 / 链表" in chunk for chunk in chunks)
    assert sum(chunk.count("指针和结点") for chunk in chunks) > 200


def test_code_fences_are_preserved_and_oversize_code_is_balanced():
    code = "```cpp\n    int x = 1;\n    x++;\n```"
    chunks = corpus.split_markdown("# 示例\n\n" + code)
    assert len(chunks) == 1
    assert code in chunks[0]
    long = "# 示例\n\n```cpp\n" + "    p = p->next;\n" * 100 + "```"
    chunks = corpus.split_markdown(long, max_tokens=70)
    assert len(chunks) > 2
    assert all(chunk.count("```") == 2 for chunk in chunks)
    assert all(corpus.estimate_tokens(chunk) <= 70 for chunk in chunks)


def test_fenced_headings_do_not_create_sections():
    text = "# C 示例\n\n```c\n## fake_heading\nint n;\n```\n\n## 原理\n指针。"
    chunks = corpus.split_markdown(text)
    assert len(chunks) == 2
    assert "## fake_heading" in chunks[0]
    assert "C 示例 / 原理" in chunks[1]


def test_no_heading_document_splits_paragraphs_and_long_ascii():
    chunks = corpus.split_markdown(("hello world " * 50 + "\n\n") * 8, max_tokens=75)
    assert len(chunks) > 8
    assert all(corpus.estimate_tokens(chunk) <= 75 for chunk in chunks)


def test_snapshot_auto_invalidates_add_edit_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus.config, "KNOWLEDGE_DIR", tmp_path)
    source = write(tmp_path, "lecture/a.md", "# 链表\n\n## 插入\n保存后继指针。")
    first = corpus.snapshot()
    assert corpus.snapshot() is first
    source.write_text("# 链表\n\n## 插入\n先保存后继，再更新指针。", encoding="utf-8")
    second = corpus.snapshot()
    assert second.version != first.version
    assert second.chunks[0]["chunk_id"] != first.chunks[0]["chunk_id"]
    extra = write(tmp_path, "buglib/b.md", "# 断链\n\n指针覆盖。")
    third = corpus.snapshot()
    assert len(third.files) == 2
    extra.unlink()
    assert corpus.snapshot().version == second.version
    source.unlink()
    assert not corpus.snapshot().chunks


def test_stable_ids_and_solution_audience(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus.config, "KNOWLEDGE_DIR", tmp_path)
    source = write(tmp_path, "kp/ds-01-01.md", kp(body="## 概念\n链表指针。\n\n## 参考答案\n完整解法。"))
    write(tmp_path, "solutions/a.md", "# 反转链表\n\n保存后继。")
    write(tmp_path, "lecture/README.md", "Ignore")
    write(tmp_path, "kp/_TEMPLATE.md", "Ignore")
    first = corpus.snapshot()
    hints = [c for c in first.chunks if c["category"] == "kp" and c["audience"] == "hint"]
    assert len(hints) == 1
    assert hints[0]["kp_id"] == "ds-01-01"
    assert hints[0]["document_id"] == "kp/ds-01-01.md"
    assert len(first.files) == 2
    assert len([c for c in first.chunks if c["audience"] == "solution"]) == 2
    source.write_text(kp(body="## 新小节\n新内容。\n\n## 概念\n链表指针。\n\n## 参考答案\n完整解法。"), encoding="utf-8")
    assert hints[0]["chunk_id"] in {c["chunk_id"] for c in corpus.snapshot().chunks}


def test_invalid_kp_does_not_replace_good_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus.config, "KNOWLEDGE_DIR", tmp_path)
    source = write(tmp_path, "kp/ds-01-01.md", kp())
    good = corpus.snapshot()
    source.write_text("Broken YAML", encoding="utf-8")
    with pytest.raises(ValueError):
        corpus.snapshot()
    assert corpus._cache is good
