# AI 伯乐 ·「我的作品 / 成长足迹」数据与指标映射方案

> 历史资料（2026-08-30 起不再描述当前实现）：本文记录 V0 聚合方案与当时的问题审计。当前运行时只使用 V1 `artifacts`、`timeline`、`evidence-records` 与 `talents`；请以 [README](README.md)、[开发交接文档](docs/development-and-handover.md) 和 V1 OpenAPI 契约为准。

> 调研范围：平台首页与个人页、四个探索模块（chat / story / deep-sea / career）、统一账号与证据中心（platform-core）、前后端数据契约与现有测试。
>
> 文档版本：v1.1 · 代码核对日期：2026-08-26

## 1. 文档目标与结论

“我的作品”和“成长足迹”共用同一批探索事件，但承担不同任务，不能使用同一套统计口径：

- **我的作品**回答“哪一次最值得我回看”，按模块保留一枚高光；展示的是一次具体探索的标题、行为事实、可选摘录与入选原因。
- **成长足迹**回答“我在哪些大陆完成过多少次探索”，从注册日开始汇总首次完成、最近完成、完成次数和可获得的有效时长。
- 两页都只呈现孩子做过什么，不把行为换算成能力分数、百分比、排名或“适合/不适合”的结论。
- 当前统一证据只在任务完成点上报，所以现阶段准确口径应称为**完成次数、首次完成、最近完成**，不能称为页面访问次数或全部使用次数。
- 高光选择与足迹统计必须先把事件归并成“探索活动”，再计算页面指标。直接数事件会让深海一次通关被算成三次，也会让窗口截断后的首次日期和累计次数漂移。

推荐的数据链路是：

```text
模块完成事件
  → 按 account_id + module + activity_id 去重
  → 归并为一次探索活动（activity）
  → 我的作品：每模块选择 1 个高光
  → 成长足迹：注册起点 + 4 个模块完成小结
```

## 2. 页面职责与现有呈现位

### 2.1 我的作品

代码入口：`app/components/WorksPage.tsx`。

页面包含三层：

1. **高光册首页**：固定展示四个大陆奖章位，奖章下方使用 `metricValue`；没有高光的大陆显示“等待第一次探索”。
2. **模块分类页**：展示该模块当前的一枚高光，票根使用 `title`、`summary` 和 `metricLabel · metricValue`。
3. **作品详情页**：展示 `detail`、可选 `quote`、主指标和“为什么它会成为高光”，支持朗读与字号切换。

因此一条高光数据至少要回答四件事：

- 这是什么：`title`
- 孩子做了什么：`detail`
- 哪个事实最能代表这次探索：`metricLabel / metricValue`
- 为什么选中它：`summary`

`quote` 只用于保存必要、短小且可回看的孩子表达，不应上传完整聊天或完整故事。

### 2.2 成长足迹

代码入口：`app/components/GrowthTrailPage.tsx`。

页面固定按以下顺序展示五站：

1. 星光起点：账号注册日。
2. 想象之洲：故事共创完成小结。
3. 创造之洲：深海基地重建完成小结。
4. 未来之洲：职业日常完成小结。
5. 倾听之洲：聊天完成小结。

每个模块站点需要：

- 是否点亮：`unlocked`
- 最近完成日期：`occurredAt / lastUsedAt`
- 首次完成日期：`firstUsedAt`
- 完成次数：`usageCount`
- 累计有效时长：拼入 `metricValue`，无可靠时长时不显示
- 最近一次行为小结：`detail`

当前对话框只直接展示最近日期和 `detail`，`firstUsedAt` 虽已进入前端类型，却没有单独显示。后续实现应在详情中增加“第一次完成 / 最近一次完成”两行，避免已采集字段不可见。

## 3. 四个探索模块与可用数据

### 3.1 倾听之洲 · 聊天观察（chat）

主要体验包括文字/语音聊天、阶段化追问、会话结束总结、潜能画像、图文手账、历史对话与小发现收藏。

当前统一上报（本方案已补齐）：

- 事件：`narrative_evidence`
- 时机：一次非空聊天正常结束
- 活动标识：`context.activity_id = context.session_id`
- 行为事实：`turn_count`、`long_turn_count`、`total_child_chars`、`topic_source`
- 新增字段：`completed`、`duration_seconds`、`topic/title`、最长孩子表达的 60 字以内短摘录、`idempotency_key`

