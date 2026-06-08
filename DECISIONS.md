# 设计决策记录

这个文件记录已经做过的取舍，避免新窗口反复讨论旧问题。

## 1. 当前 RAG 先保持内存版

决策：

```text
暂时不用 Elasticsearch、向量数据库、LangChain 或 LlamaIndex。
```

原因：

- 当前阶段目标是学习 RAG 原理和 Agent 接入。
- 内存版更容易调试 chunk、metadata、dense、BM25、context。
- 现在数据量只有几十个 chunk，不需要生产级搜索服务。

后续触发条件：

- 文档数量上千或上万 chunk。
- 需要持久化增量更新。
- 需要复杂 metadata filter。
- 需要中文 analyzer、搜索服务、性能优化。

## 2. RAG 检索优化不继续深挖算法工程

决策：

```text
第 11 阶段阶段性收束，进入 RAG + Agent。
```

原因：

- 用户目标是 Agent 开发工程师，不是搜索算法工程师。
- BM25 权重调优、rerank、ES analyzer 等有价值，但不是当前主线。
- 当前已经理解 metadata filter、BM25、jieba、hybrid retrieval 的基本原理。

## 3. Metadata filter 当前支持 date 和 file_name

已完成：

- `metadata.content_date`
- `metadata.file_name`

尚未完成：

- `project`
- `source`
- `type`
- `priority`

当前优先级：

```text
date filter 优先于 file_name filter
```

这意味着 `2026-04-23.md` 这类 query 可能先触发日期过滤。

## 4. 暂时接受跨项目相关 chunk 混入

现象：

用户问：

```text
我最近做过哪些 RAG 检索优化
```

Top2 可能出现：

```text
2026-04-23.md::chunk-2  帮卿颜改 sqyy 智能检索
```

判断：

- 这不是当前阶段的 bug。
- 它说明检索能召回语义和关键词相关内容。
- 但它也暴露了未来 Agent 上下文污染风险。

后续处理：

- context 中明确标注来源。
- Agent 回答时优先当前项目相关 chunk。
- 引入 `project/source/type` metadata。
- 必要时引入 reranker。

## 5. Query rewrite 暂时不做

决策：

```text
当前只在 build_bm25_query_tokens 中保留扩展入口。
```

原因：

- 当前先用规则完成日期 normalization。
- 以后接入 Agent 后，再让 LLM 做 query rewrite、query expansion 或 intent routing。

当前扩展入口：

```python
build_bm25_query_tokens(query)
```

## 6. jieba 日志暂时不处理

现象：

第一次调用 jieba 时可能输出：

```text
Building prefix dict from the default dictionary ...
Loading model from cache ...
```

判断：

- 这是 jieba 初始化日志，不是报错。
- 用户表示暂时不用管。

## 7. 用户学习方式优先于直接代写

决策：

```text
除非用户明确要求，否则不要直接改代码。
```

默认方式：

- 解释原理。
- 给完整示例函数。
- 告诉用户放在哪个文件。
- 用户自己改。
- 再帮助 review。

例外：

- 用户明确说“你去改”“交给你”“直接建立”。
- 文档接力包、评估记录这类辅助资料可在用户要求下直接建立。

## 8. Git 提交策略

已提交并推送：

```text
2e5705d 内存版探索学习
```

提交内容：

- RAG 核心代码
- 当前主流程 demo
- hybrid 对比 demo
- retrieval_eval.md
- pyproject.toml 依赖

未提交内容不应默认处理：

- 接力包 Markdown 文件
- `tools/rag_tools.py`
- `minicodex/agent.py`
- `RAG/data/`
- 早期 demo 文件
- `test/` 测试资料

`minicodex/` 曾被误删，已通过 `git restore minicodex` 恢复。

## 9. RAG 工具拆成 search 和 rebuild

决策：

```text
search_memory 只读已有索引。
rebuild_memory_index 单独负责重建索引。
```

原因：

- 重建索引会调用 embedding API，有成本且可能较慢。
- 自动重建会让普通检索工具产生隐性副作用。
- Agent 工程上应区分低风险只读工具和有成本/有覆盖写入行为的工具。

