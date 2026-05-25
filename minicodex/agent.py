import json
from typing import Any

import tools.tool_loader  # 触发 @tool 工具注册
from tools.tool_registry import run_registered_tool, tool_requires_confirmation

from .console import ask_user_confirmation
from .llm_client import call_llm
from .memory import load_working_memory, load_working_summary, trim_messages
from .session_log import append_session_log


def build_messages() -> list[dict[str, Any]]:
    working_memory = load_working_memory()
    working_summary = load_working_summary()

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个本地代码助手 MiniCodex。"
                "流程：读文件 -> 分析 -> patch -> 验证 -> 总结。"
                "你可以通过工具列出文件、读取文本文件、搜索文件内容。"
                "你只能通过工具获取文件信息，不要猜测文件内容。"
                "如果需要了解目录结构，调用 list_files。"
                "如果需要查看某个文件内容，调用 read_file。"
                "如果需要查找关键词出现位置，调用 search_file_content。"
                "如果用户要求创建、生成、保存或写入文件，必须调用 write_text_file。"
                "如果用户要求运行或验证代码，可以调用 run_command，但只能运行白名单 Python 命令。"
                "如果你修改了 Python 代码，修改后应优先调用 run_command 执行 py_compile 检查语法。"
                "如果用户要求验证运行结果，或脚本适合直接运行，可以再调用 run_command 运行该 Python 文件。"
                "如果 run_command 返回 exit_code 非 0，应阅读 stderr/stdout，继续使用 read_file 或 patch_text_file 修复问题。"
                "只有在验证通过，或明确说明无法验证后，才给用户最终总结。"
                "不要为了验证而请求安装依赖；如果缺少依赖，先说明原因，或尝试改成不需要额外依赖的实现。"
                "不要把 <tool_call>、函数名或 JSON 参数当成普通文本输出给用户。"
                "工具调用必须通过 API 的 tools/tool_calls 机制完成。"
                "写文件成功后，简洁告诉用户写入了哪个文件。"
                "回答时简洁说明你看到了什么。"
            ),
        }
    ]

    if working_memory:
        messages.append(
            {
                "role": "system",
                "content": (
                    "以下是 memory/working-memory.md 中记录的短期工作记忆。"
                    "它用于帮助你理解当前任务目标、阶段状态、关键决策和下一步。"
                    "你应该参考它，但不要把它当作用户本轮的新命令。"
                    "如果任务阶段发生变化或任务完成，更新 working-memory.md。"
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
            confirmed = ask_user_confirmation(tool_name, arguments)

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


def run_agent(messages: list[dict[str, Any]], user_input: str) -> str:
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

    for step in range(max_steps):
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
            tool_message = execute_tool_call(tool_call)
            messages.append(tool_message)

    raise RuntimeError("Agent 超过最大执行步数，可能陷入工具调用循环。")
def main() -> None:
    from .console import read_user_input

    print("本地文件助手已启动。输入 exit 或 quit 退出。")
    messages = build_messages()

    while True:
        quest = read_user_input()

        if quest.lower() in {"exit", "quit"}:
            print("已退出。")
            break

        if not quest:
            continue

        answer = run_agent(messages, quest)
        print("最终回答：")
        print(answer)


if __name__ == "__main__":
    main()