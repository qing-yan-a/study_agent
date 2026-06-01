import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("MIMO_API_KEY")
base_url = os.getenv("MIMO_BASE_URL")
model = os.getenv("MIMO_MODEL")

if not api_key:
    raise RuntimeError("Missing MIMO_API_KEY. Please configure it in .env first.")

client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0)


def get_display_score(chunk: dict[str, Any]) -> float:
    """统一取检索分数：Hybrid 结果用 final_score，纯向量结果用 score。"""
    if "final_score" in chunk:
        return float(chunk["final_score"])

    return float(chunk.get("score", 0.0))


def build_context(chunks: list[dict[str, Any]]) -> str:
    """把检索到的 chunk 拼成适合发给 LLM 的上下文文本。"""
    parts = []

    for i, chunk in enumerate(chunks, start=1):
        parts.append(
            "\n".join(
                [
                    f"[Source {i}]",
                    f"chunk_id: {chunk['chunk_id']}",
                    f"file: {chunk['path']}",
                    f"heading: {chunk['heading'] or '(no heading)'}",
                    f"score: {get_display_score(chunk):.4f}",
                    "content:",
                    chunk["content"],
                ]
            )
        )

    return "\n\n---\n\n".join(parts)


def answer_with_context(query: str, context: str) -> str:
    """把用户问题和检索上下文发给 LLM，让模型只基于资料回答。"""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a careful RAG assistant. "
                "Answer only based on the provided context. "
                "If the context is insufficient, say that the available material is insufficient. "
                "Do not invent facts that are not in the context. "
                "Cite the provided sources when possible."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Context:\n{context}\n\n"
                f"Question: {query}"
            ),
        },
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )

    return response.choices[0].message.content or ""
