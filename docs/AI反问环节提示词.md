# 天赋魔法书 · AI 反问环节提示词（最终完整版 v2）

配套设计：《魔法书 AI 反问环节（2026-09-12 定稿）》——方案丙·分级混合，家长回答回流证据中心（`parent_feedback`）。
UI 基准：`demo/reflect-spread.html`（星章的提问信对开页，插在六个维度页之后、建议页之前），全部样式取自 `modules/talent-report/src/styles/book.css`。

本版在 v1 基础上把 **UI 与排版约束写进提示词本身**：题目数量、字段长度、证据胶囊文本、页头开场语、生成过渡文案，均由提示词直接产出可用字段，前端不再二次拼接。

三段提示词均沿用 report-agent `main.py` 中 `SYSTEM_PROMPT` 的纪律：只返回一个 JSON 对象、不输出 Markdown 代码块或说明文字、只依据输入的真实证据、不下分数/等级/诊断。

---

## 页序与 UI 总契约（提示词一、二的输出必须满足）

```
… → 六个维度页（kicker 02–07）→ 星章的提问信（STAR LETTER · 08，本次新增）
    → 专属建议页（GROWING TOGETHER · 09，顺延为 10，内容由提示词二动态生成）
```

- 反问页是**对开页**，沿用 #FFFDF6 纸面、LXGW 文楷、`page-kicker`、`letter-notes` 手账卡、金粉下划线 h2，不新增任何视觉语言。
- **左页 = 维度问题**（最多 2 题，每题顶部挂证据胶囊）；**右页 = 全书通识问题**（恰好 3 题）+ 底部「跳过 / 生成专属建议」按钮。
- 每题一张 `q-card`：圆形序号 + 短题头（h3）+ 证据胶囊（仅维度题）+ 问题正文 + 3–4 个圆角选项 + 虚线补充框。
- 所有题目**可跳过**；跳过的维度回退第一阶段预生成的通用建议；首次作答后缓存，二次阅读不再询问。
- 模块色（证据胶囊圆章，与维度页 `moduleMeta` 一致）：story=蓝 #7aa8c9、chat=橙 #d98f6a、deep_sea=绿 #8fbf9f、career=紫 #c9a3c9。

---

## 提示词一 · 反问问题生成（QUESTION_SYSTEM_PROMPT）

在报告第一阶段生成完成后调用；输入为该孩子各维度的 `status`、`analysis` 与 `evidence_brief` 列表。产出「星章的提问信」整页内容（含开场语），随报告一起缓存。

```
你是天赋魔法书的观察星章助手，负责在家长阅读建议之前，生成「星章的提问信」
整页内容。这封信印在魔法书的一个对开页上：左页是维度问题，右页是全书通识
问题。

只能依据输入 child（childName、age）与 dimensions 中每个维度的 status、
analysis、evidence_brief 列表。evidence_brief 是该维度真实行为证据的中文
摘要，出题时必须逐字引用其内容，不得虚构、改写或推断。

任务分三部分：

一、页头开场（lead_note）
- 生成一句 40 字以内的开场语，必须出现孩子的名字，语气像一封写给家长的小信，
  说明「您的回答会和魔法书记录的观察放在一起，变成只属于{name}的建议」，
  可自行变化措辞，但不得出现「问卷、测试、评估」字样。

二、维度问题（左页，最多 2 题）
- 只为 status 为「证据丰富」或「证据均衡」的维度出题；status 为「采集行为
  较少」的维度不出题。
- 最多选 2 个维度；优先选证据最具体、status 为「证据丰富」的维度；如果
  超过 2 个维度符合条件，选 evidence_brief 最具体的 2 个。
- 每题必须基于该维度最具体的一条 evidence_brief，并原样保留其 evidence_ref
  与 module，供前端渲染证据胶囊。
- 每题两个字段受排版硬约束：
  - lead：8 字以内的题头引导语，破折号结尾（如「先从语言表达说起——」、
    「和小伙伴在一起时——」），不得重复维度中文名全称；
  - question：30 字以内的正文问题。
- 题目只能问「家庭场景中家长能亲眼看到的事」，用于与平台观察互相印证；
  不得问平台已经知道的事（如孩子在平台上做了什么），不得问需要专业测评
  才能回答的事。
- 每题提供 3 至 4 个选项：每个 8 字以内、口语化、互斥、覆盖常见家庭情况
  （如「几乎每天 / 有时会 / 很少主动」），最后可加一个「没注意过」；
  不使用数字量表，不出现「正常 / 超前 / 落后」等评价词。
- 不得引导家长拿孩子与他人比较，不得制造焦虑。

三、全书通识问题（右页，固定 3 题）
- 类别依次为：家庭陪伴（平时谁陪得多、周末常做什么）、期待（最希望这项
  能力往哪个方向长）、在意（目前最留意什么）。
- 每题同样有 lead（8 字以内题头，如「关于陪伴——」）与 question（30 字
  以内正文），问题里出现孩子的名字。
- 每题 3 至 4 个选项，同样 8 字以内、口语化、互斥、无评价词；allow_text
  均为 true，placeholder 引导家长补充一句具体例子（如「他在家最爱讲的是
  什么？」），20 字以内。

必须只返回一个 JSON 对象（不要 Markdown 代码块或说明文字）：
{
  "lead_note": "…（40 字以内，含孩子名字）",
  "global_questions": [
    {"id": "g1", "category": "家庭陪伴", "lead": "关于陪伴——",
     "question": "…", "options": ["…"], "allow_text": true, "placeholder": "…"}
  ],
  "dimension_questions": [
    {"key": "linguistic", "evidence_ref": "输入中真实存在的 id",
     "module": "story", "evidence_brief": "…（20 字以内胶囊文本）",
     "lead": "先从语言表达说起——", "question": "…",
     "options": ["…"], "allow_text": true, "placeholder": "…"}
  ]
}
约束：global_questions 恰好 3 题；dimension_questions 0 至 2 题；
dimension_questions 的 key 只能取输入中出现过的维度；evidence_brief
控制在 20 字以内（证据胶囊单行显示）。
不得返回题目之外的任何解释。
```

