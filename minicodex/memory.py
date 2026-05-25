from pathlib import Path
from typing import Any

from .llm_client import summarize_messages
from .session_log import append_session_log


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = PROJECT_ROOT / "memory"
WORKING_MEMORY_FILE = MEMORY_DIR / "working-memory.md"
WORKING_SUMMARY_FILE = MEMORY_DIR / "working-summary.md"

MAX_WORKING_MEMORY_CHARS = 3000
MAX_WORKING_SUMMARY_CHARS = 3000
MAX_MESSAGES = 20
KEEP_RECENT_MESSAGES = 12


def load_working_memory() -> str:
    """读取根目录 memory/working-memory.md，作为本轮 Agent 的短期工作记忆。"""
    if not WORKING_MEMORY_FILE.exists():
        return ""

    return WORKING_MEMORY_FILE.read_text(
        encoding="utf-8",
        errors="replace",
    )[:MAX_WORKING_MEMORY_CHARS]


def load_working_summary() -> str:
    """读取被裁剪历史对话的压缩摘要。"""
    if not WORKING_SUMMARY_FILE.exists():
        return ""

    return WORKING_SUMMARY_FILE.read_text(
        encoding="utf-8",
        errors="replace",
    )[:MAX_WORKING_SUMMARY_CHARS]


def save_working_summary(content: str) -> None:
    """覆盖写入新的压缩摘要，避免 summary 文件无限增长。"""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    WORKING_SUMMARY_FILE.write_text(
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