当前工具边界：

```text
search_memory
- risk=low
- 不自动重建
- 索引不存在时提示调用 rebuild_memory_index

rebuild_memory_index
- risk=medium
- 调用 load_and_build_index(rebuild=True)
- 覆盖 RAG/data/rag_index.json
- 需要用户确认
```

## 10. MiniCodex 暂时支持直接运行 agent.py

决策：

```text
当前为了学习调试方便，允许直接运行 minicodex/agent.py。
```

做法：

- `minicodex/agent.py` 顶部加入项目根目录到 `sys.path`。
- `agent.py` 内部改用 `from minicodex.xxx import ...` 绝对导入。

原因：

- 用户希望在 IDE 中直接运行 `agent.py`，不想每次通过 package module 或 console script 调试。
- 当前是学习项目，调试便利性优先。

后续工程化时，可以再回到标准包运行方式：

```text
python -m minicodex.agent
minicodex
```

## 11. MiniCodex prompt 不混入 Codex 教学身份

决策：

```text
MiniCodex 的 system prompt 只描述 MiniCodex 自己的产品身份和工具行为。
不要把 Codex 教练的教学路线约束写进去。
```

原因：

- Codex 当前对话中的身份是 Agent 开发教师。
- MiniCodex 的身份是用户的本地个人工作助手。
- 如果把“不要学 LangChain / LangGraph / 不要做前端”这类教学节奏写进 MiniCodex，会污染产品角色。

MiniCodex prompt 应写：

- 本地个人工作助手。
- 能使用文件工具、命令验证工具、RAG 记忆工具。
- 需要历史依据时调用 `search_memory`。
- RAG context 不足时说明资料不足，不编造。
- 资料草稿生成时必须原创整理、保留来源、提示风险、等待人工审核。

MiniCodex prompt 不应写：

- “你是 Agent 开发学习助手”。
- “不要学习 LangChain / LangGraph”。
- “不要重开大框架”。
- 其他只属于 Codex 教学节奏的约束。

## 12. 长期项目方向更正

决策：

```text
长期项目方向是 Personal Research-to-Product Agent。
```

定位：

- 用户自己的个人资料商品生产助手。
- 不是面向客户端用户的学习包产品。
- 用户决定要研究什么方向。
- Agent 负责围绕指定方向检索公开资料或本地资料、筛选信息、整理结构、生成原创化 Markdown 文档草稿。
- 用户人工审核后再决定是否上架。

版权和安全边界：

- 公开资料不能直接复制售卖。
- 不搬运盗版课件、电子书、机构资料、别人笔记。
- 输出应是原创整理、结构化总结、学习计划、清单、模板或分析文档。
- 每份文档需要来源链接、风险提示和人工审核清单。
- 暂时不做自动上架，只做文档草稿生成。

## 13. web_search v0.1 只做候选来源发现

决策：

```text
先接入极窄版 web_search(query, max_results=5)，只返回公开网页候选来源。
```

原因：

- Personal Research-to-Product Agent 需要公开资料发现能力。
- 但当前阶段还没有 source_review、正文抽取、版权判断和草稿生成 workflow。
- 如果一接入搜索就让模型自由多轮搜索和总结，容易滑入“自动研究报告”，超出当前学习边界。

当前实现：

- 新增 `tools/web_search_tools.py`。
- 底层复用本机 Tavily CLI：`C:\Users\卿颜\.local\bin\tvly.exe`。
- 工具输出只保留 `title/url/snippet/source/score/retrieved_at`。
- `max_results` 默认 5，最大 10。

当前不做：

- `tvly extract`
- `tvly research`
- `tvly crawl`
- `tvly map`
- `--include-raw-content`
- 自动总结网页全文
- 自动写入长期记忆
- 自动生成资料包
- 自动上架

Agent 回答边界：

- 只能列出候选来源和简短匹配理由。
- 必须说明候选来源尚未人工核验。
- 如果需要继续搜索、筛选来源或生成草稿，应先询问用户是否进入下一步。

## 14. web_search 当前使用工具预算限制

决策：

```text
web_search v0.1 阶段，每个用户请求最多真正执行一次 web_search。
```

