from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from RAG.core.index_store import load_index
from RAG.core.query_parser import extract_date_keywords
from RAG.core.retrieval import (
    retrieve_hybrid_chunks,
    retrieve_top_k_chunks,
    select_candidate_chunks,
)


def print_dense_results(query: str, index: list[dict], top_k: int = 3) -> None:
    """打印纯向量检索结果，用来和 Hybrid 结果做对比。"""
    print("\n[Dense]")
    results = retrieve_top_k_chunks(query, index, top_k=top_k, min_score=0.0)

    for item in results:
        print(
            f"score={item['score']:.4f}  "
            f"{item['chunk_id']}  "
            f"{item['heading'] or '(no heading)'}"
        )


def print_hybrid_results(query: str, index: list[dict], top_k: int = 3) -> None:
    """打印混合检索结果，重点观察 final/dense/bm25 三个分数。"""
    print("\n[Hybrid]")
    results = retrieve_hybrid_chunks(query, index, top_k=top_k)
    print_filter_debug(query, index, results)

    for item in results:
        print(
            f"final={item['final_score']:.4f}  "
            f"dense={item['dense_score']:.4f}  "
            f"bm25={item['bm25_score']:.4f}  "
            f"{item['chunk_id']}  "
            f"{item['heading'] or '(no heading)'}"
        )


def print_filter_debug(
    query: str,
    index: list[dict],
    results: list[dict],
) -> None:
    """打印 metadata filter 调试信息，确认本次检索是否缩小了候选集。"""
    if results:
        filter_info = results[0]["filter_info"]
    else:
        _, filter_info = select_candidate_chunks(query, index)

    if filter_info["filter_type"] == "none":
        print(
            f"filter=none  "
            f"candidate_count={filter_info['candidate_count']}/{filter_info['total_count']}"
        )
        return

    print(
        f"filter={filter_info['filter_type']}  "
        f"{filter_info['filter_key']}={filter_info['filter_value']}  "
        f"candidate_count={filter_info['candidate_count']}/{filter_info['total_count']}"
    )


def demo_hybrid_retrieval() -> None:
    """用几组典型 query 对比纯向量检索和混合检索的排序差异。"""
    index = load_index()

    test_queries = [
        "4.10发生了什么",
        "OpenClaw 微信不回复",
        "retrieve_hybrid_chunks",
        "我最近做过哪些 RAG 检索优化",
    ]

    for query in test_queries:
        print("=" * 80)
        print(f"QUERY: {query}")
        print("normalized_date_keywords:", extract_date_keywords(query))
        print_dense_results(query, index)
        print_hybrid_results(query, index)


if __name__ == "__main__":
    demo_hybrid_retrieval()