注意：`modules/chat/app.js` 中的 `durationSec` 是相邻回复之间的单轮间隔，并不是整次会话时长；本次实现由聊天页独立累计前台可见会话时间，并以 `duration_seconds` 上报。

### 3.2 想象之洲 · 故事共创（story）

主要体验包括年龄通道、角色和主题创建、最多 15 轮共创、孩子或导演写结局、故事画廊、儿童回顾、家长报告、朗读/注音/字号辅助。

当前统一上报（本方案已补齐）：

- 事件：`story_contribution`
- 时机：孩子提交自己的结尾，或导演生成并保存完整结局后
- 活动标识：`context.activity_id = story-{story_id}`，同时保留 `story_id / subject_id`
- 行为事实：`ending_length`、`turn_number`、`completed`
- 新增字段：`title`、`completion_mode`、`duration_seconds`、60 字以内结尾摘录、`idempotency_key`

事件仍不上传故事全文，也不以故事总字数比较作品。聚合层使用“共创轮次”和“自己写的结尾字数”；导演结局路径现在同样产生完成事件，不再漏记足迹。

### 3.3 创造之洲 · 深海基地重建（deep-sea）

主要体验包括珊瑚公寓生态配对、洋流电网空间规划、海洋议事厅冲突调解、跳关提示和最终报告。

当前统一上报（本方案已补齐）：

- 事件：`ecology_strategy`、`spatial_solution`、`mediation_response`
- 时机：三个关卡分别完成时各一次
- 已有事实：配对/检查/调整、管道/旋转/连通、对话轮次/和解区间等
- `context.level`：关卡事件为 1、2、3
- 三关统一使用 `context.activity_id = gameState.studentId`，分别上报 `duration_seconds` 和关卡级 `idempotency_key`
- 第三关完成后新增 `deep_sea_session_completed`，上报 3/3 完成、总时长、调整次数和整次活动幂等键

三个关卡组件计算的 `duration` 与 `gameState.studentId` 已写入统一事件。各关卡另外调用 `/api/assessment/submit-level`，但深海后端没有对应路由；这些请求仍不能视为统一持久化数据来源。

### 3.4 未来之洲 · 职业模拟器（career）

主要体验包括六类职业、情境选择与追问、职业日常多阶段任务、参与过程记录、报告/证书和安全事件处理。

当前统一上报（本方案已补齐）：

- 事件：`workday_process_summary`
- 时机：一次职业日常全部完成
- 已有事实：`completed_stages`、`stage_count`、`adjustment_count`、`retry_count`、`hint_count`、`interaction_count`
- 活动上下文：`career_id`、每次运行唯一的 `workday_run_id / activity_id`
- 行为事实：补充 `completed`、职业中文名、精确 `duration_seconds`
- 幂等规则：按本轮运行 ID 生成稳定 `idempotency_key`

去重键已从“职业 ID”改为“每次运行一个 activity_id，同一次提交使用固定 idempotency_key”。因此重复提交不会重复计数，再次开始同一职业则可形成新的完成活动。

## 4. 实施前聚合逻辑审计

聚合入口为 `GET /api/explorer/collection`，核心逻辑在 `modules/platform-core/explorer_collection.py`。

### 4.1 已有能力

| 能力 | 当前实现 |
|---|---|
| 模块分组 | story / deep_sea / career / chat 四组 |
| 我的作品 | 每个有事件的模块通过 `_highlight_rank` 选择一条事件 |
| 成长足迹 | 注册起点 + 四个固定模块站点；无事件的站点返回 `unlocked: false` |
| 时长识别 | 支持 `duration_seconds` 等五种键并可累计 |
| 前端契约 | 已支持 title / summary / detail / quote / metric / first / last / count |
| 数据降级 | 接口失败时两页显示明确标注的示例；作品完全无高光时也使用示例高光 |

### 4.2 已识别偏差（本次实现均已修正）