原因：

- Agent Loop 本身允许模型多轮工具调用，这是正确的基础结构。
- 但 v0.1 只验证“公开资料候选来源发现”，不希望模型自由改写 query 多次搜索并直接总结成方法论。
- prompt 限制不够稳定，因此加入代码层预算作为硬约束。

当前实现：

- 在 `run_agent()` 中为每次用户输入创建 `tool_call_counts`。
- 如果本轮已经执行过一次 `web_search`，第二次 `web_search` 请求会被预算分支拒绝。
- 拒绝信息作为 tool message 回传给模型，要求基于已有结果回答，或询问用户是否继续扩展搜索。

已观察到的现象：

- 终端可能出现一个空的 Agent Step。
- 原因是预算拒绝分支当前没有打印，也没有记录 `tool_result`。
- session 日志中能看到第二次 `assistant_message.tool_calls`，并能从下一轮模型 reasoning 看到它收到了“每个用户请求最多执行一次 web_search”的拒绝信息。

后续演化：

```text
v0.1: web_search_budget = 1
v0.2 source_review: 可考虑 web_search_budget = 2~3，但每次补搜要有明确目的
v0.4 research workflow: 用正式 workflow 控制多轮搜索、去重、初筛、用户确认
```

## 15. MiniCodex Core 与专用 Profile 分层

决策：

```text
保留 MiniCodex 作为通用 Agent 骨架，把 Personal Research-to-Product 的专用能力规则外置到 profile。
```

原因：

- MiniCodex v0.1 已经具备通用 Agent 底座：Agent Loop、Tool Registry、文件工具、命令白名单、human confirmation、memory、RAG、web_search 和工具预算。
- 如果继续把资料生产规则都写进 `agent.py`，会让通用 Agent core 被单一业务场景污染。
- 企业里更常见的形态是“通用 Agent 平台 + 专用 Agent 应用 / profile / workflow”，而不是一个完全写死的单体 Agent。

当前做法：

- `minicodex/agent.py` 保留通用规则和安全边界。
- 新增 `profiles/research_to_product.md` 存放资料生产助手的专用规则。
- `build_messages(profile_name="research_to_product")` 默认加载该 profile。
- profile 规则不得覆盖核心安全边界；如有冲突，以核心安全边界为准。

当前分层：

```text
MiniCodex Core:
- Agent Loop
- Tool Registry
- tool_calls 协议
- human confirmation
- risk 分级
- 文件读写边界
- 命令白名单
- memory / summary
- session log
- tool budget 机制
- RAG fallback 基础策略

Research-to-Product Profile:
- web_search v0.1 来源发现边界
- source_review v0.2 来源初筛边界
- 资料草稿版权 / 来源 / 人工审核边界
- MVP workflow 阶段限制
```

后续方向：

- 不要把新的资料生产规则继续堆回 `agent.py`。
- 优先放入 profile、专用工具或 workflow。
- 等 workflow 变复杂后，再考虑从 profile 迁移到显式 workflow state 或 LangGraph。

## 16. source_review v0.2 只做候选来源初筛

决策：

```text
source_review 只基于搜索结果可见字段做初筛，不读取网页全文。
```

原因：

- v0.2 的目标是让 `web_search` 返回的候选来源变得可控。
- 搜索摘要不能当成事实依据。
- Agent 容易误把候选来源当成已经读过全文，因此必须把判断边界写进工具 schema、profile 和 `review_note`。

当前实现：

- 新增 `tools/source_review_tools.py`。
- 输入：`research_goal` 和 `sources`。
- 输出保留 `source_index`，便于用户指定保留或丢弃哪个来源。
- 输出 `relevance`、`credibility_hint`、`risk_flags` 和 `next_action`。
- `review_note` 必须声明“仅基于标题、URL、摘要和来源域名判断”。

当前接受的局限：

- 风险判断是启发式规则，不是真实可信度结论。
- 不判断网页全文质量、发布时间、引用来源和版权风险。
- 后续这些问题交给 v0.3 正文抽取和人工审核处理。

## 17. extract_selected_sources v0.3 只抽取用户确认过的来源

决策：

