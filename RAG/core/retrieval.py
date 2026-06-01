import re
import jieba
from typing import Any

from RAG.core.embedding_utils import cosine_similarity, embed_text
from RAG.core.query_parser import extract_date_keywords
from rank_bm25 import BM25Okapi

MIN_SCORE = 0.4


def filter_chunks_by_metadata(
    index: list[dict[str, Any]],
    metadata_key: str,
    metadata_value: str,
) -> list[dict[str, Any]]:
    """按指定 metadata 字段过滤 chunk，例如 content_date 或 file_name。"""
    return [
        item
        for item in index
        if str(item.get("metadata", {}).get(metadata_key, "")) == metadata_value
    ]


def filter_chunks_by_date(
    index: list[dict[str, Any]],
    content_date: str,
) -> list[dict[str, Any]]:
    """按 metadata.content_date 过滤 chunk。"""
    return filter_chunks_by_metadata(index, "content_date", content_date)


def filter_chunks_by_file_name(
    index: list[dict[str, Any]],
    file_name: str,
) -> list[dict[str, Any]]:
    """按 metadata.file_name 过滤 chunk。"""
    return filter_chunks_by_metadata(index, "file_name", file_name)


def select_candidate_chunks(
    query: str,
    index: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """根据 query 中的结构化条件选择候选 chunk，并返回 filter 调试信息。"""
    total_count = len(index)

    # 日期是强过滤条件：能解析到日期并命中 metadata 时，优先缩小候选集。
    for date_keyword in extract_date_keywords(query):
        filtered_chunks = filter_chunks_by_date(index, date_keyword)

        if filtered_chunks:
            return filtered_chunks, {
                "filter_type": "date",
                "filter_key": "content_date",
                "filter_value": date_keyword,
                "candidate_count": len(filtered_chunks),
                "total_count": total_count,
            }

    query_text = query.lower()

    # 文件名也是明确条件：当用户问题里直接出现文件名时，按 file_name 过滤。
    file_names = sorted(
        {
            str(item.get("metadata", {}).get("file_name", ""))
            for item in index
            if item.get("metadata", {}).get("file_name")
        }
    )

    for file_name in file_names:
        if file_name.lower() in query_text:
            filtered_chunks = filter_chunks_by_file_name(index, file_name)

            if filtered_chunks:
                return filtered_chunks, {
                    "filter_type": "file_name",
                    "filter_key": "file_name",
                    "filter_value": file_name,
                    "candidate_count": len(filtered_chunks),
                    "total_count": total_count,
                }

    return index, {
        "filter_type": "none",
        "filter_key": None,
        "filter_value": None,
        "candidate_count": total_count,
        "total_count": total_count,
    }

#提取路径、文件名、函数名、类名等代码相关 token。
def extract_code_tokens(text: str) -> list[str]:

    patterns = [
        # 路径：RAG/core/retrieval.py 或 RAG\core\retrieval.py
        r"[a-zA-Z0-9_\-]+(?:[/\\][a-zA-Z0-9_\-.]+)+",

        # 文件名：query_parser.py、code-rag-notes.md
        r"[a-zA-Z0-9_\-]+\.(?:py|md|json|toml|yaml|yml|txt)",

        # 下划线函数名：retrieve_hybrid_chunks
        r"[a-zA-Z]+(?:_[a-zA-Z0-9]+)+",

        # 驼峰类名：HospitalPersistenceService
        r"[A-Z][a-zA-Z0-9]+(?:[A-Z][a-zA-Z0-9]+)+",
    ]

    tokens = []

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            tokens.append(match.group(0).lower())

    return list(dict.fromkeys(tokens))

# 用 jieba 做中文分词，同时保留英文、数字和技术词。
def tokenize_query(query: str) -> list[str]:
    code_tokens = extract_code_tokens(query)
    #把英文统一转小写。
    text = query.lower()
    #把标点符号、换行、制表符替换成空格。re.sub()意思是：用正则找到匹配内容→ 替换成指定内容。这里就是把一堆标点替换成" "。
    text = re.sub(
        r"[，。！？、,.!?;；:：()\[\]【】\n\r\t]+",
        " ",
        text,
    )

    tokens = []
    #去掉空格然后对每个片段做中文分词。
    for part in text.split():
        tokens.extend(jieba.lcut(part))

    result = []
#用+把code_tokens列表和tokens列表合并成一个更长的列表。
    for token in  code_tokens + tokens:
        #jieba.lcut(part)可能产生一些边缘token，再去除一遍空格
        token = token.strip()
        if token:
            result.append(token)
    #返回去重结果
    return list(dict.fromkeys(result))


def build_bm25_query_tokens(query: str) -> list[str]:
    """构造 BM25 查询 tokens，集中放 query 扩展逻辑，方便以后替换成 LLM rewrite。"""
    tokens = tokenize_query(query)

    # 当前阶段只接入日期 normalization；未来可在这里接 query rewrite / query expansion。
    tokens.extend(
        date_keyword.lower()
        for date_keyword in extract_date_keywords(query)
    )

    return list(dict.fromkeys(token for token in tokens if token))

# 把一个 chunk 中适合关键词检索的字段拼成 BM25 文档文本。
def chunk_to_bm25_text(item: dict[str, Any]) -> str:
    metadata = item.get("metadata", {})

    return "\n".join(
        [
            str(item.get("path", "")),
            str(item.get("chunk_id", "")),
            str(item.get("heading", "")),
            str(item.get("content", "")),
            str(metadata.get("file_name", "")),
            str(metadata.get("content_date", "")),
            str(metadata.get("file_created_at", "")),
            str(metadata.get("file_modified_at", "")),
        ]
    )

#  对候选 chunks 计算 BM25 分数，返回 chunk_id -> bm25_score。
def bm25_score_chunks(
    query: str,
    chunks: list[dict[str, Any]],
) -> dict[str, float]:
    corpus_tokens = []

    for item in chunks:
        text = chunk_to_bm25_text(item)
        tokens = tokenize_query(text)
        corpus_tokens.append(tokens)
    #这一步会根据所有chunk计算词频、逆文档频率等信息。
    bm25 = BM25Okapi(corpus_tokens)

    query_tokens = build_bm25_query_tokens(query)

    scores = bm25.get_scores(query_tokens)

    return {
        item["chunk_id"]: float(score)
        for item, score in zip(chunks, scores)
    }

#归一化bm25分数
def normalize_scores(scores: list[float]) -> list[float]:
    """把一组非负分数按最大值归一化到 0~1。"""
    if not scores:
        return []

    max_score = max(scores)

    if max_score <= 0:
        return [0.0 for _ in scores]

    return [
        score / max_score
        for score in scores
    ]

#计算 query 和单个 chunk 的字面关键词匹配分。
def keyword_match_score(query: str, item: dict[str, Any]) -> float:

    target_text = "\n".join(
        [
            str(item.get("path", "")),
            str(item.get("chunk_id", "")),
            str(item.get("heading", "")),
            str(item.get("content", "")),
            str(item.get("metadata", {})),
        ]
    ).lower()

    query_text = query.lower().strip()

    if not query_text:
        return 0.0

    score = 0.0

    if query_text in target_text:
        score += 1.0

    # 这里暂时允许普通 token 和日期扩展词重复打分，后续观察到问题再拆开。
    for token in tokenize_query(query_text):
        if token in target_text:
            score += 0.2

    for date_keyword in extract_date_keywords(query_text):
        if date_keyword.lower() in target_text:
            score += 0.5

    return min(score, 1.0)


def retrieve_top_k_chunks(
    query: str,
    index: list[dict[str, Any]],
    top_k: int = 3,
    min_score: float = MIN_SCORE,
) -> list[dict[str, Any]]:
    """纯向量检索：用 query embedding 和 chunk embedding 的余弦相似度排序。"""
    query_vector = embed_text(query, input_type="query")

    results = []

    for item in index:
        score = cosine_similarity(query_vector, item["embedding"])

        results.append(
            {
                "score": score,
                "path": item["path"],
                "chunk_id": item["chunk_id"],
                "heading": item["heading"],
                "content": item["content"],
                "metadata": item.get("metadata", {}),
            }
        )

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    filtered_results = [
        item for item in results
        if item["score"] >= min_score
    ]

    return filtered_results[:top_k]


def retrieve_hybrid_chunks(
    query: str,
    index: list[dict[str, Any]],
    top_k: int = 3,
    dense_weight: float = 0.7,
    keyword_weight: float = 0.3,
    return_all_when_filtered: bool = True,
) -> list[dict[str, Any]]:
    """内存版混合检索：先做 metadata filter，再融合向量相似度和关键词匹配分。"""
    candidate_chunks, filter_info = select_candidate_chunks(query, index)
    query_vector = embed_text(query, input_type="query")
    bm25_score_by_chunk_id = bm25_score_chunks(query, candidate_chunks)

    bm25_scores = []

    for item in candidate_chunks:
        chunk_id = item["chunk_id"]
        #去BM25分数字典里查这个chunk的分数
        score = bm25_score_by_chunk_id[chunk_id]
        bm25_scores.append(score)

    normalized_bm25_scores = normalize_scores(bm25_scores)
    results = []

    for item, bm25_score in zip(candidate_chunks, normalized_bm25_scores):
        dense_score = cosine_similarity(query_vector, item["embedding"])

        final_score = (
                dense_weight * dense_score
                + keyword_weight * bm25_score
        )

        results.append(
            {
                "final_score": final_score,
                "dense_score": dense_score,
                "bm25_score": bm25_score,
                "path": item["path"],
                "chunk_id": item["chunk_id"],
                "heading": item["heading"],
                "content": item["content"],
                "metadata": item.get("metadata", {}),
                "filter_info": filter_info,
            }
        )

    results.sort(
        key=lambda item: item["final_score"],
        reverse=True,
    )

    # 如果用户给了明确范围（日期/文件名），优先返回该范围内全部 chunk，方便后续总结。
    if return_all_when_filtered and filter_info["filter_type"] != "none":
        return results

    return results[:top_k]