| 问题 | 当前结果 | 影响 |
|---|---|---|
| 聚合接口只取最近 80 条事件 | 老事件会滑出窗口 | 首次日期后移、累计次数变小，活跃模块还可能挤掉其他模块 |
| 足迹直接用事件条数 | deep-sea 一次完整通关产生 3 条 | 完成次数最高被放大 3 倍 |
| story 的 `ending_length` 不在 `_content_length` 支持键中 | 所有真实故事长度为 0 | 指标退化为“从 N 次故事中选出” |
| career 已上报字段不在现有排名/文案规则中 | 完成阶段与调整次数均未使用 | 指标退化为兜底文案 |
| 四模块都未上报可直接累计的总时长 | `DURATION_KEYS` 始终取不到值 | 足迹没有累计时长 |
| 真实事件不带标题和短摘录 | 使用模块通用标题，`quote` 为空 | “作品”缺少作品感和可回看内容 |
| 证据强弱定义不一致 | 首次做对可能反而不如“调整过”强 | `evidence_level` 不适合直接作为跨场景作品质量分 |
| ISO 时间以字符串排序 | 混用 `Z` 与带偏移时间时不保证时序正确 | 首次/最近和并列选择可能错误 |
| 有任意真实高光后不再混入示例 | 只完成一个模块时，其余三个奖章位为空 | 这是当前真实行为，应保持并明确提示，而非伪装四枚真实奖章 |
| 足迹接口总会返回注册和四个站点 | 无探索记录时也有 5 条 milestone | 正常联网时足迹不会进入整页示例，而会显示真实注册起点和四个未点亮站点 |

上述内容用于记录实施前基线。当前聚合已改为 activity 归并、模块内可解释排序、全量历史统计和真实时间比较，具体口径以第 5–7 节为准。

## 5. 统一指标模型

### 5.1 三层指标

| 层级 | 作用 | 示例 |
|---|---|---|
| 原始事件指标 | 模块在完成点上报的最小事实 | `turn_count`、`ending_length`、`completed_stages` |
| 探索活动指标 | 将同一次探索的一个或多个事件归并 | 一次深海活动完成 3/3 关、有效时长 28 分钟 |
| 页面展示指标 | 面向孩子的短句与解释 | “完成 3 个基地任务 · 调整 5 次” |

页面不应直接解释原始事件。统一聚合层先生成 activity，再派生作品和足迹字段。

### 5.2 每次探索的公共字段

| 字段 | 必需 | 口径 |
|---|---:|---|
| `module` | 是 | `chat / story / deep_sea / career` |
| `event_type` | 是 | 具体完成事件类型 |
| `occurred_at` | 是 | ISO 8601，服务端统一转 UTC 后排序 |
| `context.activity_id` | 是 | 一次探索运行的稳定 ID；同一深海三关使用同一个值 |
| `context.subject_id` | 建议 | 作品/任务 ID，如 story_id、career run ID |
| `raw_evidence.completed` | 是 | 是否到达该口径定义的完成点 |
| `raw_evidence.duration_seconds` | 建议 | 页面可见且有效交互期间的秒数，不含后台挂起 |
| `raw_evidence.completed_units` | 建议 | 已完成轮次/关卡/阶段数 |
| `raw_evidence.total_units` | 可选 | 有固定总量时填写 |
| `raw_evidence.title` | 建议 | 经过净化的作品/任务短标题，建议不超过 30 字 |
| `raw_evidence.child_words` | 可选 | 必要摘录，建议不超过 60 字，不上传全文 |
| `context.idempotency_key` | 是 | 同一次提交重试时保持不变，防止重复计数 |

`evidence_level` 继续服务于证据报告，可作为高光质量门槛或低优先级并列项；不能替代作品完成度，也不直接展示给孩子。

### 5.3 活动归并规则

1. 先按 `account_id + module + activity_id` 分组。
2. 同一个 `idempotency_key` 只保留一次；网络重试不能增加次数。
3. chat、story、career 的一个完成汇总事件通常就是一次 activity。
4. deep-sea 的三关事件先合并；只有收到整次完成事件，或明确拥有 1/2/3 三个关卡完成事件时，才计为一次“完整重建”。
5. `duration_seconds` 在同一 activity 内按事件性质处理：关卡分段时求和，重复汇总事件不重复相加。
6. 完成次数统计 activity 数，不统计 event 数。
7. 首次/最近时间基于全量 activity 计算，不从“最近 80 条”窗口推导。

## 6.「我的作品」映射指标

### 6.1 高光选择总规则

