from typing import Any
from urllib.parse import urlparse

from .tool_registry import tool


# 官方/准官方域名线索：这类来源通常可以先给较高可信度线索，但仍不等于已核验事实。
OFFICIAL_DOMAIN_HINTS = {
    ".gov",
    ".edu",
    "docs.",
    "developer.",
    "support.",
    "help.",
}

# 社区内容线索：经验帖可能有价值，但观点主观、质量不稳定，所以可信度先标 unknown。
COMMUNITY_DOMAIN_HINTS = {
    "zhihu.com",
    "csdn.net",
    "reddit.com",
    "medium.com",
    "juejin.cn",
    "jianshu.com",
}

# 视频来源线索：v0.2 不抽取视频正文，只提示后续核验成本较高。
VIDEO_DOMAIN_HINTS = {
    "youtube.com",
    "bilibili.com",
}

# 平台/服务商线索：这类文章可能夹带产品立场或营销目的，需要单独打风险标签。
PLATFORM_VENDOR_DOMAIN_HINTS = {
    "ketangjie.com",
    "polyv.net",
    "ckjr001.com",
}

# 和“个人电子资料商品”最直接相关的产品词。
CORE_PRODUCT_KEYWORDS = {
    "电子资料",
    "数字商品",
    "数位商品",
    "虚拟资料",
    "资料包",
    "电子书",
    "数字产品",
    "虚拟产品",
}

# 和“选题方法”直接相关的方法论词。
METHOD_KEYWORDS = {
    "选题",
    "方法",
    "策划",
    "调研",
    "需求",
    "用户画像",
    "痛点",
    "商品类型",
}

# 更宽泛的市场词：命中这些词说明可能相关，但通常不如核心产品词精确。
BROAD_MARKET_KEYWORDS = {
    "知识付费",
    "内容产品",
    "数字内容",
    "付费产品",
    "课程",
}

# 强营销承诺词：这类词不代表内容一定无用，但必须提示高风险。
STRONG_MARKETING_KEYWORDS = {
    "暴利",
    "稳赚",
    "躺赚",
    "0成本",
    "三个月赚",
    "收益10万",
    "月入",
    "保姆级",
    "免费领取",
}

# 普通商业导向词：比强营销弱一些，但仍然需要人工确认是否有偏向。
COMMERCIAL_KEYWORDS = {
    "赚钱",
    "变现",
    "私域",
    "引流",
}


def contains_any(text: str, keywords: set[str]) -> bool:
    # 只要文本命中任意一个关键词，就认为这一类规则被触发。
    return any(keyword in text for keyword in keywords)


def get_domain(url: str, source: str = "") -> str:
    # web_search 已经给出 source 时优先使用；否则从 URL 里解析域名。
    if source:
        return source.lower()

    parsed = urlparse(url)
    return parsed.netloc.lower()


def judge_relevance(research_goal: str, title: str, snippet: str) -> str:
    # 相关性只基于候选来源自己的标题和摘要判断，避免被用户问题里的关键词“带偏”。
    source_text = f"{title}\n{snippet}".lower()

    has_core_product = contains_any(source_text, CORE_PRODUCT_KEYWORDS)
    has_method = contains_any(source_text, METHOD_KEYWORDS)
    has_broad_market = contains_any(source_text, BROAD_MARKET_KEYWORDS)

    # 同时命中核心产品词和方法词，说明来源既谈对象也谈方法，相关性最高。
    if has_core_product and has_method:
        return "high"

    # 只命中宽泛市场词和方法词，说明有参考价值，但不一定直指电子资料商品。
    if has_broad_market and has_method:
        return "medium"

    # 只命中产品或市场词，说明主题可能相关，但方法论信息不足。
    if has_core_product:
        return "medium"

    if has_broad_market:
        return "medium"

    return "low"


def judge_credibility_hint(domain: str) -> str:
    # 这里判断的是“可信度线索”，不是最终可信度；最终仍要靠人工或后续全文核验。
    if any(hint in domain for hint in OFFICIAL_DOMAIN_HINTS):
        return "high"

    if any(hint in domain for hint in COMMUNITY_DOMAIN_HINTS):
        return "unknown"

    if any(hint in domain for hint in VIDEO_DOMAIN_HINTS):
        return "unknown"

    return "medium"


