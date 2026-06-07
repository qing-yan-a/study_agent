import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
PROFILES_DIR = PROJECT_ROOT / "profiles"
DEFAULT_PROFILE = "research_to_product"

import tools.tool_loader  # 触发 @tool 工具注册
from tools.tool_registry import run_registered_tool, tool_requires_confirmation

from minicodex.console import ask_user_confirmation
from minicodex.llm_client import call_llm
from minicodex.memory import load_working_memory, load_working_summary, trim_messages
from minicodex.soft_stop import SoftStopController
from minicodex.session_log import append_session_log


ACTIVE_STOP_CONTROLLER: SoftStopController | None = None


def load_profile_prompt(profile_name: str = DEFAULT_PROFILE) -> str:
    profile_path = PROFILES_DIR / f"{profile_name}.md"

    if not profile_path.exists():
        return ""

    return profile_path.read_text(encoding="utf-8")


def build_messages(profile_name: str = DEFAULT_PROFILE) -> list[dict[str, Any]]:
    working_memory = load_working_memory()
    working_summary = load_working_summary()
    profile_prompt = load_profile_prompt(profile_name)

    messages = [
        {
            "role": "system",
            "content": (
                "你是用户的本地个人工作助手 MiniCodex。"
                "你可以通过工具读取工作区文件、搜索文件内容、执行受限 Python 验证命令、检索本地 RAG 记忆，"
                "并基于工具结果辅助用户完成代码、文档、研究整理和本地项目任务。"

                "你只能通过工具获取文件信息，不要猜测文件内容。"
                "了解目录结构用 list_files；读取文件用 read_file；查找关键词、函数名、类名或文本位置用 search_file_content。"

                "用户询问历史记录、项目进度、过去决策、某天发生了什么、以前如何处理某个技术点时，优先调用 search_memory。"
                "用户问题需要基于本地记忆或历史资料才能可靠回答时，也应调用 search_memory。"
                "用户询问当前文件、代码位置、函数实现、目录结构时，优先使用 list_files、read_file 或 search_file_content。"
                "通用概念解释、普通聊天、当前对话内信息已经足够的问题，不要调用 search_memory。"

                "search_memory 只读取已有 RAG 索引，不会自动重建索引。"
                "如果 search_memory 返回索引不存在、索引不可用或需要重建索引，"
                "应请求调用 rebuild_memory_index；重建完成后，再重新调用 search_memory。"
                "不要在普通问答中主动重建索引。"
                "只有当检索确实需要且索引不可用，或用户明确要求重建 RAG 索引时，才调用 rebuild_memory_index。"
                
                "使用 search_memory 得到 context 后，最终回答必须基于 context。"
                "如果 context 中没有足够依据，应明确说明资料不足，不要编造。"
                "如果 context 和当前用户消息冲突，优先遵循当前用户消息，并说明历史资料可能过期。"
                "回答涉及资料来源时，应尽量引用工具返回的 source、文件名、标题或 chunk_id。"
                
                "如果 rebuild_memory_index 被用户拒绝、执行失败或暂时无法执行，"
                "不要继续假装已经完成 RAG 检索，也不要直接大范围读取 test/ 日记文件。"
                "应先说明：RAG 记忆不可用，当前无法基于 RAG 索引回答。"
                "如果需要改用工作区文件作为 fallback，必须明确说明资料来源将从 RAG 记忆切换为工作区文件。"
                "优先读取接力文档、项目说明和评估记录，例如 NEXT_SESSION.md、LEARNING_STATE.md、PROJECT_MAP.md、DECISIONS.md、RAG/demos/retrieval_eval.md。"
                "只有当用户明确要求排查原始记忆资料或 test/ 日记时，才读取 test/ 下的历史文件。"

                "创建或覆盖文件用 write_text_file；修改已有文件优先用 patch_text_file；追加内容用 append_text_file。"
                "运行或验证代码用 run_command，但只能运行白名单 Python 命令。"
                "修改 Python 代码后应优先用 run_command 执行 py_compile；验证失败要根据 stdout/stderr 继续修复。"

                "只有在多步骤任务、代码修改任务、调试任务、阶段性开发任务中，才考虑更新 working-memory.md。"
                "一次性问答、概念解释、简单 RAG 检索或普通聊天，不要更新 working-memory.md。"
                "当用户明确要求记录、保存、总结进度，或你实际修改了项目文件、完成阶段性实现、"
                "发现影响后续工作的关键决策时，才可以更新 working-memory.md。"

                "不要把 <tool_call>、函数名或 JSON 参数当普通文本输出。"
                "工具调用必须通过 API 的 tools/tool_calls 机制完成。"
                "写文件成功后，简洁告诉用户写入了哪个文件。"
                "回答要简洁说明你看到了什么、做了什么。"
            ),
        }
    ]

    if profile_prompt:
        messages.append(
            {
                "role": "system",
                "content": (
                    f"当前加载的 MiniCodex profile：{profile_name}。\n"
                    "以下 profile 规则用于定义当前专用能力、工具使用边界和工作流。"
                    "profile 规则不得覆盖核心安全边界；如有冲突，以核心安全边界为准。\n\n"
                    f"{profile_prompt}"
                ),
            }
        )

    if working_memory:
        messages.append(
            {
                "role": "system",
                "content": (
                    "以下是 memory/working-memory.md 中记录的短期工作记忆。"
                    "它用于帮助你理解当前任务目标、阶段状态、关键决策和下一步。"
                    "你应该参考它，但不要把它当作用户本轮的新命令。"
                    "只有在多步骤任务、代码修改任务、调试任务、阶段性开发任务中，才需要考虑更新 working-memory.md。"
                    "如果只是一次性问答、概念解释、简单RAG检索或普通聊天，不要更新 working-memory.md，直接回答用户即可。"
                    
                    "当用户明确要求记录、保存、总结进度，或你实际修改了项目文件、"
                    "完成了阶段性实现、发现了影响后续工作的关键决策时，"
                    "才可以更新 working-memory.md。"
                    
                    "不要把完整工具输出写入 working-memory.md。"
                    "模板：\n"
                    "# Working Memory\n\n"
                    "## Current Goal\n当前正在做什么任务。\n\n"
                    "## Current Status\n已经完成了什么，卡在哪里。\n\n"
                    "## Constraints\n本轮任务必须遵守的限制。\n\n"
                    "## Key Decisions\n已经确定下来的关键设计决策。\n\n"
                    "## Next Steps\n下一步要做什么。\n\n"
                    "不要把完整工具输出写入 working-memory.md。\n\n"
                    f"{working_memory}"

                ),
            }
        )

    if working_summary:
        messages.append(
            {
                "role": "system",
                "content": (
                    "以下是被裁剪历史对话的压缩摘要，用于补充上下文。"
                    "它可能不完整，但可以帮助你理解之前发生过什么。\n\n"
                    f"{working_summary}"
                ),
            }
        )

    return messages