- 每个模块最多返回一枚真实高光，四个模块视觉权重相同。
- 先检查是否满足模块的完成条件，再按模块内排序键选择；不同模块之间不比较。
- 排序使用可解释的行为事实，采用字典序，不合成总分。
- 并列时依次参考 `evidence_level` 和最近完成时间；页面不显示证据等级。
- 不把“更快”作为儿童高光的核心条件。产品原则要求“不比较快慢”，而速度还会鼓励匆忙操作；时长只用于足迹回顾。
- 没有真实候选时返回空奖章位；只有整个作品列表为空或接口失败时，前端才展示明确标注的整套示例。

### 6.2 模块映射表

| 模块 | 高光定义 | 候选完成条件 | 模块内排序键（从高到低） | 主指标文案 | 入选原因模板 |
|---|---|---|---|---|---|
| 倾听之洲 | 表达最充分的一次对话 | `narrative_evidence` 且 `turn_count > 0` | `total_child_chars` → `long_turn_count` → `turn_count` → strong → 最近 | 表达记录 / `12 轮对话 · 5 次长表达` | “这次你围绕一个话题说得最充分，共表达了 N 字。” |
| 想象之洲 | 孩子参与最完整的一篇故事 | 故事完成，至少有一轮孩子输入；孩子结尾和导演结尾都可候选 | `turn_number` → `ending_length` → 是否自己写结尾 → strong → 最近 | 创作记录 / `8 轮共创 · 结尾 126 字`；导演结尾则为 `8 轮共创` | “这篇故事里，你连续参与了 N 轮，还自己写下了结尾。” |
| 创造之洲 | 完成最完整、过程最有调整的一次基地重建 | 同一 activity 完成 3/3 关；若产品允许部分作品，可降级为完成至少 1 关并明确标注 | `completed_levels` → `meaningful_adjustments` → `strong_event_count` → 最近 | 重建记录 / `完成 3 个任务 · 调整 5 次` | “这次你完成了三处基地任务，并根据检查结果调整了 N 次。” |
| 未来之洲 | 完成最完整、主动尝试最充分的一次职业日常 | `completed_stages = stage_count > 0` | 完成率 → `interaction_count` → `adjustment_count + retry_count` → strong → 最近 | 体验记录 / `完成 5/5 个阶段 · 主动尝试 18 次` | “这次你完成了全部职业阶段，还在过程中主动尝试了 N 次。” |

说明：

- `total_child_chars` 与 `ending_length` 都是字符数，儿童端统一写“字”，避免混用英文分词意义上的 word count。
- `meaningful_adjustments` 只计有明确任务结果的调整，不计空白点击和装饰性交互。
- “第一次做对”同样是完整作品，不应因调整次数为 0 被排除；调整只用于完整度相同后的并列比较。
- story 的目标文案应由“最长故事高光”调整为“完整创作高光”；deep-sea 应由“最快重建高光”调整为“完整重建高光”，与“不比较快慢”的产品原则一致。

### 6.3 页面字段映射

| 页面字段 | 生成规则 |
|---|---|
| `title` | 模块上报的净化标题；缺失时按主题/关卡/职业映射中文标题 |
| `detail` | 描述这一次具体做了什么，不解释能力，不复制 `summary` |
| `summary` | 使用对应模块的“入选原因模板”，必须能解释排序事实 |
| `quote` | `child_words`；没有必要摘录时为空，不生成伪引语 |
| `metricLabel` | 表达记录 / 创作记录 / 重建记录 / 体验记录 |
| `metricValue` | 最多两项事实，建议不超过 24 个汉字 |
| `occurredAt` | 该 activity 完成时间 |
| `usageCount` | 该模块累计完成 activity 数，不是原始事件数 |

## 7.「成长足迹」映射指标

### 7.1 指标定义

| 指标 | 计算口径 | 页面用途 |
|---|---|---|
| 注册时间 | 账号 `created_at` | 第 1 站“星光起点” |
| 是否点亮 | 模块完成 activity 数 `> 0` | 站点解锁状态、已点亮大陆数 |
| 首次完成 | `MIN(activity.completed_at)` | 详情中的“第一次完成” |
| 最近完成 | `MAX(activity.completed_at)` | 星路卡片日期、详情中的“最近完成” |
| 完成次数 | `COUNT(DISTINCT activity_id)` | `N 次探索` |
| 累计有效时长 | `SUM(activity.duration_seconds)`，仅累计可信非负值 | `累计 N 分钟`，缺失时整段省略 |
| 最近小结 | 最近 activity 的行为摘要 | 详情页小纸条 |

