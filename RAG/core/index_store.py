import json
from pathlib import Path
from typing import Any
from RAG.core.chunk_utils import chunk_markdown
from RAG.core.embedding_utils import embed_text

RAG_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = RAG_ROOT.parent
TEST_DIR = PROJECT_ROOT / "test"
INDEX_FILE = RAG_ROOT / "data" / "rag_index.json"


def load_documents() -> list[dict[str, str]]:
    """加载测试目录里的 Markdown 文档，作为本地 RAG 的原始资料。"""
    documents = []

    for path in sorted(TEST_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8", errors="replace")

        documents.append(
            {
                "path": str(path),
                "content": content,
            }
        )

    return documents

# """把文档切成 chunk，并为每个 chunk 生成 embedding 后组成内存索引。"""
def build_index(documents: list[dict[str, str]]) -> list[dict[str, Any]]:

    index = []

    for doc in documents:
        chunks = chunk_markdown(
            path=doc["path"],
            content=doc["content"],
        )

        for chunk in chunks:
            vector = embed_text(chunk["content"], input_type="document")

            index.append(
                {
                    "path": chunk["path"],
                    "chunk_id": chunk["chunk_id"],
                    "heading": chunk["heading"],
                    "content": chunk["content"],
                    "embedding": vector,
                    "metadata": chunk["metadata"],
                }
            )

    return index

# """把构建好的索引保存成 JSON，避免每次查询都重新 embedding。"""
def save_index(index: list[dict[str, Any]]) -> None:

    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

#  """从本地 JSON 文件读取已经构建好的索引。"""
def load_index() -> list[dict[str, Any]]:

    return json.loads(INDEX_FILE.read_text(encoding="utf-8"))


def load_and_build_index(rebuild: bool = False) -> list[dict[str, Any]]:
    """优先读取已有索引；需要重建或索引不存在时，重新加载文档并构建。"""
    if INDEX_FILE.exists() and not rebuild:
        print("Loading existing index...")
        return load_index()

    if rebuild:
        print("Rebuilding index...")
    else:
        print("Index does not exist, building...")

    documents = load_documents()

    if not documents:
        raise RuntimeError(f"No documents found in: {TEST_DIR}")

    index = build_index(documents)
    save_index(index)

    return index