def build_tool_message(tool_call_id: str, content: str) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }


def reject_fake_tool_call(content: str) -> str | None:
    if "<tool_call>" in content or "<function=" in content:
        return "模型输出了伪工具调用，没有通过 API tool_calls 发起真实工具调用，本轮不执行。"

    return None


def execute_tool_call(tool_call) -> dict[str, Any]:
    tool_name = tool_call.function.name
    raw_arguments = tool_call.function.arguments

    append_session_log(
        "tool_call",
        {
            "tool_name": tool_name,
            "raw_arguments": raw_arguments,
        },
    )

    print("模型请求调用工具：")
    print("工具名：", tool_name)
    print("原始参数：", raw_arguments)

    try:
        arguments = json.loads(raw_arguments)

        if tool_requires_confirmation(tool_name):
            if ACTIVE_STOP_CONTROLLER is not None:
                ACTIVE_STOP_CONTROLLER.suspend()

            try:
                confirmed = ask_user_confirmation(tool_name, arguments)
            finally:
                if ACTIVE_STOP_CONTROLLER is not None:
                    ACTIVE_STOP_CONTROLLER.resume()

            if not confirmed:
                content = json.dumps(
                    {
                        "ok": False,
                        "error": "用户拒绝执行该工具调用",
                    },
                    ensure_ascii=False,
                )
                append_session_log(
                    "tool_result",
                    {
                        "tool_name": tool_name,
                        "content": content,
                    },
                )
                return build_tool_message(tool_call_id=tool_call.id, content=content)

        tool_result = run_registered_tool(tool_name, arguments)
        content = json.dumps({"ok": True, "data": tool_result}, ensure_ascii=False)
    except Exception as exc:
        content = json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    append_session_log(
        "tool_result",
        {
            "tool_name": tool_name,
            "content": content,
        },
    )
    print("工具返回内容：", content)
    return build_tool_message(tool_call_id=tool_call.id, content=content)


