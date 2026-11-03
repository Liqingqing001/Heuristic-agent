"""离线 RAG 检索评测；默认 lexical，不下载模型、不调用大模型。

python scripts/eval_rag.py --mode lexical --strict --output /tmp/rag-report.json
hybrid 需要先成功建库；报告记录实际 retrieval 类型，不能把降级结果当向量评测。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time
from typing import Callable

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_DATASET = BACKEND_DIR / "data" / "rag_eval.jsonl"


def source_key(source: str) -> str:
    """知识点源文件与其 kp_id 共享同一个文档标签，避免重复计分。"""
    source = Path(source).name
    matched = re.match(r"(ds-\d{2}-\d{2})(?:-|\.)", source)
    return "kp:" + matched.group(1) if matched else "source:" + source


def expected_keys(case: dict) -> set[str]:
    return {"kp:" + key for key in case.get("relevant_kp_ids", [])} | {
        source_key(source) for source in case.get("relevant_sources", [])
    }


def evaluate_case(case: dict, results: list[dict], top_k: int) -> dict:
    expected = expected_keys(case)
    results = results[:top_k]
    found: set[str] = set()
    matched_ranks = []
    for rank, result in enumerate(results, 1):
        keys = {source_key(result.get("source", ""))}
        if result.get("kp_id"):
            keys.add("kp:" + result["kp_id"])
        matches = expected & keys
        if matches:
            matched_ranks.append(rank)
            found.update(matches)
    answerable = bool(expected)
    return {
        "id": case["id"],
        "query": case["query"],
        "answerable": answerable,
        "expected": sorted(expected),
        "matched": sorted(found),
        "hit": bool(found) if answerable else None,
        "recall": len(found) / len(expected) if answerable else None,
        "reciprocal_rank": 1 / matched_ranks[0] if matched_ranks else 0.0 if answerable else None,
        "returned_precision": len(matched_ranks) / len(results) if results and answerable else 0.0 if answerable else None,
        "correct_abstention": not results if not answerable else None,
        "results": [{key: item.get(key) for key in (
            "chunk_id", "document_id", "kp_id", "source", "section", "retrieval", "distance",
        )} for item in results],
    }


def percentile(values: list[float], percentile_value: float) -> float:
    """线性插值分位数，对单条样本和空样本同样有定义。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile_value
    lower = math.floor(index)
    upper = math.ceil(index)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def evaluate(cases: list[dict], search: Callable, mode: str, top_k: int, audience: str = "hint") -> dict:
    measured = []
    for case in cases:
        started = time.perf_counter()
        kwargs = {"top_k": top_k, "mode": mode, "audience": audience}
        if case.get("categories"):
            kwargs["categories"] = case["categories"]
        results = search(case["query"], **kwargs)
        elapsed = (time.perf_counter() - started) * 1000
        report = evaluate_case(case, results, top_k)
        report["latency_ms"] = round(elapsed, 3)
        measured.append(report)
    answerable = [case for case in measured if case["answerable"]]
    unanswerable = [case for case in measured if not case["answerable"]]
    mean = lambda key: statistics.mean(case[key] for case in answerable) if answerable else None
    retrieval_modes: dict[str, int] = {}
    for case in measured:
        for result in case["results"]:
            name = result.get("retrieval") or "unspecified"
            retrieval_modes[name] = retrieval_modes.get(name, 0) + 1
    latencies = [case["latency_ms"] for case in measured]
    return {
        "requested_mode": mode,
        "audience": audience,
        "top_k": top_k,
        "case_count": len(measured),
        "answerable_count": len(answerable),
        "unanswerable_count": len(unanswerable),
        "metrics": {
            "hit_at_k": mean("hit"),
            "recall_at_k": mean("recall"),
            "mrr": mean("reciprocal_rank"),
            "returned_precision": mean("returned_precision"),
            "no_answer_accuracy": statistics.mean(case["correct_abstention"] for case in unanswerable) if unanswerable else None,
            "latency_p50_ms": round(percentile(latencies, .5), 3),
            "latency_p95_ms": round(percentile(latencies, .95), 3),
        },
        "retrieval_modes": retrieval_modes,
        "cases": measured,
        "limits": "检索文档相关性标注；不评估大模型答案质量。延迟包含首个请求的冷启动，不代表线上并发性能。",
    }


def load_cases(path: Path) -> list[dict]:
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids: set[str] = set()
    for case in cases:
        if not case.get("id") or case["id"] in ids or not isinstance(case.get("query"), str) or not case["query"].strip():
            raise ValueError("评测样本需要唯一 id 和非空 query")
        ids.add(case["id"])
        for key in ("relevant_kp_ids", "relevant_sources"):
            if not isinstance(case.get(key), list) or not all(isinstance(value, str) for value in case[key]):
                raise ValueError(f"{case['id']} 的 {key} 必须是字符串数组")
    if not cases:
        raise ValueError("评测集不能为空")
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("lexical", "hybrid"), default="lexical")
    parser.add_argument("--audience", choices=("hint", "all"), default="hint", help="hint 遵循学生端策略，排除答案；all 用于全语料检索算法对比")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true", help="Hit@K 至少 0.75，无答案准确率至少 0.8；缺少任一类样本也不通过")
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k 必须大于 0")
    from app.core.rag import search

    report = evaluate(load_cases(args.dataset), search, args.mode, args.top_k, args.audience)
    report["dataset"] = str(args.dataset)
    report["dataset_sha256"] = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"RAG 检索评测 · {args.mode} / {args.audience} · top-{args.top_k} · {report['case_count']} 个问题")
    for key, value in report["metrics"].items():
        print(f"  {key}: {value:.4f}" if value is not None else f"  {key}: N/A")
    print("  实际检索模式:", json.dumps(report["retrieval_modes"], ensure_ascii=False))
    misses = [case["id"] for case in report["cases"] if case["hit"] is False or case["correct_abstention"] is False]
    print("  未命中/未拒答:", ", ".join(misses) or "无")
    metrics = report["metrics"]
    if args.strict and ((metrics["hit_at_k"] or 0) < .75 or (metrics["no_answer_accuracy"] or 0) < .8):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
