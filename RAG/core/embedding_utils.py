import os
from typing import Any
import voyageai
from dotenv import load_dotenv

#绘图
load_dotenv()

voyage_api_key = os.getenv("VOYAGE_API_KEY")
embedding_model = os.getenv("VOYAGE_EMBEDDING_MODEL", "voyage-4-lite")

if not voyage_api_key:
    raise RuntimeError("缺少 VOYAGE_API_KEY，请先在 .env 中配置。")

vo = voyageai.Client(api_key=voyage_api_key)


def get_embedding_model() -> str:
    return embedding_model

#向量化
def embed_text(text: str, input_type: str) -> list[float]:
    result = vo.embed(
        [text],
        model=embedding_model,
        input_type=input_type,
    )

    return result.embeddings[0]

#余弦相似度
def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)

#排序
def rank_by_similarity(question: str, texts: list[str]) -> list[tuple[float, int, str]]:
   #问题向量化
    query_vector = embed_text(question, input_type="query")

    results = []

    for index, text in enumerate(texts, start=1):
        #文本相似度
        doc_vector = embed_text(text, input_type="document")
        #计算余弦相似度
        score = cosine_similarity(query_vector, doc_vector)
        results.append((score, index, text))
    #结果排序返回
    return sorted(results, reverse=True, key=lambda item: item[0])

#简述
def short_label(text: str, max_chars: int = 12) -> str:
    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "..."

#绘图
def visualize_embedding_2d(question: str, texts: list[str]) -> None:
    import matplotlib
    import matplotlib.pyplot as plt
    from sklearn.decomposition import PCA

    matplotlib.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
    ]
    matplotlib.rcParams["axes.unicode_minus"] = False

    vectors = [embed_text(question, input_type="query")]

    for text in texts:
        vectors.append(embed_text(text, input_type="document"))

    points = PCA(n_components=2).fit_transform(vectors)

    plt.figure(figsize=(11, 8))

    plt.scatter(
        points[0, 0],
        points[0, 1],
        marker="*",
        s=320,
        color="crimson",
        label="Question",
    )
    plt.text(
        points[0, 0],
        points[0, 1],
        " Q: " + short_label(question),
        fontsize=10,
        weight="bold",
    )

    for i in range(1, len(points)):
        plt.scatter(points[i, 0], points[i, 1], color="steelblue")
        plt.text(
            points[i, 0],
            points[i, 1],
            f" T{i}: " + short_label(texts[i - 1]),
            fontsize=8,
        )

    plt.title("Embedding 2D Visualization with PCA")
    plt.xlabel("PCA 1")
    plt.ylabel("PCA 2")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()

    print("二维可视化图已显示。")
    print("\n文本编号：")
    print("Q:", question)

    for i, text in enumerate(texts, start=1):
        print(f"T{i}: {text}")
