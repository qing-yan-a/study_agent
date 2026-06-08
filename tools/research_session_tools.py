import json
from datetime import datetime, timezone
from typing import Any

from minicodex.session_manager import (
    default_research_session as default_research_session_data,
    get_active_research_session_path,
    require_active_session_id,
)
from .tool_registry import tool


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

ALLOWED_QUERY_TYPES = {
    "past_questions",
    "experience",
    "official_verification",
}

ALLOWED_QUERY_STATUS = {
    "pending",
    "done",
    "failed",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_session() -> dict[str, Any]:
    # 用 JSON 深拷贝，避免列表字段在多次调用之间共享引用。
    return json.loads(json.dumps(default_research_session_data(), ensure_ascii=False))


def load_session() -> dict[str, Any]:
    session_file = get_active_research_session_path()

    if not session_file.exists():
        return default_session()

    return json.loads(session_file.read_text(encoding="utf-8"))


def save_session(session: dict[str, Any]) -> None:
    session_file = get_active_research_session_path()
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(
        json.dumps(session, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def validate_search_query_item(item: dict[str, Any]) -> None:
    # search_queries 是后续多轮搜索计划的核心结构，必须在工具层拦脏数据。
    if not isinstance(item, dict):
        raise ValueError("search_queries 的每一项都必须是对象")

    query_id = str(item.get("query_id", "")).strip()
    query = str(item.get("query", "")).strip()
    query_type = str(item.get("query_type", "")).strip()
    status = str(item.get("status", "")).strip()
    notes = item.get("notes", "")

    if not query_id:
        raise ValueError("search_queries[].query_id 不能为空")

    if not query:
        raise ValueError("search_queries[].query 不能为空")

    if query_type not in ALLOWED_QUERY_TYPES:
        raise ValueError(f"不支持的 query_type: {query_type}")

    if status not in ALLOWED_QUERY_STATUS:
        raise ValueError(f"不支持的 status: {status}")

    if not isinstance(notes, str):
        raise ValueError("search_queries[].notes 必须是字符串")


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
        if field == "search_queries":
            for item in updates[field]:
                validate_search_query_item(item)

    for field in BOOL_FIELDS & updates.keys():
        if not isinstance(updates[field], bool):
            raise ValueError(f"{field} 必须是布尔值")


@tool(
    name="get_research_session",
    description=(
        "读取当前复试资料 research_session 状态。"
        "用于查看当前研究任务的目标、搜索 query、候选来源、已筛选来源、已确认来源、已抽取来源、失败来源、资料缺口和 draft_ready。"
        "本工具只读取当前 active session 目录下的 research_session.json，不搜索网页，不抽取正文，不生成草稿。"
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
    session_id = require_active_session_id()
    session = load_session()

    return {
        "path": f"memory/sessions/{session_id}/research_session.json",
        "session": session,
    }


@tool(
    name="create_research_session",
    description=(
        "创建或重置当前 active session 的 research_session。"
        "当用户开始一个新的学校/专业/年份复试资料整理任务时调用。"
        "本工具只写入当前 active session 目录下的 research_session.json，不搜索网页，不抽取正文，不生成草稿。"
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
    session_id = require_active_session_id()

    if not isinstance(research_goal, str) or not research_goal.strip():
        raise ValueError("research_goal 必须是非空字符串")

    if not isinstance(school, str) or not school.strip():
        raise ValueError("school 必须是非空字符串")

    if not isinstance(major, str) or not major.strip():
        raise ValueError("major 必须是非空字符串")

    existing = load_session()
    has_existing_goal = bool(str(existing.get("research_goal", "")).strip())
    same_identity = (
        str(existing.get("vertical", "")).strip() == (vertical.strip() or "postgraduate_reexam")
        and str(existing.get("school", "")).strip() == school.strip()
        and str(existing.get("major", "")).strip() == major.strip()
        and str(existing.get("year", "")).strip() == (year.strip() if isinstance(year, str) and year.strip() else "latest")
    )

    if has_existing_goal and not overwrite and not same_identity:
        raise ValueError("已存在 research_session；如需重置，请明确传 overwrite=true")

    if has_existing_goal and same_identity and not overwrite:
        existing["research_goal"] = research_goal.strip()
        existing["updated_at"] = utc_now()
        save_session(existing)
        return {
            "path": f"memory/sessions/{session_id}/research_session.json",
            "session": existing,
        }

    now = utc_now()
    session = default_session()
    session.update(
        {
            "session_id": existing.get("session_id", session_id),
            "title": existing.get("title", ""),
            "status": existing.get("status", "active"),
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
        "path": f"memory/sessions/{session_id}/research_session.json",
        "session": session,
    }


@tool(
    name="update_research_session",
    description=(
        "更新当前 research_session 的一个或多个字段。"
        "用于记录搜索计划、候选来源、初筛结果、用户确认来源、抽取成功来源、失败来源、资料缺口和 draft_ready。"
        "本工具只更新当前 active session 目录下的 research_session.json，不搜索网页，不抽取正文，不生成草稿。"
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
    session_id = require_active_session_id()
    validate_updates(updates)

    session = load_session()
    session.update(updates)
    session["updated_at"] = utc_now()

    save_session(session)

    return {
        "path": f"memory/sessions/{session_id}/research_session.json",
        "session": session,
    }
