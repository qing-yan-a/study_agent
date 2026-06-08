# Agent 学习状态

这个文件用于在新窗口或上下文压缩后快速恢复学习进度。

## 当前阶段

当前处在 Agent 开发学习路线的第 12 阶段：

```text
第 11 阶段：RAG 检索优化，阶段性完成
第 12 阶段：RAG + Agent，已完成 v0.1 ~ v0.4 最小闭环，正在推进 v0.5
```

当前不是继续做通用资料整合，而是进入垂直场景 v0.5：

```text
复试资料 Agent 的状态管理 + 多 query 搜索计划 + 资料缺口判断
```

长期项目方向已更正为：

```text
Personal Research-to-Product Agent
个人资料商品生产助手
```

这是用户自己的个人生产型 Agent，不是面向客户端用户的产品。当前第一阶段产品方向收窄为：

```text
某某大学计算机研究生复试资料整合 Agent
```

用户决定学校、专业和年份。Agent 负责检索公开资料、优先找官方来源、辅助参考经验来源、筛选信息、整理结构、生成原创化 Markdown 文档草稿，最终由用户人工审核。

## 已完成学习内容

- OpenAI-compatible API 基础调用
- JSON Schema
- Tool / Function Calling
- 工具结果回传
- Agent Loop 基础版
- 本地文件工具基础版
- 写文件、追加写入、局部 patch 的基本思路
- Human confirmation 和安全边界意识
- run_command 白名单意识
- Tool Registry 基础概念
- Memory / Summary 基础概念
- 基础 RAG 闭环
- RAG 检索优化最小版
- RAG + Agent 工具接入基础版
- Agent 工具失败 fallback 策略
- web_search v0.1 公开资料候选来源发现
- source_review v0.2 候选来源初筛
- extract_selected_sources v0.3 已确认来源正文预览抽取
- draft_markdown v0.4 受约束 Markdown 草稿框架生成
- 工具调用预算控制最小版
- research_session 基础状态结构
- 多会话隔离与启动会话选择
- 多 query 搜索计划与 query 状态记录

## 当前 v0.5 已完成能力

### 1. Research Session 基础结构

当前 research_session 至少包含：

```json
{
  "research_goal": "...",
  "vertical": "postgraduate_reexam",
  "school": "...",
  "major": "...",
  "year": "...",
  "search_queries": [],
  "candidate_sources": [],
  "reviewed_sources": [],
  "selected_sources": [],
  "extracted_sources": [],
  "failed_sources": [],
  "open_gaps": [],
  "draft_ready": false
}
```

### 2. 多会话隔离

当前已经从单一全局状态升级为：

```text
memory/
  active_session.json
  sessions/<session_id>/
    research_session.json
    working-memory.md
    working-summary.md
```

启动 `minicodex/agent.py` 时会先进入终端版会话选择器。

### 3. 多 query 搜索计划

当前已具备：

- `plan_search_queries`
- `get_pending_search_queries`
- `update_search_query_status`

默认 query 类型顺序：

```text
past_questions
-> experience
-> official_verification
```

每条 query 会记录：

- `query_id`
- `query`
- `query_type`
- `status`
- `notes`

## 当前 v0.5 还没完成的部分

还没做完的不是“再加更多工具”，而是把已有状态真正用起来：

### 1. `open_gaps`

它表示：

```text
当前资料还缺哪些关键块
```

最小建议包括：

- 官方复试方案/招生简章缺失
- 专业目录/科目说明缺失
- 分数线/名单/录取线索缺失
- 流程类资料缺失
- 真题/机试/面试题线索缺失

### 2. `draft_ready`

它表示：

```text
当前资料是否已经足够进入 Markdown 草稿阶段
```

第一版不追求复杂打分，只做规则判断即可：

- 关键官方依据完全缺失 -> `false`
- 有官方依据 + 有流程或经验辅助 + 有至少一类题型线索 -> `true`
- 即便 `true`，也要保留风险提示和人工核验点

## 当前重要结论

### 1. 当前 RAG 仍是学习版

它的价值是理解：

- chunk 是怎么来的
- metadata 为什么重要
- dense 检索为什么会漏
- BM25 为什么能补
- hybrid score 怎么融合
- context 怎么交给 LLM

暂时不继续深入 ES、reranker、复杂权重调优和搜索算法工程。

### 2. 当前 v0.5 的重点是“状态显式化”

现在最值得学的不是更多提示词技巧，而是：

- Agent 如何记录自己做到哪一步
- 下一步该补什么资料
- 什么时候可以进入草稿

这正是后面 LangGraph、工作流图、持久执行会自然接上的地方。

## 当前已知问题

- 内存版索引不适合大规模文档。
- `rag_index.json` 不会自动检测文档变化；当前通过 `rebuild_memory_index` 工具或手动 rebuild 重建。
- 跨项目相关 chunk 可能进入 Top3。
- `search_file_content` 默认跳过 `sessions/`，避免运行日志污染日常代码搜索；明确 `path="sessions"` 时仍可排查日志。
- `web_search` v0.1 的第二次调用会被预算分支拒绝，但当前拒绝分支没有终端打印，因此终端可能出现空的 Agent Step。
- 当前 `open_gaps` 和 `draft_ready` 只是 research_session 里的字段，还没有专门的判断工具或判定函数。

## 更新后的教学大纲

后续教学继续以“垂直复试资料 Agent”为主线。

总路线：

```text
MiniCodex 基础 Agent
-> RAG + 工具系统
-> 垂直 Research Agent MVP
-> 问题路由与状态管理
-> RAG 检索优化
-> FastAPI 服务化
-> Python 工程与面试点
-> LangChain
-> LangGraph
-> Docker / 部署
-> 面试复盘
```

### 当前最近的具体任务

```text
v0.5.2：open_gaps + draft_ready
```

先把“资料缺口判断”和“草稿就绪判断”做成最小闭环，再考虑更细的问题路由或更复杂工作流。

## 已纳入后续教学路线的 RAG 进阶主题

用户希望后续系统学习以下 RAG 进阶能力，并结合 MiniCodex 项目逐步落地：

```text
1. Query Rewrite / Query Expansion
2. Rerank
3. MMR / 多样性检索
4. Parent-child retrieval
5. Graph RAG
6. 向量数据库 / Elasticsearch
```

建议学习顺序：

```text
Query Rewrite / Query Expansion
-> Rerank
-> MMR / 多样性检索
-> Parent-child retrieval
-> 向量数据库 / Elasticsearch
-> Graph RAG
```

当前不要立刻展开这些主题。先完成 Personal Research-to-Product Agent 的 v0.5：

```text
research_session
-> 多 query 搜索计划
-> open_gaps
-> draft_ready
```

## 用户协作偏好

- 用户希望学习，而不是 vibe coding。
- 除非用户明确说“你去改”“你直接改”“交给你”，否则优先给完整示例代码并指导用户自己修改。
- 用户希望一步一步推进，不要一次性塞大框架。
- 用户可以理解函数作用，但需要明确知道下一步该做什么、为什么做。
- 用户项目文件默认 UTF-8。
- Windows / PowerShell 读取中文文件时显式使用 UTF-8。

## Git 状态提示

最近一次已推送提交：

```text
2e5705d 内存版探索学习
```

当前工作区有未提交变更时，不要默认处理，除非用户明确要求。
