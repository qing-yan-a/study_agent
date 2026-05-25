import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

import tools.tool_loader  # 触发 @tool 工具注册
from tools.tool_registry import get_openai_tools


SUMMARY_MODEL_MAX_TOKENS = 800


load_dotenv()

api_key = os.getenv("MIMO_API_KEY")
base_url = os.getenv("MIMO_BASE_URL")
model = os.getenv("MIMO_MODEL")

if not api_key:
    raise RuntimeError("缺少 MIMO_API_KEY，请先在 .env 中配置。")

client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0)


def call_llm(messages: list[dict[str, Any]], max_retries: int = 3):
    last_error = None

    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                tools=get_openai_tools(),
                tool_choice="auto",
                max_tokens=4000,
            )
        except Exception as exc:
            last_error = exc
            wait_seconds = attempt + 1

            print(f"调用模型失败，第 {attempt + 1}/{max_retries} 次：{exc}")

            if attempt < max_retries - 1:
                print(f"{wait_seconds} 秒后重试...")
                time.sleep(wait_seconds)

    raise RuntimeError(f"调用模型失败，已重试 {max_retries} 次：{last_error}")


def summarize_messages(old_summary: str, pruned_messages: list[dict[str, Any]]) -> str:
    summary_messages = [
        {
            "role": "system",
            "content": (
                "你是 MiniCodex 的上下文压缩器。"
                "你的任务是把旧摘要和即将被裁剪的对话压缩成新的 working-summary.md。"
                "只保留对后续任务有用的信息：用户目标、已完成事项、关键决策、文件路径、未解决问题。"
                "不要保留完整工具输出，不要保留无关寒暄。"
                "用中文 Markdown 输出，控制在 2000 字以内。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "old_summary": old_summary,
                    "pruned_messages": pruned_messages,
                },
                ensure_ascii=False,
            ),
        },
    ]

    response = client.chat.completions.create(
        model=model,
        messages=summary_messages,
        max_tokens=SUMMARY_MODEL_MAX_TOKENS,
    )

    return response.choices[0].message.content or ""