### 7.2 模块口径

| 站点 | 一次“完成探索”的定义 | 去重键 | 时长来源 | `metricValue` 示例 |
|---|---|---|---|---|
| 星光起点 | 创建统一账号 | `account_id` | 不统计 | `第一次出发` |
| 倾听之洲 | 一次非空聊天正常结束并产生 `narrative_evidence` | `session_id / activity_id` | 聊天页有效会话计时 | `8 次探索 · 累计 45分钟` |
| 想象之洲 | 一个故事进入 completed；无论结尾由孩子或导演完成 | `story_id / activity_id` | 各次可见创作区间累计 | `5 次探索 · 累计 1小时20分` |
| 创造之洲 | 同一轮游戏完成三关并进入结束仪式 | `gameState.studentId / activity_id` | 三关 `duration` 求和 | `2 次探索 · 累计 38分钟` |
| 未来之洲 | 一次职业日常完成全部阶段 | 新建 `workday_run_id / activity_id` | `activeMs` 转精确秒数 | `3 次探索 · 累计 52分钟` |

若业务希望统计“进入过但未完成”的使用，必须另建 `activity_started` / `activity_abandoned` 口径，并与完成次数分开展示；不能用完成证据反推访问次数。

### 7.3 时长显示规则

- `< 60 秒`：显示“不到 1 分钟”，不显示 0 分钟。
- `1–59 分钟`：显示“N 分钟”。
- `≥ 60 分钟`：显示“N 小时 M 分”，M 为 0 时省略。
- activity 没有可靠时长时，不以 0 补齐；模块总时长只汇总有值记录，并可内部保留 `duration_coverage = 有时长活动数 / 总活动数`。
- 当覆盖率不足 100% 时，儿童端可写“已记录时长 N 分钟”，不要写成完整累计时长。
- 页面隐藏、切到其他标签页或长时间无交互的时间不计入有效时长。

## 8. 各模块最小改造字段

| 模块 | 现有事件 | 必须补充 | 建议补充 |
|---|---|---|---|
| chat | `narrative_evidence` | `duration_seconds`（新增有效会话计时） | `title/topic`、最长孩子表达的安全短摘录、`idempotency_key` |
| story | `story_contribution` | 导演结局也上报完成；把 `story_id` 统一为 `activity_id`；聚合支持 `ending_length` | `title`、`completion_mode`、`duration_seconds`、短结尾摘录 |
| deep_sea | 三个关卡事件 | 三条事件都带 `activity_id = gameState.studentId` 和各关 `duration_seconds` | 结束仪式新增 `deep_sea_session_completed` 汇总事件 |
| career | `workday_process_summary` | 新建每次运行 ID；移除按职业 ID 的长期 sessionStorage 去重；上报精确 `duration_seconds` | `career_name`、稳定 `idempotency_key` |

建议的最小统一事件示例：

```json
{
  "module": "career",
  "event_type": "workday_process_summary",
  "occurred_at": "2026-08-26T03:20:00Z",
  "evidence_level": "strong",
  "intelligence_candidates": ["intrapersonal", "logical_mathematical"],
  "behavior_summary": "完成职业日常任务，并在过程中根据结果进行尝试和调整。",
  "raw_evidence": {
    "completed": true,
    "duration_seconds": 1260,
    "completed_stages": 5,
    "stage_count": 5,
    "adjustment_count": 3,
    "retry_count": 1,
    "interaction_count": 18,
    "title": "社区医生的一天"
  },
  "context": {
    "activity_id": "workday-uuid",
    "career_id": "doctor",
    "idempotency_key": "workday-uuid:completed"
  }
}
```

## 9. 聚合接口目标契约

在保持现有前端字段兼容的前提下，建议为可解释统计补充结构化字段，避免只能解析展示文案：

```json
{
  "module": "chat",
  "kind": "module_summary",
  "unlocked": true,
  "usage_count": 8,
  "first_used_at": "2026-08-03T09:10:00Z",
  "last_used_at": "2026-08-26T02:30:00Z",
  "duration_seconds": 2700,
  "duration_coverage": 0.75,
  "metric_label": "累计完成",
  "metric_value": "8 次探索 · 已记录时长 45分钟"
}
```

