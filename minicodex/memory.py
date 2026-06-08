from pathlib import Path
from typing import Any

from .llm_client import summarize_messages
from .session_manager import (
    get_active_working_memory_path,
    get_active_working_summary_path,
)
from .session_log import append_session_log


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = PROJECT_ROOT / "memory"

MAX_WORKING_MEMORY_CHARS = 3000
MAX_WORKING_SUMMARY_CHARS = 3000
MAX_MESSAGES = 20
KEEP_RECENT_MESSAGES = 12


def load_working_memory() -> str:
    """读取当前 active session 的 working-memory.md。"""
    try:
        working_memory_file = get_active_working_memory_path()
    except RuntimeError:
        return ""

    if not working_memory_file.exists():
        return ""

    return working_memory_file.read_text(
        encoding="utf-8",
        errors="replace",
    )[:MAX_WORKING_MEMORY_CHARS]


def load_working_summary() -> str:
    """读取当前 active session 的 working-summary.md。"""
    try:
        working_summary_file = get_active_working_summary_path()
    except RuntimeError:
        return ""

    if not working_summary_file.exists():
        return ""

    return working_summary_file.read_text(
        encoding="utf-8",
        errors="replace",
    )[:MAX_WORKING_SUMMARY_CHARS]


def save_working_summary(content: str) -> None:
    """覆盖写入当前 active session 的压缩摘要。"""
    working_summary_file = get_active_working_summary_path()
    working_summary_file.parent.mkdir(parents=True, exist_ok=True)

    working_summary_file.write_text(
        content[:MAX_WORKING_SUMMARY_CHARS],
        encoding="utf-8",
    )


def trim_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """裁剪对话历史，并在裁剪前用 LLM 压缩旧消息。"""
    if len(messages) <= MAX_MESSAGES:
        return messages

    system_messages: list[dict[str, Any]] = []
    index = 0

    while index < len(messages) and messages[index]["role"] == "system":
        system_messages.append(messages[index])
        index += 1

    conversation_messages = messages[index:]
    old_messages = conversation_messages[:-KEEP_RECENT_MESSAGES]
    recent = conversation_messages[-KEEP_RECENT_MESSAGES:]

    while recent and recent[0]["role"] == "tool":
        old_messages.append(recent.pop(0))

    if old_messages:
        try:
            old_summary = load_working_summary()
            new_summary = summarize_messages(old_summary, old_messages)
            save_working_summary(new_summary)
            append_session_log(
                "summary_updated",
                {
                    "pruned_messages": len(old_messages),
                    "summary_chars": len(new_summary),
                },
            )
        except Exception as exc:
            append_session_log(
                "summary_failed",
                {
                    "error": str(exc),
                    "pruned_messages": len(old_messages),
                },
            )

    return system_messages + recent
