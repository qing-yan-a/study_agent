import json
from datetime import datetime, timezone
from typing import Any

from .file_tools import WORKSPACE_ROOT
from .tool_registry import tool


# research_session 是某一次资料研究任务的业务状态，不是长期记忆。
# 当前 v0.5 先只维护一个单会话 JSON 文件，后续再考虑多 session。
SESSION_FILE = WORKSPACE_ROOT / "memory" / "research_session.json"

DEFAULT_SESSION: dict[str, Any] = {
    "research_goal": "",
    "vertical": "postgraduate_reexam",
    "school": "",
    "major": "",
    "year": "",
    "search_queries": [],
    "candidate_sources": [],
    "reviewed_sources": [],
    "selected_sources": [],
    "extracted_sources": [],
    "failed_sources": [],
    "open_gaps": [],
    "draft_ready": False,
    "notes": [],
}

LIST_FIELDS = {
    "search_queries",
    "candidate_sources",
    "reviewed_sources",
    "selected_sources",
    "extracted_sources",
    "failed_sources",
    "open_gaps",
    "notes",
}

STRING_FIELDS = {
    "research_goal",
    "vertical",
    "school",
    "major",
    "year",
}

BOOL_FIELDS = {
    "draft_ready",
}

ALLOWED_FIELDS = STRING_FIELDS | LIST_FIELDS | BOOL_FIELDS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_session() -> dict[str, Any]:
    # 用 JSON 深拷贝，避免列表字段在多次调用之间共享引用。
    return json.loads(json.dumps(DEFAULT_SESSION, ensure_ascii=False))


def load_session() -> dict[str, Any]:
    if not SESSION_FILE.exists():
        return default_session()

    return json.loads(SESSION_FILE.read_text(encoding="utf-8"))


def save_session(session: dict[str, Any]) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(
        json.dumps(session, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def validate_updates(updates: dict[str, Any]) -> None:
    if not isinstance(updates, dict) or not updates:
        raise ValueError("updates 必须是非空对象")

    unknown_fields = set(updates) - ALLOWED_FIELDS
    if unknown_fields:
        raise ValueError(f"不允许更新未知字段：{sorted(unknown_fields)}")

    for field in STRING_FIELDS & updates.keys():
        if not isinstance(updates[field], str):
            raise ValueError(f"{field} 必须是字符串")

    for field in LIST_FIELDS & updates.keys():
        if not isinstance(updates[field], list):
            raise ValueError(f"{field} 必须是列表")

    for field in BOOL_FIELDS & updates.keys():
        if not isinstance(updates[field], bool):
            raise ValueError(f"{field} 必须是布尔值")


@tool(
    name="get_research_session",
    description=(
        "读取当前复试资料 research_session 状态。"
        "用于查看当前研究任务的目标、搜索 query、候选来源、已筛选来源、已确认来源、已抽取来源、失败来源、资料缺口和 draft_ready。"
        "本工具只读取 memory/research_session.json，不搜索网页，不抽取正文，不生成草稿。"
    ),
    input_schema={
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    risk="low",
)
def get_research_session() -> dict[str, Any]:
    session = load_session()

    return {
        "path": "memory/research_session.json",
        "session": session,
    }


@tool(
    name="create_research_session",
    description=(
        "创建或重置当前复试资料 research_session。"
        "当用户开始一个新的学校/专业/年份复试资料整理任务时调用。"
        "本工具只写入 memory/research_session.json，不搜索网页，不抽取正文，不生成草稿。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "research_goal": {
                "type": "string",
                "description": "本次研究任务目标，例如：整理昆明理工大学计算机研究生复试资料。",
            },
            "school": {
                "type": "string",
                "description": "目标学校，例如：昆明理工大学。",
            },
            "major": {
                "type": "string",
                "description": "目标专业或方向，例如：计算机。",
            },
            "year": {
                "type": "string",
                "description": "目标年份；用户未说明时可用 latest。",
            },
            "vertical": {
                "type": "string",
                "description": "垂直场景。当前默认 postgraduate_reexam。",
            },
            "overwrite": {
                "type": "boolean",
                "description": "如果已存在非空 session，是否允许覆盖。默认 false。",
            },
        },
        "required": ["research_goal", "school", "major"],
        "additionalProperties": False,
    },
    risk="low",
)
def create_research_session(
    research_goal: str,
    school: str,
    major: str,
    year: str = "latest",
    vertical: str = "postgraduate_reexam",
    overwrite: bool = False,
) -> dict[str, Any]:
    if not isinstance(research_goal, str) or not research_goal.strip():
        raise ValueError("research_goal 必须是非空字符串")

    if not isinstance(school, str) or not school.strip():
        raise ValueError("school 必须是非空字符串")

    if not isinstance(major, str) or not major.strip():
        raise ValueError("major 必须是非空字符串")

    existing = load_session()
    has_existing_goal = bool(str(existing.get("research_goal", "")).strip())

    if has_existing_goal and not overwrite:
        raise ValueError("已存在 research_session；如需重置，请明确传 overwrite=true")

    now = utc_now()
    session = default_session()
    session.update(
        {
            "research_goal": research_goal.strip(),
            "vertical": vertical.strip() or "postgraduate_reexam",
            "school": school.strip(),
            "major": major.strip(),
            "year": year.strip() if isinstance(year, str) and year.strip() else "latest",
            "created_at": now,
            "updated_at": now,
        }
    )

    save_session(session)

    return {
        "path": "memory/research_session.json",
        "session": session,
    }


@tool(
    name="update_research_session",
    description=(
        "更新当前 research_session 的一个或多个字段。"
        "用于记录搜索计划、候选来源、初筛结果、用户确认来源、抽取成功来源、失败来源、资料缺口和 draft_ready。"
        "本工具只更新 memory/research_session.json，不搜索网页，不抽取正文，不生成草稿。"
        "调用前应尽量先读取已有 session，避免覆盖已有列表内容。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "updates": {
                "type": "object",
                "description": "要更新的字段。列表字段会整体替换，因此应传入合并后的完整列表。",
                "properties": {
                    "research_goal": {"type": "string"},
                    "vertical": {"type": "string"},
                    "school": {"type": "string"},
                    "major": {"type": "string"},
                    "year": {"type": "string"},
                    "search_queries": {"type": "array"},
                    "candidate_sources": {"type": "array"},
                    "reviewed_sources": {"type": "array"},
                    "selected_sources": {"type": "array"},
                    "extracted_sources": {"type": "array"},
                    "failed_sources": {"type": "array"},
                    "open_gaps": {"type": "array"},
                    "draft_ready": {"type": "boolean"},
                    "notes": {"type": "array"},
                },
                "additionalProperties": False,
            },
        },
        "required": ["updates"],
        "additionalProperties": False,
    },
    risk="low",
)
def update_research_session(updates: dict[str, Any]) -> dict[str, Any]:
    validate_updates(updates)

    session = load_session()
    session.update(updates)
    session["updated_at"] = utc_now()

    save_session(session)

    return {
        "path": "memory/research_session.json",
        "session": session,
    }