平台核心现已读取账号全量事件并在聚合层归并 activity，统一计算首次、最近、去重次数和有效时长；高光与足迹不再受原 `LIMIT 80` 窗口影响。数据量进一步增长后，可把同一口径下沉为 SQL 聚合或独立 activity 表。

## 10. 实施状态

| 层级 | 已完成内容 | 代码位置 |
|---|---|---|
| P0：统计真值 | activity 归并、全量历史、ISO 真实时间排序、深海/职涯运行 ID、服务端幂等去重 | `modules/platform-core/explorer_collection.py`、`modules/platform-core/main.py` |
| P1：真实高光 | 四模块分别按表达、创作、重建和职业参与事实排序并生成可解释文案 | `modules/platform-core/explorer_collection.py` |
| P2：时长与完成路径 | 四模块上报有效时长；导演结局与深海整次完成均上报；足迹展示首次/最近完成 | 四模块事件入口、`app/components/GrowthTrailPage.tsx` |
| P3：文案一致性 | 作品页移除“最快/最长/最好”的比较式表述；足迹统一为完成口径 | `app/lib/explorer-data.mjs`、两个页面组件 |

以下清单保留为变更追溯，当前均已落地。

### P0：修正统计真值

1. 足迹从“事件计数”改为“activity 去重计数”。
2. 移除聚合统计的最近 80 条限制，使用全量 SQL 或物化的 activity 汇总。
3. 时间统一解析为 UTC 后比较。
4. deep-sea 三关增加同一 activity_id；career 增加每次运行 ID。

### P1：让现有真实高光可读

1. story 聚合识别 `ending_length`，并把高光主指标改为“共创轮次 / 结尾字数”。
2. career 使用完成阶段、主动尝试和调整/重试生成排序与文案。
3. chat 增加长表达次数和总表达字数。
4. 按 story title、deep-sea level、career ID、chat topic 生成明确标题；无孩子原话时保持 `quote` 为空。

### P2：补齐时长和完成路径

1. 四模块上报有效 `duration_seconds`。
2. story 的导演结局路径也产生完成事件。
3. deep-sea 增加整次完成汇总事件。
4. 成长详情页实际展示首次完成与最近完成。

### P3：体验文案一致性

1. 将 story“最长故事”改为“完整创作”。
2. 将 deep-sea“最快重建”改为“完整重建”。
3. 将足迹中的“使用次数/最近使用”改为“完成次数/最近完成”，直到真正采集访问事件。

## 11. 验收标准

### 11.1 数据验收

- 同一事件重试两次，完成次数只增加 1。
- 一次深海三关产生 3 条关卡事件，足迹只增加 1 次完整探索。
- 同一职业完成两轮不同 workday_run，足迹增加 2；同一轮网络重试不重复。
- 账号产生超过 80 条事件后，首次完成日期和累计次数不变化。
- 混用 `Z` 与 `+08:00` 时间输入，首次/最近仍按真实时间排序。
- 没有可靠时长时不显示“累计 0 分钟”。

### 11.2 作品页验收

- 每个有候选的模块最多一枚真实高光；无候选模块显示等待状态。
- 高光主指标能由原始字段复算，`summary` 能解释为何入选。
- story 不再把 `ending_length` 为 0 的兜底文案当成“故事长度”。
- career 能展示完成阶段和主动尝试，不再退化为“从 N 次体验中选出”。
- 详情没有真实摘录时不生成引号内容；朗读文本不包含空字段。

### 11.3 足迹页验收

- 注册站始终使用统一账号真实 `created_at`。
- 四个模块固定存在，未完成模块明确未点亮。
- 首次完成、最近完成、完成次数与 activity 明细一致。
- 累计时长的覆盖范围可解释，页面不把部分时长伪装为全量。
- 接口失败显示明确示例；接口正常但无探索时显示真实注册起点和四个未点亮站点。

## 12. 指标边界

以下数据不进入“我的作品 / 成长足迹”的儿童指标：

- story 的 0–5 观察分、家长版百分制或成长加分。
- deep-sea 的 A–E 等级和综合加权分。
- career 的 16 维能力分、职业适配结论和安全事件内容。
- chat 的完整对话、AI 回复全文和详细画像分项。
- 普通页面浏览、装饰点击、鼠标轨迹、逐秒日志和无意义重复操作。

这些边界保证两个页面始终是“可回看的作品 + 可解释的完成历程”，而不是儿童排行榜或能力诊断面板。