def collect_risk_flags(title: str, snippet: str, domain: str, url: str) -> list[str]:
    # 风险标签只基于搜索结果的可见字段，不读取网页正文。
    text = f"{title}\n{snippet}".lower()
    risk_flags: list[str] = []

    if contains_any(text, STRONG_MARKETING_KEYWORDS):
        risk_flags.append("强营销承诺风险")

    if contains_any(text, COMMERCIAL_KEYWORDS):
        risk_flags.append("商业变现导向，需要人工核验")

    if any(hint in domain for hint in COMMUNITY_DOMAIN_HINTS):
        risk_flags.append("经验帖/社区内容，需要人工核验")

    if any(hint in domain for hint in VIDEO_DOMAIN_HINTS):
        risk_flags.append("视频/专栏内容，后续抽取和核验成本较高")

    if any(hint in domain for hint in PLATFORM_VENDOR_DOMAIN_HINTS):
        risk_flags.append("平台/服务商内容，可能带营销立场")

    if url.lower().endswith(".pdf") or ".pdf" in url.lower():
        risk_flags.append("PDF 来源，后续抽取前需要用户确认")

    if "报告" in text and "2026" not in text and "2025" not in text:
        risk_flags.append("报告可能过时，需要确认发布时间")

    # 没有命中特定风险时，也不能默认可靠，因为 v0.2 还没有读全文。
    if not risk_flags:
        risk_flags.append("需要人工核验")

    return risk_flags


def decide_next_action(
    relevance: str,
    credibility_hint: str,
    risk_flags: list[str],
) -> str:
    # 明显低相关的来源直接丢弃，减少后续人工核验负担。
    if relevance == "low":
        return "discard"

    # 强营销承诺不直接丢弃，但必须交给用户确认，避免误用夸大内容。
    if "强营销承诺风险" in risk_flags:
        return "needs_user_check"

    # 高可信度线索来源可以先保留；是否作为事实依据仍取决于后续核验。
    if credibility_hint == "high":
        return "keep"

    return "needs_user_check"


@tool(
    name="source_review",
    description=(
        "对 web_search 返回的候选来源做初筛。"
        "本工具只基于 title、url、snippet、source/domain 判断相关性、可信度线索和风险。"
        "不打开网页全文，不抽取正文，不生成草稿，不做最终事实判断。"
        "review_note 必须明确说明判断仅基于标题、URL、摘要和来源域名。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "research_goal": {
                "type": "string",
                "description": "用户本轮想研究的目标或选题，用来判断来源是否相关。",
            },
            "sources": {
                "type": "array",
                "description": "web_search 返回的候选来源列表。",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_index": {
                            "type": "integer",
                            "description": "来源在 web_search 结果中的序号，从 0 开始。",
                        },
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "snippet": {"type": "string"},
                        "source": {"type": "string"},
                        "score": {"type": "number"},
                        "retrieved_at": {"type": "string"},
                    },
                    "required": ["title", "url", "snippet", "source"],
                    "additionalProperties": True,
                },
            },
        },
        "required": ["research_goal", "sources"],
        "additionalProperties": False,
    },
    risk="low",
)
def source_review(
    research_goal: str,
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    # 工具入口做基础参数校验，避免模型传空目标或错误类型。
    if not isinstance(research_goal, str) or not research_goal.strip():
        raise ValueError("research_goal 必须是非空字符串")

    if not isinstance(sources, list):
        raise ValueError("sources 必须是列表")

    reviews = []

    # 对 web_search 返回的每个候选来源分别做相关性、可信度线索和风险判断。
    for index, item in enumerate(sources):
        title = str(item.get("title", ""))
        url = str(item.get("url", ""))
        snippet = str(item.get("snippet", ""))
        source = str(item.get("source", ""))

        source_index = item.get("source_index", index)
        domain = get_domain(url, source)

        # 四个小函数各管一件事，主函数只负责串联和组装结构化结果。
        relevance = judge_relevance(research_goal, title, snippet)
        credibility_hint = judge_credibility_hint(domain)
        risk_flags = collect_risk_flags(title, snippet, domain, url)
        next_action = decide_next_action(
            relevance=relevance,
            credibility_hint=credibility_hint,
            risk_flags=risk_flags,
        )

        # review_note 明确声明判断边界，防止 Agent 表现得像已经读过全文。
        review_note = (
            "仅基于标题、URL、摘要和来源域名判断："
            f"该来源相关性为 {relevance}，"
            f"可信度线索为 {credibility_hint}，"
            f"风险标签为 {'、'.join(risk_flags)}，"
            f"建议动作为 {next_action}。"
        )

        reviews.append(
            {
                # source_index 保留 web_search 原始序号，方便用户指定要保留或丢弃的来源。
                "source_index": source_index,
                "title": title,
                "url": url,
                "source": domain,
                "relevance": relevance,
                "credibility_hint": credibility_hint,
                "risk_flags": risk_flags,
                "review_note": review_note,
                "next_action": next_action,
            }
        )

    return {
        "research_goal": research_goal,
        "review_count": len(reviews),
        "reviews": reviews,
    }
