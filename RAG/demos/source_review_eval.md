# source_review v0.2 测试记录

测试日期：2026-06-06

本轮目标：

- 验证 `source_review` 只基于 `title/url/snippet/source` 做候选来源初筛。
- 验证输出保留 `source_index`，便于追踪 web_search 返回的第几个来源。
- 验证 `review_note` 明确声明“仅基于标题、URL、摘要和来源域名判断”。
- 验证风险规则能区分无关来源、强营销承诺、商业变现导向、PDF、平台/服务商内容。

## 测试命令

```powershell
.\.venv\Scripts\python.exe -m py_compile tools\source_review_tools.py test_source_review.py
.\.venv\Scripts\python.exe test_source_review.py
```

## 测试样例

research_goal：

```text
适合个人做电子资料商品的选题方法
```

候选来源：

| source_index | 来源类型 | 预期 |
| --- | --- | --- |
| 0 | 数字商品攻略 | 高相关，但仍需人工核验 |
| 1 | 虚拟资料暴利玩法 | 识别强营销承诺风险 |
| 2 | TikTok 表单设置 | 低相关，丢弃 |
| 3 | 知识付费内容产品选题 | 中相关，需人工核验 |
| 4 | 知识付费市场 PDF 报告 | 中相关，识别 PDF 和可能过时风险 |
| 5 | 平台服务商的知识付费变现文章 | 中相关，识别商业变现导向和平台立场 |

## 实际结果

| source_index | relevance | credibility_hint | risk_flags | next_action |
| --- | --- | --- | --- | --- |
| 0 | high | medium | 需要人工核验 | needs_user_check |
| 1 | medium | medium | 强营销承诺风险；商业变现导向，需要人工核验 | needs_user_check |
| 2 | low | medium | 需要人工核验 | discard |
| 3 | medium | medium | 需要人工核验 | needs_user_check |
| 4 | medium | medium | PDF 来源，后续抽取前需要用户确认；报告可能过时，需要确认发布时间 | needs_user_check |
| 5 | medium | medium | 商业变现导向，需要人工核验；平台/服务商内容，可能带营销立场 | needs_user_check |

## 结论

v0.2 已经达到最小可用状态：

- 不把搜索结果直接当作可靠资料。
- 能把明显无关来源标为 `discard`。
- 能把强营销、平台立场、PDF、过时报告等风险显式暴露出来。
- 对非官方、未读全文的来源默认要求人工核验。

当前限制：

- 规则仍是启发式关键词判断，不代表真实可信度结论。
- 工具没有打开网页全文，因此不能判断原文质量、发布时间、引用来源和版权风险。
- 下一阶段 `v0.3 extract_selected_sources` 应只对用户确认过的 URL 做正文抽取。
