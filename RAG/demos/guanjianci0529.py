import json
from pathlib import Path
from typing import Any
def tokenize_query(query: str) -> list[str]:
    return [
        token.strip()#strip去除空字符
        #把中文问号？替换成空格。
        for token in query.replace("？", " ").replace("?", " ").split()
        if token.strip()
    ]
#按关键词给分
def keyword_match_score(query: str, item: dict[str, Any]) -> float:
    target_text = "\n".join(
        [
            item["path"],
            item["chunk_id"],
            item["heading"],
            item["content"],
        ]
    ).lower()#把英文统一转小写。

    query_text = query.lower().strip()

    if not query_text:
        return 0.0

    score = 0.0

    if query_text in target_text:
        score += 1.0

    for token in tokenize_query(query_text):
        if token and token in target_text:
            score += 0.2

    return min(score, 1.0)

"""def demo_tokenize_query() -> None:
    test_queries = [
        "豆包 TTS API 更新了吗？",
        "4.10发生了什么？",
        "2026-04-23 发生了什么?",
        "帮我找 HospitalPersistence 相关内容",
    ]

    for query in test_queries:
        print("query:", query)
        print("tokens:", tokenize_query(query))
        print("-" * 40)


if __name__ == "__main__":
    demo_tokenize_query()"""
def demo_keyword_score() -> None:
    index_path = Path(__file__).resolve().parent.parent / "data" / "rag_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))

    query = "豆包 不存在词 更新"

    for item in index[:5]:
        score = keyword_match_score(query, item)

        print("chunk_id:", item["chunk_id"])
        print("heading:", item["heading"])
        print("score:", score)
        print("-" * 40)


if __name__ == "__main__":
    demo_keyword_score()