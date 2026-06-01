from pathlib import Path
from typing import Any
import re
from datetime import datetime

HEADING_PREFIXES = ("# ", "## ", "### ")

#判断一行文本是不是Markdown标题。
def is_heading(line: str) -> bool:
    stripped = line.lstrip()#去掉字符串左边的空白字符
    return stripped.startswith(HEADING_PREFIXES)#判断字符串是不是以某个内容开头

#获取标题
def get_heading(lines: list[str]) -> str:
    for line in lines:
        if is_heading(line):
            return line.strip()

    return ""

#从文件名提取日期
def extract_date_from_path(path: str | Path) -> str | None:
    file_name = Path(path).name

    match = re.search(r"\d{4}-\d{2}-\d{2}", file_name)

    if not match:
        return None

    return match.group(0)

#获取文件属性
def get_file_metadata(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    stat = file_path.stat()

    return {
        "file_name": file_path.name,
        "file_size": stat.st_size,
        "file_created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(timespec="seconds"),
        "file_modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }

#按Markdown标题把一整篇文本切成多个大块。
def split_by_markdown_heading(text: str) -> list[list[str]]:
    blocks = []#用来保存最终切出来的多个块。

    current_lines = []

    for line in text.splitlines(keepends=True):
        #遇到“下一个标题”时，才把前一个标题块收起来。。
        if is_heading(line) and current_lines:#这个if从第二个标题出现才开始触发
            blocks.append(current_lines)
            current_lines = []

        current_lines.append(line)
   # 循环结束后，最后一块还没被放进blocks，所以这里补一次。
    if current_lines:
        blocks.append(current_lines)

    return blocks

#如果某个大块太长，再继续切小块
def split_long_block(
    lines: list[str],
    max_chars: int,
    overlap_lines: int,
) -> list[list[str]]:
    chunks = []
    current_lines = []
    current_chars = 0

    for line in lines:
        line_chars = len(line)

        if current_lines and current_chars + line_chars > max_chars:
            chunks.append(current_lines)# 先把旧chunk保存
            current_lines = current_lines[-overlap_lines:] if overlap_lines > 0 else []## overlap留几行当下一块的开头
            current_chars = sum(len(item) for item in current_lines)

        current_lines.append(line)
        current_chars += line_chars

    if current_lines:
        chunks.append(current_lines)

    return chunks


def chunk_markdown(
    path: str | Path,
    content: str,
    max_chars: int = 1500,
    overlap_lines: int = 2,
) -> list[dict[str, Any]]:
    source_path = str(path)
    file_metadata = get_file_metadata(source_path)
    content_date = extract_date_from_path(source_path)

    heading_blocks = split_by_markdown_heading(content)
    chunks = []
    chunk_number = 1

    for block in heading_blocks:
        block_chunks = split_long_block(
            lines=block,
            max_chars=max_chars,
            overlap_lines=overlap_lines,
        )

        for block_chunk in block_chunks:
            chunk_content = "".join(block_chunk).strip()

            if not chunk_content:
                continue

            heading = get_heading(block_chunk)

            chunks.append(
                {
                    "path": source_path,
                    "chunk_id": f"{Path(source_path).name}::chunk-{chunk_number}",
                    "heading": heading,
                    "content": chunk_content,
                    "metadata": {
                        **file_metadata,
                        "content_date": content_date,
                    },
                }
            )

            chunk_number += 1

    return chunks