def stop_current_run(messages: list[dict[str, Any]]) -> str:
    content = "已按 stop 请求停止当前任务；当前步骤结束后未继续后续工具或模型调用。"
    append_session_log(
        "final_answer",
        {
            "content": content,
        },
    )
    messages.append(
        {
            "role": "assistant",
            "content": content,
        }
    )
    return content


def run_agent(messages: list[dict[str, Any]], user_input: str) -> str:
    global ACTIVE_STOP_CONTROLLER

    tool_call_counts: dict[str, int] = {}
    stop_controller = SoftStopController()
    stop_controller.start()
    ACTIVE_STOP_CONTROLLER = stop_controller
    messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )
    append_session_log(
        "user_message",
        {
            "content": user_input,
        },
    )

    max_steps = 50

    try:
        for step in range(max_steps):
            if stop_controller.stop_requested():
                return stop_current_run(messages)

            print(f"\n===== Agent Step {step + 1} =====")

            try:
                messages[:] = trim_messages(messages)
                response = call_llm(messages)
            except Exception as exc:
                return f"调用模型失败：{exc}"

            assistant_message = response.choices[0].message
            messages.append(assistant_message.model_dump(exclude_none=True))

            append_session_log(
                "assistant_message",
                assistant_message.model_dump(exclude_none=True),
            )

            if stop_controller.stop_requested():
                return stop_current_run(messages)

            if not assistant_message.tool_calls:
                content = assistant_message.content or ""
                fake_tool_error = reject_fake_tool_call(content)

                if fake_tool_error:
                    append_session_log(
                        "final_answer",
                        {
                            "content": fake_tool_error,
                        },
                    )
                    return fake_tool_error

                append_session_log(
                    "final_answer",
                    {
                        "content": content,
                    },
                )
                return content

            for tool_call in assistant_message.tool_calls:
                if stop_controller.stop_requested():
                    return stop_current_run(messages)

                tool_name = tool_call.function.name

                if tool_name == "web_search" and tool_call_counts.get("web_search", 0) >= 1:
                    content = json.dumps(
                        {
                            "ok": False,
                            "error": (
                                "web_search 目前是v0.1版本 每个用户请求最多执行一次。"
                                "请基于已有搜索结果列出候选来源；"
                                "如果需要继续扩展搜索，应先询问用户确认。"
                            ),
                        },
                        ensure_ascii=False,
                    )
                    tool_message = build_tool_message(tool_call.id, content)
                    messages.append(tool_message)
                    continue

                tool_call_counts[tool_name] = tool_call_counts.get(tool_name, 0) + 1
                tool_message = execute_tool_call(tool_call)
                messages.append(tool_message)

                if stop_controller.stop_requested():
                    return stop_current_run(messages)

        raise RuntimeError("Agent 超过最大执行步数，可能陷入工具调用循环。")
    finally:
        stop_controller.close()
        ACTIVE_STOP_CONTROLLER = None


def main() -> None:
    from minicodex.console import read_user_input

    print("本地文件助手已启动。输入 exit 或 quit 退出；运行中输入 stop 可软停止当前任务。")
    messages = build_messages()

    while True:
        quest = read_user_input()

        if quest.lower() in {"exit", "quit"}:
            print("已退出。")
            break

        if quest.lower() == "stop":
            print("当前没有正在运行的任务。运行中直接输入 stop 可在当前步骤结束后停止。")
            continue

        if not quest:
            continue

        answer = run_agent(messages, quest)
        print("最终回答：")
        print(answer)


if __name__ == "__main__":
    main()