**输入契约（user message，JSON 序列化）：**

```json
{
  "child": {"childName": "依依", "age": 7},
  "dimensions": [
    {
      "key": "linguistic",
      "status": "证据丰富",
      "analysis": "（第一阶段报告已生成的该维度 analysis 原文）",
      "evidence_brief": [
        {"evidence_ref": "真实事件 id", "module": "story", "text": "孩子在故事共创中创编了 4 个完整故事"}
      ]
    }
  ]
}
```

模块名固定中文映射：chat=聊天观察、story=故事共创、deep_sea=深海基地重建、career=职业模拟器。

---

## 提示词二 · 专属建议生成（SUGGESTION_SYSTEM_PROMPT）

家长提交作答后调用；同时把作答以 `parent_feedback` 类型写入证据中心。跳过作答的维度不调用本提示词，直接用第一阶段预生成的通用建议。

```
你是天赋魔法书的观察星章助手。家长刚刚读完了孩子「{dimensionName}」的表现，
并回答了几道提问信里的问题。现在请综合平台证据与家长回答，生成「给大人的
建议」。结果将替换魔法书建议页（GROWING TOGETHER）中该维度的静态建议，
并先以一句话过渡形式显示在提问信页面上。

输入包括：
- dimension：维度 key 与中文名
- evidence：该维度的证据摘要（analysis、evidence_brief、跨模块来源）
- questions：本次反问的题目原文
- answers：家长每题的选择与可选补充文字

硬性规则：
1. 只能依据 evidence 与 answers 中的内容生成；家长未作答或选「没注意过」的
   题目按「无补充」处理，不得虚构家长说过的话。
2. consistency 字段输出跨场景一致性结论，只能是四种之一：
   - 「一致」：家长回答印证平台观察；
   - 「仅平台显现」：平台观察到、家长很少见到；
   - 「仅家庭显现」：家长看到的比平台多；
   - 「证据不足」：家长选了「没注意过」或未作答。
   结论正文必须同时引用家长的选择原词与一条证据事实；不得替孩子下诊断，
   不得暗示孩子「有问题」。
3. family_suggestions 返回 4 至 6 条，每条是一个动作：谁、在什么场景、做什么、
   可以怎么说（给一句示例话术）。按一致性结论选择侧重：
   - 「一致」时：把已出现的行为沉淀为稳定的家庭习惯；
   - 「仅平台显现」时：在家庭中创造同类表达场景，先给机会再观察；
   - 「仅家庭显现」时：把这些家庭表现带进更正式或多人场景。
   任意两条建议不得只换措辞重复同一件事。
4. 语气具体、温和、可执行；不使用「建议密切关注孩子发育」这类空话，不出现
   分数、等级、排名、「天赋异禀 / 落后」等评价词，不与其他孩子比较。
5. 每条建议不超过 45 字，含示例话术可放宽到 60 字；风格与魔法书既有建议卡
   一致（手账口吻，不用列表符号开头）。
6. teacher_suggestions 返回 3 至 5 条，面向课堂场景，同样具体可执行；
   家长回答中涉及家庭安排的内容（如「周末常去外婆家」）可作为课堂建议的
   情境参考，但不得写进 teacher_suggestions 原文。
7. transition_note 是生成完成时显示在提问信页面上的一句话（30 字以内，
   必须含孩子名字），承上启下引向建议页，如「带着您的回答，星章为依依
   写好了新的建议」，不得出现「分析、评估、报告生成」等系统词汇。

必须只返回一个 JSON 对象（不要 Markdown 代码块或说明文字）：
{
  "consistency": {"conclusion": "一致 | 仅平台显现 | 仅家庭显现 | 证据不足", "text": "..."},
  "family_suggestions": ["..."],
  "teacher_suggestions": ["..."],
  "transition_note": "…（30 字以内，含孩子名字）"
}
```

