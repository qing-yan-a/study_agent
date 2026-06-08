from typing import Any

from .research_session_tools import (
    ALLOWED_QUERY_STATUS,
    ALLOWED_QUERY_TYPES,
    load_session,
    save_session,
    utc_now,
    validate_search_query_item,
)
from .tool_registry import tool


QUERY_TYPE_ORDER = [
    "past_questions",
    "experience",
    "official_verification",
]


def make_query_item(
    query_id: str,
    query: str,
    query_type: str,
    status: str = "pending",
    notes: str = "",
) -> dict[str, str]:
    # 统一由一个 helper 生成 query item，避免不同工具写出不一致的结构。
    item = {
        "query_id": query_id.strip(),
        "query": query.strip(),
        "query_type": query_type.strip(),
        "status": status.strip(),
        "notes": notes,
    }
    validate_search_query_item(item)
    return item


def build_query_plan(school: str, major: str, year: str) -> list[dict[str, str]]:
    # year 为空或 latest 时，不把年份硬拼进每条 query，避免把召回范围卡得太死。
    prefix = f"{school.strip()} {major.strip()}".strip()
    year_text = year.strip()
    dated_prefix = f"{prefix} {year_text}".strip() if year_text and year_text != "latest" else prefix

    return [
        make_query_item(
            query_id="past_questions_1",
            query=f"{dated_prefix} 复试 真题 回忆",
            query_type="past_questions",
        ),
        make_query_item(
            query_id="past_questions_2",
            query=f"{dated_prefix} 复试 机试题",
            query_type="past_questions",
        ),
        make_query_item(
            query_id="past_questions_3",
            query=f"{dated_prefix} 复试 面试题",
            query_type="past_questions",
        ),
        make_query_item(
            query_id="experience_1",
            query=f"{dated_prefix} 复试经验",
            query_type="experience",
        ),
        make_query_item(
            query_id="experience_2",
            query=f"{dated_prefix} 上岸经验 复试",
            query_type="experience",
        ),
        make_query_item(
            query_id="experience_3",
            query=f"{dated_prefix} 复试 流程",
            query_type="experience",
        ),
        make_query_item(
            query_id="official_verification_1",
            query=f"{dated_prefix} 复试方案",
            query_type="official_verification",
        ),
        make_query_item(
            query_id="official_verification_2",
            query=f"{school.strip()} 研究生院 招生简章 {major.strip()}",
            query_type="official_verification",
        ),
        make_query_item(
            query_id="official_verification_3",
            query=f"{dated_prefix} 专业目录",
            query_type="official_verification",
        ),
    ]


def query_type_rank(query_type: str) -> int:
    try:
        return QUERY_TYPE_ORDER.index(query_type)
    except ValueError:
        return len(QUERY_TYPE_ORDER)


@tool(
    name="plan_search_queries",
    description=(
        "为复试资料整理任务生成多轮搜索计划，并写入当前 active research_session 的 search_queries。"
        "当用户开始某学校+某专业+某年份的复试资料研究任务时调用。"
        "本工具只生成结构化搜索计划，不搜索网页，不初筛来源，不抽取正文。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "school": {
                "type": "string",
                "description": "目标学校，例如：昆明理工大学。",
            },
            "major": {
                "type": "string",
                "description": "目标专业，例如：计算机。",
            },
            "year": {
                "type": "string",
                "description": "目标年份；不明确时可用 latest。",
            },
            "overwrite": {
                "type": "boolean",
                "description": "如果当前 session 已存在 search_queries，是否覆盖。默认 false。",
            },
        },
        "required": ["school", "major"],
        "additionalProperties": False,
    },
    risk="low",
)
def plan_search_queries(
    school: str,
    major: str,
    year: str = "latest",
    overwrite: bool = False,
) -> dict[str, Any]:
    if not isinstance(school, str) or not school.strip():
        raise ValueError("school 必须是非空字符串")

    if not isinstance(major, str) or not major.strip():
        raise ValueError("major 必须是非空字符串")

    if not isinstance(year, str):
        raise ValueError("year 必须是字符串")

    session = load_session()
    existing_queries = session.get("search_queries", [])

    if existing_queries and not overwrite:
        raise ValueError("当前 research_session 已存在 search_queries；如需重建，请明确传 overwrite=true")

    query_plan = build_query_plan(school, major, year or "latest")
    session["search_queries"] = query_plan
    session["updated_at"] = utc_now()
    save_session(session)

    return {
        "query_count": len(query_plan),
        "search_queries": query_plan,
        "message": "已生成多轮搜索计划，并写入当前 research_session。",
    }


