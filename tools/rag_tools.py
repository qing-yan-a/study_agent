from typing import Any

from RAG.core.index_store import INDEX_FILE, load_and_build_index, load_index
from RAG.core.rag_pipeline import build_context
from RAG.core.retrieval import retrieve_hybrid_chunks

from .tool_registry import tool


@tool(
    name="search_memory",
    description=(
            "在本地 RAG 记忆资料中检索与用户问题相关的内容。"
            "当用户询问过去记录、学习进度、项目记忆、某天发生了什么、某个技术点之前怎么处理时调用。"
            "本工具只读取已有索引，不会重建索引。"
            "如果本工具返回索引不存在、索引不可用或需要重建索引，"
            "应先请求调用 rebuild_memory_index，重建完成后再重新调用 search_memory。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "要检索的问题或关键词。"
            },
            "top_k": {
                "type": "integer",
                "description": "最多返回多少条结果。默认 3。"
            }
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    risk="low",
)
#调用RAG搜索
def search_memory(query: str, top_k: int = 3) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query 必须是非空字符串")

    if not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k 必须是正整数")

    if not INDEX_FILE.exists():
        raise FileNotFoundError(
            "RAG 索引不存在，请先调用 rebuild_memory_index 重建索引。"
        )

    index = load_index()
    results = retrieve_hybrid_chunks(query, index, top_k=top_k)
    context = build_context(results)

    sources = []

    for item in results:
        sources.append(
            {
                "chunk_id": item["chunk_id"],
                "file": item["path"],
                "heading": item["heading"],
                "score": item.get("final_score", item.get("score")),
                "metadata": item.get("metadata", {}),
            }
        )

    return {
        "query": query,
        "result_count": len(results),
        "context": context,
        "sources": sources,
    }

#重建索引工具
@tool(
    name="rebuild_memory_index",
    description=(
        "重建本地 RAG 记忆索引。"
        "当 search_memory 提示索引不存在、索引过期，或用户明确要求重建 RAG 索引时调用。"
        "本工具会递归读取 test 目录下的所有 Markdown 文件，重新切片并调用 embedding API，"
        "然后覆盖保存 RAG/data/rag_index.json。"
        "由于会调用外部 embedding API 并覆盖本地索引，执行前需要用户确认。"
    ),
    input_schema={
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    risk="medium",
)
def rebuild_memory_index() -> dict[str, Any]:
    index = load_and_build_index(rebuild=True)

    return {
        "rebuilt": True,
        "chunk_count": len(index),
        "message": "RAG 记忆索引已重建。",
    }