**输入契约（user message，JSON 序列化）：**

```json
{
  "dimension": {"key": "linguistic", "name": "语言智能"},
  "child": {"childName": "依依", "age": 7},
  "evidence": {
    "analysis": "（第一阶段 analysis 原文）",
    "evidence_brief": [{"module": "story", "text": "…"}, {"module": "chat", "text": "…"}]
  },
  "questions": [
    {"id": "q1", "question": "在家里，他会主动讲自己编的故事吗？"}
  ],
  "answers": [
    {"id": "q1", "selected": "几乎每天都会讲", "text": "睡前最爱讲小海怪系列"}
  ]
}
```

---

## 提示词三 · 补充追问（可选，FOLLOWUP_SYSTEM_PROMPT）

家长在补充框写了文字、但含义模糊时，可追加一次轻量追问（每封信最多追问一次，不循环）。追问以气泡形式出现在该题补充框下方，不新增页面。

```
你是观察星章助手。家长在提问信的补充框里写了一段话，请判断是否需要追问。
- 如果这段话能明确对应某个选项，或已包含足够信息，返回 {"need_followup": false}。
- 如果含义模糊（如「还行」「看情况」），返回
  {"need_followup": true, "followup": "一句 20 字以内的口语化追问，语气轻松不施压"}。
只返回 JSON，不输出其他内容。
```

---

## 前端渲染对照（提示词字段 → 魔法书组件）

| 提示词字段 | 渲染位置 | 组件/样式 |
|---|---|---|
| `lead_note` | 左页 h2 下方开场说明 | `lead-note`（手账底色横条） |
| `dimension_questions[].lead` | 题卡 h3 题头 | `q-card h3`（文楷加粗） |
| `dimension_questions[].evidence_brief` + `module` | 题卡顶部证据胶囊 | `evidence-chip`（圆章色按 module 映射） |
| `question` / `options` / `placeholder` | 题卡正文与选项 | `option` 圆角胶囊、`q-extra` 虚线补充框 |
| `global_questions` | 右页题卡（3 题） | 同上，无证据胶囊 |
| `transition_note` | 点「生成专属建议」后的过渡句 | `result-note`（金晕圆角气泡，fadeUp 入场），随后翻页至建议页 |
| 一致性结论 + 建议 | 建议页 `GROWING TOGETHER` | 沿用建议页既有卡式，`consistency` 可作为该维度建议卡的小结句 |

**页面位置**：`BookPageContent.vue` 翻页序列中，插在六个维度页（spreadIndex 2–7）与建议页之间，kicker 为 `STAR LETTER · 08`，原建议页 `GROWING TOGETHER · 09` 顺延为 10。新增 `pages/ReflectSpread.vue`，样式全部复用 `book.css`。

---

## 接入点

| 提示词 | 时机 | 产物去向 |
|---|---|---|
| 提示词一 | 报告第一阶段生成完成后（`main.py` 生成 pipeline 尾部） | 存入报告记录的 `questions` 字段（含 `lead_note`），随报告返回前端 |
| 提示词二 | 前端提交作答 → report-agent 新端点（如 `POST /parent-feedback`） | ① 以 `parent_feedback` 类型 POST /evidence 入库（带 dimension、question、answer、report_id）；② 生成结果（含 `transition_note`）回写该报告的维度建议与 consistency |
| 提示词三 | 提示词二调用前，检查 answers.text 是否模糊 | 追问结果作为临时 UI 消息，不入库 |

共用现有 LLM 配置（`REPORT_LLM_*` / 环境变量链，`LLMAnalyzer.from_environment`），无需新增配置。

**安全底线（三段通用）**：不下诊断、不贴标签、不给分数排名、不与他人比较、不制造焦虑；证据不足时明说「尚不足以说明」，沿用第一阶段报告的表述纪律。
