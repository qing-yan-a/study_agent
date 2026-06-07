import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .file_tools import WORKSPACE_ROOT
from .tool_registry import tool


TVLY_EXE = Path.home() / ".local" / "bin" / "tvly.exe"
MAX_WEB_RESULTS = 10
MAX_SNIPPET_CHARS = 500
COMMAND_TIMEOUT_SECONDS = 30


def get_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()


def normalize_result(item: dict[str, Any], retrieved_at: str) -> dict[str, Any]:
    url = str(item.get("url", ""))
    content = str(item.get("content") or "")

    return {
        "title": str(item.get("title") or ""),
        "url": url,
        "snippet": content[:MAX_SNIPPET_CHARS],
        "source": get_domain(url),
        "score": item.get("score"),
        "retrieved_at": retrieved_at,
    }


@tool(
    name="web_search",
    description=(
        "搜索公开网页资料，返回候选来源列表。"
        "当用户问题需要公开资料、外部来源、最新信息或网页来源时调用。"
        "本工具只做搜索结果发现，不抽取网页全文，不自动总结网页，不下载 PDF，"
        "不写入长期记忆，也不生成资料包或自动上架。"
        "工具结果只是候选来源，最终回答必须说明需要用户人工确认来源可靠性。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词。应是简短搜索 query，不要传长篇任务说明。",
            },
            "max_results": {
                "type": "integer",
                "description": "最多返回多少条结果。默认 5，最大 10。",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    risk="low",
)
def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query 必须是非空字符串")

    if not isinstance(max_results, int) or max_results <= 0:
        raise ValueError("max_results 必须是正整数")

    max_results = min(max_results, MAX_WEB_RESULTS)

    if not TVLY_EXE.exists():
        raise FileNotFoundError(f"找不到 Tavily CLI：{TVLY_EXE}")

    command = [
        str(TVLY_EXE),
        "search",
        query.strip(),
        "--max-results",
        str(max_results),
        "--json",
    ]

    result = subprocess.run(
        command,
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=COMMAND_TIMEOUT_SECONDS,
        shell=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "web_search 调用 Tavily CLI 失败："
            f"exit_code={result.returncode}, stderr={result.stderr[:500]}"
        )

    data = json.loads(result.stdout)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    raw_results = data.get("results", [])

    return {
        "query": query.strip(),
        "result_count": len(raw_results),
        "results": [
            normalize_result(item, retrieved_at)
            for item in raw_results[:max_results]
        ],
    }
