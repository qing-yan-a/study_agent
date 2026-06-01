import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from RAG.core.index_store import load_and_build_index
from RAG.core.rag_pipeline import answer_with_context, build_context
from RAG.core.retrieval import MIN_SCORE, retrieve_hybrid_chunks


def should_rebuild_index() -> bool:
    return "--rebuild" in sys.argv


if __name__ == "__main__":
    index = load_and_build_index(rebuild=should_rebuild_index())

    print(f"Index chunks: {len(index)}")

    query = input("Question: ")

    results = retrieve_hybrid_chunks(query, index, top_k=3)

    if not results:
        print(f"\nNo chunks found with score >= {MIN_SCORE}.")
        print("Answer: available material is insufficient.")
        exit()

    context = build_context(results)
    print("\nContext:")
    print(context)

    answer = answer_with_context(query, context)
    print(f"\nAnswer: {answer}")