```text
extract_selected_sources 只对用户明确确认且明确要求抽取正文的 URL 做正文预览抽取。
```

原因：

- “保留来源”和“读取正文”是两个不同授权动作。
- PDF 抽取风险更高，必须额外明确允许。
- 正文内容可能很长，必须控制单次抽取数量和返回长度。

当前实现：

- 新增 `tools/extract_selected_sources_tools.py`。
- 底层使用 Tavily CLI：`tvly extract URL --format markdown --json`。
- 单次最多 2 个 URL。
- 只允许 `http/https` URL。
- PDF 默认拒绝，除非 `allow_pdf=true`。
- 返回截断后的 `content_preview`、`content_chars` 和 `truncated`。

已验证行为：

```text
“我确认保留这个 PDF 来源”
-> 不调用工具，先询问是否允许抽取 PDF 正文。

“我明确允许抽取这个 PDF 正文，请抽取正文预览”
-> 调用 extract_selected_sources(..., allow_pdf=true)
```

输出边界：

- v0.3 抽取完成后允许给用户轻度概览，帮助判断是否进入 v0.4。
- 不生成研究报告、资料草稿、教程、方案或可售卖文档。
- 不自动写长期记忆。
- 不自动抽取未确认来源。

## 18. v0.4 draft_markdown 必须基于已确认且已抽取来源

决策：

```text
下一阶段 draft_markdown v0.4 不应直接基于 web_search 或 source_review 结果生成草稿。
```

原因：

- `web_search` 只是候选来源。
- `source_review` 只是初筛。
- 只有 `extract_selected_sources` 拿到的正文预览才适合进入草稿生成阶段。

v0.4 必须保留：

- 来源列表。
- URL。
- 风险提示。
- 人工审核清单。
- 哪些内容来自来源。
- 哪些内容是 Agent 的原创结构化整理。

v0.4 禁止：

- 复制长段原文。
- 声称内容已经人工审核。
- 自动上架。
- 基于未确认来源生成草稿。
- 把单个来源当作最终事实。

## 19. research_session 不是长期记忆，而是当前任务状态

决策：

```text
research_session 用来保存“这一次研究任务做到哪一步”，不是长期记忆库。
```

原因：

- 长期记忆回答的是“以前做过什么”“之前怎么决定的”。
- `research_session` 回答的是“这一次复试资料任务当前做到哪了”。
- 如果把两者混在一起，Agent 很容易把历史经验和当前任务状态污染到一起。

当前含义：

- `search_queries`：本次任务的搜索计划
- `selected_sources`：本次任务中用户确认保留的来源
- `extracted_sources`：本次任务里已经抽取过正文预览的来源
- `open_gaps`：本次任务还缺哪些关键资料块
- `draft_ready`：本次任务是否足够进入草稿阶段

## 20. 研究会话状态按 session 隔离

决策：

```text
research_session、working-memory、working-summary 都按研究会话隔离。
```

原因：

- 用户后续会同时维护不同学校、不同专业、不同年份的资料任务。
- 如果仍然共用全局状态，很容易把不同任务互相污染。
- 这也是后续工作流、状态图、持久执行的自然前置。

当前结构：

```text
memory/
  active_session.json
  sessions/<session_id>/
    research_session.json
    working-memory.md
    working-summary.md
```

保留全局共享的只有：

- 代码
- 工具
- profile
- 项目级文档
- `sessions/*.jsonl` 运行日志

## 21. v0.5 先做显式状态，不急着做完整状态机

决策：

```text
当前先用 research_session + 小工具把状态显式化，不急着上 LangGraph 或完整状态机。
```

原因：

- 用户当前更需要先吃透“状态字段为什么存在、怎么更新、怎么驱动下一步动作”。
- 如果现在直接切 LangGraph，容易学成“会搭图，不理解为什么需要这些状态”。
- 先把 `open_gaps` 和 `draft_ready` 做明白，后面再上图会非常顺。

当前最小落地顺序：

```text
research_session 字段
-> 多 query 搜索计划
-> query 执行状态
-> open_gaps
-> draft_ready
-> 再考虑更显式的 workflow / LangGraph
```