@tool(
    name="get_pending_search_queries",
    description=(
        "读取当前 research_session 中尚未执行的 search_queries。"
        "用于决定下一步优先搜索哪些 query。"
        "默认优先顺序是 past_questions -> experience -> official_verification。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "最多返回多少条 pending query。默认 3。",
            },
            "query_type": {
                "type": "string",
                "description": "可选。只返回指定类型的 pending query。",
                "enum": ["past_questions", "experience", "official_verification"],
            },
        },
        "required": [],
        "additionalProperties": False,
    },
    risk="low",
)
def get_pending_search_queries(
    limit: int = 3,
    query_type: str | None = None,
) -> dict[str, Any]:
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit 必须是正整数")

    if query_type is not None and query_type not in ALLOWED_QUERY_TYPES:
        raise ValueError(f"不支持的 query_type: {query_type}")

    session = load_session()
    search_queries = session.get("search_queries", [])

    if not isinstance(search_queries, list):
        raise ValueError("当前 research_session.search_queries 结构无效")

    pending_queries = []
    for item in search_queries:
        validate_search_query_item(item)
        if item["status"] != "pending":
            continue
        if query_type is not None and item["query_type"] != query_type:
            continue
        pending_queries.append(item)

    pending_queries.sort(
        key=lambda item: (
            query_type_rank(item["query_type"]),
            item["query_id"],
        )
    )

    return {
        "pending_count": len(pending_queries),
        "results": pending_queries[:limit],
    }


@tool(
    name="update_search_query_status",
    description=(
        "更新当前 research_session 中某条 search query 的状态。"
        "用于在某轮搜索完成、失败或需要回退时，记录对应 query_id 的执行状态和备注。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query_id": {
                "type": "string",
                "description": "要更新的 query_id，例如：past_questions_1。",
            },
            "status": {
                "type": "string",
                "description": "新的状态。",
                "enum": ["pending", "done", "failed"],
            },
            "notes": {
                "type": "string",
                "description": "可选备注，例如：结果很多但大多是营销页。",
            },
        },
        "required": ["query_id", "status"],
        "additionalProperties": False,
    },
    risk="low",
)
def update_search_query_status(
    query_id: str,
    status: str,
    notes: str = "",
) -> dict[str, Any]:
    if not isinstance(query_id, str) or not query_id.strip():
        raise ValueError("query_id 必须是非空字符串")

    if status not in ALLOWED_QUERY_STATUS:
        raise ValueError(f"不支持的 status: {status}")

    if not isinstance(notes, str):
        raise ValueError("notes 必须是字符串")

    session = load_session()
    search_queries = session.get("search_queries", [])

    if not isinstance(search_queries, list):
        raise ValueError("当前 research_session.search_queries 结构无效")

    updated = False
    normalized_query_id = query_id.strip()
    for item in search_queries:
        validate_search_query_item(item)
        if item["query_id"] != normalized_query_id:
            continue
        item["status"] = status
        item["notes"] = notes
        updated = True
        break

    if not updated:
        raise ValueError(f"未找到 query_id={normalized_query_id} 对应的 search query")

    session["search_queries"] = search_queries
    session["updated_at"] = utc_now()
    save_session(session)

    return {
        "query_id": normalized_query_id,
        "status": status,
        "notes": notes,
        "message": "search query 状态已更新。",
    }
