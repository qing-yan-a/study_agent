import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .file_tools import WORKSPACE_ROOT
from .tool_registry import tool


# Tavily CLI 的位置，和 web_search_tools.py 保持一致。
TVLY_EXE = Path.home() / ".local" / "bin" / "tvly.exe"

# 单次最多抽取几个 URL。
# v0.3 建议先限制为 2，方便少量多次读入。
MAX_URLS_PER_CALL = 2

# 每个网页正文最多返回多少字符。
# 这里不是保存全文，而是防止一次把上下文撑爆。
MAX_CONTENT_CHARS = 3000

# 调用 Tavily CLI 的超时时间。
COMMAND_TIMEOUT_SECONDS = 30


def is_http_url(url: str) -> bool:
    # 只允许 http / https，避免模型传 file://、本地路径或其他奇怪协议。
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_pdf_url(url: str) -> bool:
    # 简单判断 PDF。v0.3 先不自动抽 PDF，因为 PDF 可能很长，也涉及版权/抽取质量问题。
    lower_url = url.lower()
    return lower_url.endswith(".pdf") or ".pdf" in lower_url


def normalize_extracted_item(item: dict[str, Any], extracted_at: str) -> dict[str, Any]:
    # Tavily extract 返回里通常有 raw_content。
    # 我们只截断返回，不在 v0.3 里做总结。
    raw_content = str(item.get("raw_content") or "")

    return {
        "url": str(item.get("url") or ""),
        "title": str(item.get("title") or ""),
        "content_preview": raw_content[:MAX_CONTENT_CHARS],
        "content_chars": len(raw_content),
        "truncated": len(raw_content) > MAX_CONTENT_CHARS,
        "extracted_at": extracted_at,
    }


@tool(
    name="extract_selected_sources",
    description=(
        "只对用户已经确认过的 URL 做网页正文抽取。"
        "本工具不搜索新来源，不 crawl，不 research，不 map，不自动总结，不生成草稿，不写入长期记忆。"
        "单次最多抽取 2 个 URL。"
        "返回内容是截断后的正文预览和元数据，不代表已经完成资料整理。"
        "PDF 默认不抽取，除非用户明确允许 allow_pdf=true。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "urls": {
                "type": "array",
                "description": "用户已经确认要抽取的 URL 列表，单次最多 2 个。",
                "items": {
                    "type": "string"
                },
            },
            "allow_pdf": {
                "type": "boolean",
                "description": "是否允许抽取 PDF。默认 false，只有用户明确允许时才传 true。",
            },
        },
        "required": ["urls"],
        "additionalProperties": False,
    },
    risk="low",
)
def extract_selected_sources(
    urls: list[str],
    allow_pdf: bool = False,
) -> dict[str, Any]:
    # 1. 参数类型校验。
    if not isinstance(urls, list) or not urls:
        raise ValueError("urls 必须是非空列表")

    if len(urls) > MAX_URLS_PER_CALL:
        raise ValueError(f"单次最多只能抽取 {MAX_URLS_PER_CALL} 个 URL")

    # 2. URL 安全校验。
    normalized_urls = []

    for url in urls:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("urls 里的每一项都必须是非空字符串")

        clean_url = url.strip()

        if not is_http_url(clean_url):
            raise ValueError(f"只允许 http/https URL：{clean_url}")

        if is_pdf_url(clean_url) and not allow_pdf:
            raise ValueError(f"PDF 默认不抽取，需要用户明确允许 allow_pdf=true：{clean_url}")

        normalized_urls.append(clean_url)

    # 3. 检查 Tavily CLI 是否存在。
    if not TVLY_EXE.exists():
        raise FileNotFoundError(f"找不到 Tavily CLI：{TVLY_EXE}")

    # 4. 组装命令。
    # 等价于：
    # tvly extract URL1 URL2 --format markdown --json
    command = [
        str(TVLY_EXE),
        "extract",
        *normalized_urls,
        "--format",
        "markdown",
        "--json",
    ]

    # 5. 执行命令。
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

    # 6. Tavily 调用失败时，抛出错误，让工具层返回给 Agent。
    if result.returncode != 0:
        raise RuntimeError(
            "extract_selected_sources 调用 Tavily CLI 失败："
            f"exit_code={result.returncode}, stderr={result.stderr[:500]}"
        )

    # 7. 解析 JSON 输出。
    data = json.loads(result.stdout)
    extracted_at = datetime.now(timezone.utc).isoformat()

    raw_results = data.get("results", [])
    failed_results = data.get("failed_results", [])

    # 8. 返回结构化结果。
    return {
        "url_count": len(normalized_urls),
        "extracted_count": len(raw_results),
        "results": [
            normalize_extracted_item(item, extracted_at)
            for item in raw_results
        ],
        "failed_results": failed_results,
    }