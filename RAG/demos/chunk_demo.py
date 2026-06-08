from pathlib import Path
import sys

RAG_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = RAG_ROOT.parent
sys.path.insert(0, str(RAG_ROOT))

from RAG.core.chunk_utils import chunk_markdown

TEST_DIR = PROJECT_ROOT / "test"


def load_markdown_files() -> list[Path]:
    return sorted(TEST_DIR.glob("*.md"))


if __name__ == "__main__":
    files = load_markdown_files()

    if not files:
        raise RuntimeError(f"没有找到 Markdown 文件，请检查目录：{TEST_DIR}")

    for path in files:
        content = path.read_text(encoding="utf-8", errors="replace")
        chunks = chunk_markdown(path=path, content=content)

        print(f"\n文件：{path}")
        print(f"切出 {len(chunks)} 个 chunk")

        for chunk in chunks:
            preview = chunk["content"][:90].replace("\n", " ")
            print("  metadata：", chunk["metadata"])
            print(
                f"- {chunk['chunk_id']} | "
                f"{len(chunk['content'])} chars | "
                f"{chunk['heading'] or '(no heading)'}"
            )
            print(f"  预览：{preview}")
