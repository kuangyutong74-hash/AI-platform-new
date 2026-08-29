# AI 伯乐模块化评测平台架构重构设计 v1.1

> 状态：已根据架构评审补强授权、版本、证据语义、状态机与质量门禁，等待项目负责人复审
>
> 日期：2026-08-29
>
> 范围：架构规划，不修改现有业务功能
> 适用规模：几十位学生、低并发、单机或局域网实验环境

## 1. 文档目的

本文档在保留现有功能的前提下，重新划分 AI 伯乐平台的系统边界、模块职责、数据所有权和扩展方式。重构目标不是把项目升级成复杂的企业级系统，而是让实验项目具备以下能力：

- 四个现有体验模块可以继续独立演化；
- 新模块可以通过注册和契约接入，而不是修改平台首页核心代码；
- 账号、探索会话、证据、作品索引和报告使用统一数据入口；
- 报告中的结论能够追溯到真实行为证据；
- 本地安装、启动、调试和数据迁移保持简单；
- React、Vue、原生 JavaScript 等不同技术栈可以在过渡期共存。

本文档也是后续实施计划、数据库迁移、模块接入和回归验收的基线。

## 2. 已确认的架构决策

| 编号 | 决策 | 原因 |
|---|---|---|
| ADR-01 | 采用“模块化单体核心 + 独立体验模块” | 兼顾清晰边界和现有功能保护，适合低并发实验项目 |
| ADR-02 | 不立即统一四个模块的前端技术栈 | 全量重写风险高，对当前研究目标贡献有限 |
| ADR-03 | Core API 是唯一跨模块数据入口 | 避免多个 Node/Python 进程直接读写同一数据库 |
| ADR-04 | 统一数据库继续使用 SQLite | 当前人数和并发量不需要 PostgreSQL 或分布式方案 |
| ADR-05 | 优先统一跨模块数据，模块内部数据渐进迁移 | 降低一次性迁移聊天、故事和职业任务数据的风险 |
| ADR-06 | 四个模块通过 Module SDK 和版本化契约接入 | 替换当前散落的固定端口、脚本注入和事件拼接 |
| ADR-07 | 报告从标准化证据生成，不直接读取模块内部数据库 | 保持报告可解释、可追溯并降低模块耦合 |
| ADR-08 | 不引入消息队列、容器编排或微服务治理 | 项目规模不需要这些基础设施 |
| ADR-09 | `sessionId` 仅是资源标识，不承担授权职责 | 防止模块伪造或越权操作其他探索会话 |
| ADR-10 | 模块授权使用一次性 launch code 换取短期不透明 token | 满足最小权限，同时避免引入 JWT/OAuth 复杂度 |
| ADR-11 | JSON Schema/OpenAPI 是跨语言契约的唯一事实来源 | TypeScript、Python 和原生 JavaScript 可共享同一语义 |
| ADR-12 | Construct Registry 和 Evidence Policy 均进行版本化 | 防止模块间构念命名和证据强度口径漂移 |
| ADR-13 | 数据库变更采用 Expand → Migrate → Contract | 避免代码、数据和旧 API 在同一版本破坏性切换 |

## 3. 当前架构基线

### 3.1 当前运行拓扑

当前一键启动配置包含 10 项本地服务：

| 服务 | 端口 | 技术 | 当前职责 |
|---|---:|---|---|
| 整合平台 | 4173 | Vinext、React、TypeScript | 登录页、探索星球、作品、足迹、报告入口 |
| 统一账号与证据中心 | 8020 | FastAPI、SQLite | 账号、Cookie 会话、证据事件、作品/足迹聚合 |
| 报告生成服务 | 8030 | FastAPI | 规则或 LLM 报告生成 |
| 聊天观察 | 3000 | Express、原生 HTML/JS | 对话、语音、手账、收藏、聊天分析 |
| 故事共创后端 | 8010 | FastAPI、SQLite | 故事、角色、观察、TTS、AI 服务 |
| 故事共创前端 | 5174 | React、Vite | 故事创建、游玩和作品展示 |
| 深海基地后端 | 8005 | FastAPI | 角色代理、评分和评估接口 |
| 深海基地前端 | 3001 | Vue、Vite | 三关游戏和关卡报告 |
| 职业模拟器 | 8000 | FastAPI、Jinja、原生 JS、SQLite | 职业情境、任务、记录和观察页 |
| 天赋报告 | 5175 | Vue、Vite | 报告书、雷达图和证据说明 |

平台通过 `app/config/modules.ts` 中的固定 URL 和端口打开四个模块。四个模块再加载 `http://localhost:8020/ai-bole-bridge.js`，通过全局 `window.AIBole` 获取账号和上报证据。

```mermaid
flowchart TB
    Portal[整合平台 4173]
    Core[账号与证据中心 8020]
    ReportAgent[报告服务 8030]
    ReportUI[天赋报告 5175]
    Chat[聊天观察 3000]
    StoryFE[故事前端 5174]
    StoryBE[故事后端 8010]
    SeaFE[深海前端 3001]
    SeaBE[深海后端 8005]
    Career[职业模拟器 8000]

    Portal -->|固定 URL 跳转| Chat
    Portal -->|固定 URL 跳转| StoryFE
    Portal -->|固定 URL 跳转| SeaFE
    Portal -->|固定 URL 跳转| Career
    Portal --> ReportUI
    StoryFE --> StoryBE
    SeaFE --> SeaBE
    Chat -.浏览器桥接脚本.-> Core
    StoryFE -.浏览器桥接脚本.-> Core
    SeaFE -.浏览器桥接脚本.-> Core
    Career -.浏览器桥接脚本.-> Core
    ReportUI --> Core
    ReportUI --> ReportAgent
```

### 3.2 当前数据分布

| 数据 | 当前存储 | 当前所有者 | 问题 |
|---|---|---|---|
| 账号和登录会话 | `ai_bole_core.db` | platform-core | 与模块内部身份并未形成正式契约 |
| 跨模块证据事件 | `ai_bole_core.db` | platform-core | 事件结构偏通用，缺少正式评测会话实体 |
| 聊天历史、手账、收藏 | JSON/JSONL 文件 | chat | 单机 guest 设计与统一账号存在语义差异 |
| 故事、角色、消息、观察 | `story_cocreate.db` | story | 数据与统一账号仅通过上报事件间接关联 |
| 深海关卡状态 | 前端状态和后端评分结果 | deep-sea | 完整运行记录主要依赖浏览器上报 |
| 职业任务和会话 | `career_sim.db` | career | 内部会话和平台会话不是同一模型 |
| 报告 | 页面请求时生成 | talent-report/report-agent | 缺少统一的已发布报告快照和版本记录 |
| 作品与成长足迹 | 从证据事件推导 | platform-core | 聚合器依赖各模块不同的原始字段约定 |

### 3.3 当前功能清单

下列功能全部属于重构保护范围。

#### 平台功能

- 登录、注册、退出和儿童昵称/年龄档案；
- 探索星球与四模块入口；
- 我的作品；
- 成长足迹；
- 天赋报告入口和阅读；
- 浏览器前进、后退和模块返回平台；
- 示例数据与真实数据明确区分；
- 桌面、平板、手机和减少动态偏好支持。

#### 聊天观察

- 儿童与 AI 伙伴自由对话；
- 对话状态机、回复校验、修复和降级；
- 潜能画像分析；
- 历史对话、手账、每日发现和收藏；
- Vosk 离线语音输入；
- 对话完成证据上报。

#### 故事共创

- 创建角色、主题和故事；
- SSE 故事共创流程；
- 儿童输入安全处理；
- 儿童或故事导演完成结局；
- 故事作品、书架、观察和 TTS；
- 故事完成证据上报。

#### 深海基地

- 珊瑚生态配对；
- 洋流电网空间建构；
- 海洋议事厅协调任务；
- 角色互动、音效、语音和关卡反馈；
- 分关证据和完整通关证据上报；
- 失败暂存和重新同步提示。

#### 职业体验

- 职业选择和职业情境；
- 工作日任务和多阶段交互；
- 重试、提示、调整等过程记录；
- 职业探索历史与观察页面；
- 完成过程证据和体验快照上报。

### 3.4 当前主要问题与根因

| 表象 | 根因 | 后果 |
|---|---|---|
| 四模块被固定展示在一个统一页面 | 平台把模块清单、启动方式和 UI 写死在同一层 | 新增或替换模块需要修改平台代码 |
| 页面能跳转但模块没有真正统一 | 集成依赖固定端口、全局脚本和 Cookie | 本地环境变化会产生连锁故障 |
| 作品和足迹聚合逻辑复杂 | 没有统一探索会话和作品契约 | 聚合器需要猜测各模块字段含义 |
| 报告结论与模块内部分析并存 | 领域边界没有统一 | 同一行为可能被多套规则重复解释 |
| 数据库和 JSON 文件分散 | 每个模块从独立项目演进而来 | 账号关联、备份、迁移和实验数据导出困难 |
| 10 个服务依赖启动顺序 | 前后端和报告页面均独立运行 | 单机演示和故障定位成本较高 |
| 模块技术栈不一致 | 历史实现差异 | 公共能力难复用，但并非当前首要风险 |

## 4. 目标架构

### 4.1 总体结构

![目标架构总览](../../architecture/assets/target-architecture-overview-v1.png)

目标系统分为四个清晰层次：

1. **Portal**：统一用户体验，不承担模块内部业务；
2. **Core API**：统一账号、模块目录、探索会话、证据、作品和报告；
3. **Module SDK + Contracts**：定义所有模块共同遵守的接入协议；
4. **Experience Modules**：保留独立业务体验和内部实现。

Core API 是统一 SQLite 的唯一所有者。体验模块不能直接读取其他模块的数据，也不能直接读写统一数据库。

### 4.2 目标目录

```text
AI-platform-new/
├─ apps/
│  ├─ portal/                       # 统一平台外壳
│  └─ core-api/                     # 唯一跨模块后端
│     ├─ accounts/
│     ├─ catalog/
│     ├─ sessions/
│     ├─ evidence/
│     ├─ artifacts/
│     ├─ reports/
│     └─ database/
├─ experiences/
│  ├─ listening/
│  ├─ storytelling/
│  ├─ deep-sea-building/
│  └─ career-exploration/
├─ packages/
│  ├─ module-sdk/
│  ├─ contracts/
│  ├─ design-tokens/
│  └─ test-contracts/
├─ config/modules/
├─ scripts/
├─ docs/
└─ tests/
```

该目录是目标结构，不要求在第一阶段一次性移动全部文件。迁移期间通过兼容适配器维护现有路径。

### 4.3 组件职责

#### Portal

负责：

- 登录、注册和退出界面；
- 当前儿童档案；
- 从模块目录渲染探索入口；
- 创建探索会话并启动模块；
- 作品、足迹和报告阅读；
- 模块故障、数据空状态和重试提示。

不负责：

- 模块内部关卡和对话状态；
- 判定证据强弱；
- 拼接报告结论；
- 保存跨模块数据；
- 硬编码模块端口。

#### Core API

负责：

- 账号凭据和儿童档案；
- 模块注册、版本和适龄信息；
- 探索会话生命周期；
- 证据校验、幂等保存和查询；
- 作品元数据和快照索引；
- 报告生成、版本和证据引用；
- SQLite 数据库迁移、备份和实验数据导出。

#### Experience Module

负责：

- 自己的儿童交互、业务状态和内容安全；
- 生成可解释的模块原始行为；
- 通过 SDK 上报证据和作品；
- 正确结束、中断或退出探索会话；
- 提供模块健康状态和版本信息。

不负责：

- 识别统一账号 Cookie；
- 直接生成跨模块天赋结论；
- 查询其他模块数据；
- 直接写统一 SQLite；
- 决定平台作品、足迹和报告布局。

#### Module SDK

负责：

- 接收平台传入的启动上下文；
- 封装证据、作品和会话 API；
- 统一超时、重试、离线暂存和幂等键；
- 提供返回平台方法；
- 屏蔽模块内部框架差异。

## 5. 模块注册与契约

### 5.1 契约事实来源

跨语言契约以仓库中的 JSON Schema 和 OpenAPI 文件为唯一事实来源：

```text
packages/contracts/
├─ openapi/core-api.v1.yaml
├─ schemas/module-manifest.v1.schema.json
├─ schemas/launch-context.v1.schema.json
├─ schemas/artifact.v1.schema.json
├─ schemas/construct-registry.v1.schema.json
├─ schemas/evidence-policy.v1.schema.json
└─ schemas/evidence/
   ├─ envelope.v1.schema.json
   ├─ deep-sea.spatial-task-completed.v1.schema.json
   ├─ story.contribution-completed.v1.schema.json
   └─ ...
```

TypeScript interface、Pydantic model、原生 JavaScript 校验器和契约测试均从这些 Schema 生成或映射，不能各自维护一套近似定义。

### 5.2 模块清单

平台不再维护固定的四模块数组。每个模块提供经过校验的清单：

```ts
interface ModuleManifest {
  id: string;
  version: string;
  name: string;
  description: string;
  entryUrl: string;
  healthUrl?: string;
  targetAge: { min: number; max: number };
  constructRegistryVersion: string;
  constructs: string[]; // 只能引用对应 Registry 中的 key
  supportedEventTypes: string[];
  capabilities: {
    resumable: boolean;
    producesArtifacts: boolean;
    requiresAI: boolean;
    supportsOfflineEvidence: boolean;
  };
}
```

当前四个模块以配置文件注册。配置由 Core API 读取，Portal 只消费 `/api/v1/modules` 返回的数据。

模块的稳定身份和具体发布版本分开保存。`moduleId` 表示长期稳定的模块，`moduleVersion` 表示不可修改的历史发布版本；已被探索会话引用的 manifest 不得覆盖。

### 5.3 启动授权与上下文

`sessionId` 只是资源标识，不是凭据。Portal 创建探索会话后，Core API 同时签发只能使用一次、默认 60 秒过期的 `launchCode`：

```mermaid
sequenceDiagram
    participant Portal
    participant Core as Core API
    participant Module as Experience Module

    Portal->>Core: 创建 assessment session（Cookie + CSRF）
    Core-->>Portal: sessionId + one-time launchCode
    Portal->>Module: LaunchContext(sessionId, launchCode)
    Module->>Core: POST /module-authorizations:exchange
    Core-->>Module: 短期不透明 moduleSessionToken
    Module->>Core: Bearer token + evidence/artifact/session API
```

```ts
interface LaunchContext {
  sessionId: string;
  moduleId: string;
  moduleVersion: string;
  launchCode: string;
  launchCodeExpiresAt: string;
  returnUrl: string;
  contractVersion: "1.0";
}
```

LaunchContext 不暴露 `accountId` 或 `childProfileId`。Core API 在服务端将 token 绑定到：

- `session_id`；
- `module_id` 和 `module_version`；
- 内部 `child_profile_id`；
- `evidence:write`、`artifact:write`、`session:complete`、`session:interrupt` scope；
- `expires_at`、唯一 `jti` 和 `contract_version`。

当前规模使用随机生成的不透明 token，数据库只保存 token 哈希。默认有效期为 2 小时，可在会话仍为 `active` 时由 SDK 刷新一次；完成、放弃、退出登录或管理员撤销会话时立即失效。不引入 JWT、OAuth 服务或公私钥体系。

### 5.4 Construct Registry

所有构念使用稳定、版本化的注册表，模块不得提交任意字符串：

```yaml
version: "1.0"
constructs:
  - key: creativity.narrative_expression
    displayName: 叙事表达
    reportDimension: linguistic
  - key: problem_solving.planning
    displayName: 规划
    reportDimension: logical
  - key: problem_solving.adaptation
    displayName: 策略调整
    reportDimension: logical
  - key: collaboration.perspective_taking
    displayName: 观点采择
    reportDimension: interpersonal
```

Registry 负责稳定命名和报告维度映射，不在其中定义儿童能力高低。历史 Evidence Policy 必须记录使用的 Registry 版本，避免后续改名静默改变旧报告。

### 5.5 标准证据：Envelope + Event Schema

```ts
interface EvidenceEnvelopeV1<TPayload> {
  schemaVersion: "1.0";
  eventId: string;
  idempotencyKey: string;
  eventType: `${string}.v${number}`;
  occurredAt: string;
  sequenceNo?: number;
  payload: TPayload;
}
```

`sessionId`、`moduleId`、`moduleVersion` 和 `childProfileId` 不接受客户端在事件正文中自由声明，而是由 module token 的服务端绑定关系写入数据库。

每种 `eventType` 必须注册独立 JSON Schema。例如：

```json
{
  "schemaVersion": "1.0",
  "eventId": "0198-example-event",
  "idempotencyKey": "run-42:career-task-3:completed",
  "eventType": "career.task-completed.v1",
  "occurredAt": "2026-08-29T06:01:00Z",
  "sequenceNo": 7,
  "payload": {
    "taskKey": "organize-emergency-supplies",
    "attemptCount": 2,
    "hintCount": 1,
    "completionSeconds": 182,
    "adjustmentCount": 1
  }
}
```

约束：

- `eventType` 必须在对应模块版本的 manifest 中声明；
- `payload` 必须通过该 event type 的 JSON Schema；
- 字段名称和单位由 Schema 固定，例如统一使用 `attemptCount` 和秒；
- 原始对话全文、敏感输入和无关点击流不得进入统一证据库；
- Core API 根据 `session_id + idempotency_key` 防止重复；
- `occurred_at` 保存客户端声明的行为发生时间；
- `sequenceNo` 用于同一会话内的可选排序和缺失检测，不作为全局序号；
- 契约升级新增 event type 版本，不原地修改已发布 payload schema。

### 5.6 Evidence Policy

模块只提交事实性事件和测量值，不直接决定 `strong/reference` 或最终 construct。版本化 Evidence Policy 负责：

```text
event type + validated payload
        ↓
allowed constructs
        ↓
evidence policy/ruleset version
        ↓
evidence level + construct candidates + behavior summary template
```

每条派生证据保存 `policy_version`、`construct_registry_version` 和源事件 ID。模块可在开发时提供建议策略，但运行时判定来源必须是 Core 中注册的 policy。

### 5.7 标准作品

```ts
interface ArtifactV1 {
  schemaVersion: "1.0";
  artifactId: string;
  sessionId: string;
  moduleId: string;
  type: "story" | "snapshot" | "conversation" | "game-result" | "other";
  title: string;
  summary: string;
  previewResourceId?: string;
  sourceResourceId?: string;
  createdAt: string;
}
```

`artifacts` 保存跨模块作品索引，不要求第一阶段复制所有故事正文或对话正文。资源字段保存稳定 ID，不保存 `localhost:端口` URL。Core API 根据资源 ID 解析当前可访问地址；迁移期可为旧模块 ID 建立映射。

### 5.8 SDK 最小接口

```ts
interface AIBoleModuleSDK {
  initialize(): Promise<LaunchContext>;
  exchangeLaunchCode(context: LaunchContext): Promise<void>;
  emitEvidence<TPayload>(event: EvidenceEnvelopeV1<TPayload>): Promise<void>;
  publishArtifact(artifact: Omit<ArtifactV1, "sessionId" | "moduleId">): Promise<void>;
  completeSession(summary?: Record<string, unknown>): Promise<void>;
  interruptSession(reason: string): Promise<void>;
  returnToPortal(): void;
}
```

当前 `window.AIBole` 作为 V0 兼容入口保留一段迁移期，内部转发到新版 SDK。

## 6. 统一数据模型

### 6.1 数据所有权原则

1. Core API 独占统一数据库连接；
2. Portal 和体验模块只能通过 API 访问跨模块数据；
3. 模块内部运行数据可在迁移期保留原存储；
4. 所有跨模块记录必须关联 `child_profile_id` 和 `assessment_session_id`；
5. 报告保存生成时快照，不因后续规则变化静默改变；
6. 报告结论和证据通过显式关联表连接。

### 6.2 核心实体关系

```mermaid
erDiagram
    ACCOUNTS ||--|| CHILD_PROFILES : owns
    CHILD_PROFILES ||--o{ ASSESSMENT_SESSIONS : participates
    MODULES ||--o{ MODULE_VERSIONS : releases
    MODULE_VERSIONS ||--o{ ASSESSMENT_SESSIONS : runs
    ASSESSMENT_SESSIONS ||--o{ MODULE_AUTHORIZATIONS : authorizes
    ASSESSMENT_SESSIONS ||--o{ SOURCE_EVENTS : produces
    SOURCE_EVENTS ||--o{ EVIDENCE_RECORDS : derives
    ASSESSMENT_SESSIONS ||--o{ ARTIFACTS : produces
    CHILD_PROFILES ||--o{ REPORTS : receives
    REPORTS ||--o{ REPORT_EVIDENCE_LINKS : cites
    EVIDENCE_RECORDS ||--o{ REPORT_EVIDENCE_LINKS : supports

    ACCOUNTS {
      text id PK
      text username UK
      text password_hash
      text password_salt
      text created_at
      text updated_at
    }
    CHILD_PROFILES {
      text id PK
      text account_id FK_UK
      text display_name
      integer age
      text created_at
      text updated_at
    }
    MODULES {
      text id PK
      text name
      integer enabled
      text current_version
      text updated_at
    }
    MODULE_VERSIONS {
      text module_id PK_FK
      text version PK
      text contract_version
      text construct_registry_version
      text manifest_json
      text created_at
    }
    ASSESSMENT_SESSIONS {
      text id PK
      text child_profile_id FK
      text module_id FK_COMPOSITE
      text module_version FK_COMPOSITE
      text status
      text created_at
      text started_at
      text ended_at
      integer active_seconds
      integer state_version
    }
    MODULE_AUTHORIZATIONS {
      text id PK
      text session_id FK
      text launch_code_hash UK
      text launch_expires_at
      text exchanged_at
      text token_hash UK
      text scopes_json
      text expires_at
      text revoked_at
    }
    SOURCE_EVENTS {
      text id PK
      text session_id FK
      text idempotency_key
      text event_type
      text schema_version
      text payload_json
      integer sequence_no
      text occurred_at
    }
    EVIDENCE_RECORDS {
      text id PK
      text source_event_id FK
      text evidence_level
      text constructs_json
      text behavior_summary
      text policy_version
      text construct_registry_version
      text derived_at
    }
    ARTIFACTS {
      text id PK
      text session_id FK
      text type
      text title
      text summary
      text preview_resource_id
      text source_resource_id
      text created_at
    }
    REPORTS {
      text id PK
      text child_profile_id FK
      text generator_version
      text ruleset_version
      text prompt_version
      text model_id
      text evidence_set_hash
      text status
      text report_json
      text generated_at
      text published_at
    }
    REPORT_EVIDENCE_LINKS {
      text report_id FK
      text evidence_record_id FK
      text section_key
    }
```

除图中外，数据库必须建立以下组合约束：`module_versions(module_id, version)` 为主键，`assessment_sessions(module_id, module_version)` 引用该组合主键；`source_events(session_id, idempotency_key)` 唯一。`started_at` 在 `created → active` 时写入，不能用会话创建时间代替实际启动时间。

### 6.3 Assessment Session 状态机

会话状态由 Core API 强制执行，模块不能直接写任意状态：

```mermaid
stateDiagram-v2
    [*] --> created
    created --> active: launch code 成功兑换
    created --> abandoned: launch code 过期或用户取消
    active --> completed: completeSession
    active --> interrupted: 页面关闭、网络中断或主动暂停
    active --> abandoned: 明确放弃
    interrupted --> active: resume + 新授权
    interrupted --> abandoned: 明确放弃或超过保留期
    completed --> [*]
    abandoned --> [*]
```

允许的状态转换只有：

| 当前状态 | 允许目标状态 |
|---|---|
| `created` | `active`、`abandoned` |
| `active` | `completed`、`interrupted`、`abandoned` |
| `interrupted` | `active`、`abandoned` |
| `completed` | 无 |
| `abandoned` | 无 |

`completeSession()` 和 `interruptSession()` 必须幂等：重复提交相同目标状态返回当前会话，不重复计算时长或触发报告。非法反向转换返回 `409 SESSION_TRANSITION_INVALID`。`state_version` 用于乐观并发控制，防止双击完成和网络重试覆盖较新的状态。

### 6.4 SQLite 配置

为适应多个本地请求但较低并发的场景，Core API 初始化数据库时统一设置：

- `PRAGMA foreign_keys = ON`；
- `PRAGMA journal_mode = WAL`；
- `PRAGMA busy_timeout = 5000`；
- Core API 的 Uvicorn worker 固定为 `1`；
- 数据迁移按版本顺序执行；
- 一致性备份使用 SQLite Online Backup API 或 `VACUUM INTO`，不直接复制 WAL 运行中的 `.db` 文件；
- 不允许模块进程直接打开统一数据库文件。

### 6.5 模块内部存储的迁移边界

第一轮必须迁入统一数据库：

- 账号和儿童档案；
- 模块定义；
- 探索会话；
- 标准化证据；
- 作品索引；
- 报告快照和证据引用。

第一轮允许保留模块内部：

- 聊天全文、手账和收藏；
- 故事正文、消息、角色和内部观察；
- 深海临时关卡状态；
- 职业任务内部运行明细。

这些内部记录必须能够通过 `child_profile_id`、`assessment_session_id` 或明确的 `sourceResourceId` 与统一数据关联。是否继续迁移，以后按实际维护成本决定。

## 7. API 边界

建议使用 `/api/v1` 作为新契约前缀，旧接口在迁移期继续可用。

| 方法 | 路径 | 用途 |
|---|---|---|
| `POST` | `/api/v1/auth/register` | 注册账号和儿童档案 |
| `POST` | `/api/v1/auth/session` | 创建登录会话 |
| `DELETE` | `/api/v1/auth/session` | 退出登录 |
| `GET` | `/api/v1/profiles/me` | 当前儿童档案 |
| `GET` | `/api/v1/modules` | 获取启用的模块目录 |
| `POST` | `/api/v1/assessment-sessions` | 创建探索会话 |
| `POST` | `/api/v1/module-authorizations:exchange` | 一次性 launch code 换取模块 token |
| `GET` | `/api/v1/assessment-sessions/{id}` | 查询会话和恢复信息 |
| `PATCH` | `/api/v1/assessment-sessions/{id}` | 完成、中断或恢复会话 |
| `POST` | `/api/v1/evidence-events:batch` | 幂等批量提交证据 |
| `POST` | `/api/v1/artifacts` | 发布作品索引 |
| `GET` | `/api/v1/artifacts` | 查询“我的作品” |
| `GET` | `/api/v1/timeline` | 查询成长足迹 |
| `POST` | `/api/v1/reports` | 生成并保存报告快照 |
| `GET` | `/api/v1/reports/latest-published` | 获取最近一次已发布报告 |

Portal 的账号接口使用 HttpOnly Cookie 和 CSRF 防护；体验模块的写接口使用 scoped module bearer token。模块 token 不能调用账号、模块管理、报告发布或其他会话接口。

错误返回统一包含：

```json
{
  "error": {
    "code": "EVIDENCE_SCHEMA_INVALID",
    "message": "这条探索记录格式不完整",
    "retryable": false,
    "requestId": "..."
  }
}
```

儿童界面只显示友好提示；技术错误码用于日志、测试和调试。

## 8. 关键业务流程

### 8.1 启动并完成一次体验

```mermaid
sequenceDiagram
    actor Child as 儿童
    participant Portal
    participant Core as Core API
    participant Module as 体验模块
    participant SDK as Module SDK
    participant DB as SQLite

    Child->>Portal: 选择模块
    Portal->>Core: 创建 assessment_session
    Core->>DB: 保存 created 会话
    Core-->>Portal: sessionId + one-time launchCode
    Portal->>Module: 使用 LaunchContext 启动
    Module->>SDK: initialize + exchangeLaunchCode
    SDK->>Core: launchCode 换取 scoped token
    Core-->>SDK: moduleSessionToken
    Module->>SDK: 上报过程证据/作品
    SDK->>Core: Bearer token + 批量幂等提交
    Core->>DB: 按 event schema 校验并保存 source event
    Core->>DB: 按 policy 派生 evidence record
    Module->>SDK: completeSession
    SDK->>Core: 会话状态改为 completed
    Core->>DB: 保存结束时间和时长
    SDK-->>Portal: 返回探索星球
```

### 8.2 生成报告

```mermaid
flowchart LR
    Sessions[已完成探索会话] --> Events[已验证 Source Events]
    Events --> Policy[版本化 Evidence Policy]
    Policy --> Evidence[Evidence Records]
    Evidence --> Rules[规则分析器]
    Evidence -.可选.-> LLM[LLM 分析器]
    Rules --> Normalize[结构归一化与证据引用校验]
    LLM --> Normalize
    Normalize --> Snapshot[报告快照]
    Snapshot --> Reader[Portal 报告阅读]
```

无论规则路径还是 LLM 路径，输出必须经过同一归一化和证据引用校验。LLM 不可创建数据库中不存在的证据 ID。报告快照同时保存 `generator_version`、`ruleset_version`、`prompt_version`、`model_id`、`evidence_set_hash` 和生成时间；儿童端默认只读取最近一次 `published` 报告。

## 9. 容错与降级

| 场景 | 处理方式 | 是否阻塞儿童体验 |
|---|---|---|
| Core API 暂时不可用 | SDK 保存最多 100 条本地队列，恢复后按幂等键补交 | 否 |
| 模块 AI 服务不可用 | 使用模块现有规则、固定回应或降级内容 | 原则上否 |
| 模块健康检查失败 | Portal 标记该模块暂不可用，并提供重试 | 只影响该模块 |
| 证据契约无效 | Core API 拒绝并记录原因，SDK 不无限重试 | 否 |
| 模块中途关闭 | 会话标记 `interrupted`；已有证据保留 | 否 |
| 报告生成失败 | 展示最近一次成功报告；允许重新生成 | 否 |
| 无真实数据 | 展示明确标记的示例或空状态 | 否 |
| 数据库迁移失败 | 停止 Core API 启动并保留迁移前备份 | 是，仅平台核心 |

不引入消息队列。浏览器本地队列和批量补交足以满足当前规模。

## 10. 部署与启动模型

### 10.1 迁移期

第一阶段保持现有 10 项服务可启动，新增服务配置校验和模块清单，不改变用户运行方式。

### 10.2 目标状态

在不重写模块业务的情况下，将服务数量从 10 项收敛到最多 6 项：

| 目标进程 | 合并内容 |
|---|---|
| Portal | 整合平台 + 天赋报告前端 |
| Core API | 账号中心 + 证据中心 + 报告服务 |
| 聊天观察 | 保留现有 Express 服务 |
| 故事共创 | FastAPI 提供 API 并托管前端构建产物 |
| 深海基地 | FastAPI 提供 API 并托管前端构建产物 |
| 职业体验 | 保留现有 FastAPI/Jinja 服务 |

一键启动脚本仍作为主要入口，但服务定义从单一配置读取。Portal 不再包含端口常量，只使用 Core API 返回的模块入口。

目标状态不要求 Docker、Nginx 或 Kubernetes。若以后需要局域网部署，再增加单一反向代理，不影响当前模块契约。

## 11. 新旧职责对照

| 当前实现 | 目标归属 | 处理方式 |
|---|---|---|
| `app/page.tsx` 中登录请求 | Portal + Core API/accounts | 保留界面，抽取 API 客户端 |
| `app/config/modules.ts` 固定模块数组 | Core API/catalog + `config/modules` | 改为注册表读取 |
| `PlanetHome` 直接 `location.href` | Portal 模块启动器 | 先创建会话，再打开模块 |
| `ai-bole-bridge.js` 全局脚本 | `packages/module-sdk` | 保留 V0 兼容层，逐模块迁移 |
| `platform-core/main.py` 多项职责 | Core API 内部业务模块 | 拆分文件但保留单进程 |
| `explorer_collection.py` 猜测模块字段 | sessions/artifacts 查询服务 | 改为读取标准会话和作品契约 |
| 独立 report-agent | Core API/reports | 合并为内部分析器 |
| 独立 talent-report 前端 | Portal/report | 保留视觉组件，迁入平台外壳 |
| 模块自行判断强/参考证据 | Core API/evidence-policy | 模块提交事实事件，Core 按版本化 policy 派生证据 |
| 模块内部会话 ID | `assessment_session_id` | 建立映射并逐步替换 |

## 12. 原功能保留矩阵

| 功能 | 重构后入口 | 数据来源 | 验收方式 |
|---|---|---|---|
| 登录/注册/退出 | Portal | Core API/accounts | 原账号可迁移并正常登录 |
| 探索星球 | Portal | Core API/modules | 四模块顺序和文案保持，可动态增删 |
| 我的作品 | Portal | Core API/artifacts | 四模块各至少一类作品可回看 |
| 成长足迹 | Portal | Core API/sessions | 首次、最近、次数和时长口径稳定 |
| 天赋报告 | Portal | Core API/reports | 报告维度、建议和证据详情可查看 |
| 聊天对话 | listening | 模块内部 + Core 会话关联 | 完成一次对话并生成记录 |
| 聊天语音/手账/收藏 | listening | 模块内部 | 原功能回归通过 |
| 故事创建和共创 | storytelling | 模块内部 + Core 会话关联 | 完成故事并发布作品 |
| 故事安全/TTS/书架 | storytelling | 模块内部 | 原功能回归通过 |
| 深海三关 | deep-sea-building | 模块内部状态 | 三关均可完成 |
| 深海证据 | deep-sea-building | Core evidence | 三关和整轮证据不重复 |
| 职业选择和工作日 | career-exploration | 模块内部 | 至少完成一个职业流程 |
| 职业过程记录 | career-exploration | Core evidence | 调整、重试、提示等指标可追溯 |
| 示例数据 | Portal | Portal fixture | 始终明确标记为示例 |

## 13. 测试策略

### 13.1 契约测试

所有模块共享同一套测试：

- manifest 字段、版本、入口和适龄范围有效；
- 能接收合法 LaunchContext，并只能兑换一次 launch code；
- module token 只能操作绑定会话和允许 scope；
- 每种 source event 均通过对应 V1 JSON Schema；
- construct 和 evidence level 均由指定版本 Registry/Policy 产生；
- 幂等提交不会创建重复事件；
- 完成、中断和返回平台状态正确；
- 模块无法连接 Core API 时能够暂存证据。

### 13.2 Core API 测试

- 账号之间的数据完全隔离；
- 探索会话状态迁移合法；
- 非法状态转换被拒绝，重复完成不会重复计时；
- source event 必须属于 token 绑定且匹配模块版本的会话；
- source event 保存经过格式校验的 `occurred_at`；
- 历史模块版本 manifest 不会被新版本覆盖；
- Evidence Policy 只引用合法 Construct Registry key；
- 作品必须关联合法会话；
- 报告只能引用真实证据；
- 旧账号和证据迁移后数量、所属和时间不变；
- SQLite 外键、WAL 和幂等索引生效。

### 13.3 最小端到端回归

1. 注册或登录测试账号；
2. 分别完成聊天、故事、深海和职业的最短有效路径；
3. 返回 Portal；
4. 在作品和足迹中看到对应记录；
5. 生成报告；
6. 从报告证据详情回溯到四模块的真实事件；
7. 退出并重新登录，确认数据仍存在且不串号。

### 13.4 CI 最小质量门禁

本项目不建立复杂发布流水线，但每个合并请求或主分支提交必须执行统一脚本，并满足：

| 门禁 | 要求 |
|---|---|
| 格式与静态检查 | Portal、Core 和被修改模块的 lint/typecheck 全部通过 |
| Schema 检查 | OpenAPI、Manifest、Construct Registry 和全部 Event Schema 有效 |
| 单元测试 | 被修改应用和 Core API 测试通过 |
| 契约测试 | 四模块适配器及 SDK 公共契约通过 |
| 迁移测试 | 临时副本执行 migration dry-run，数量和外键校验通过 |
| 最小 E2E | Portal 登录、创建会话、提交事件、完成会话和读取结果通过 |

由于部分模块依赖本地 AI、语音或图形交互，CI 中允许使用确定性 stub 完成 smoke test；真实 AI 和完整人工体验验收在阶段发布检查中执行。任何被修改模块不得以“其他模块没有 CI”为理由跳过自己的契约测试。

## 14. 分阶段迁移计划

```mermaid
flowchart LR
    P0[阶段 0\n冻结现状基线] --> P1[阶段 1\n建立契约与注册表]
    P1 --> P2[阶段 2\n统一核心数据库]
    P2 --> P3[阶段 3\n收拢 Portal 与 Core]
    P3 --> P4[阶段 4\n逐模块接入]
    P4 --> P5[阶段 5\n可选技术栈收敛]
```

### 阶段 0：冻结现状基线

- 保存当前服务、端口、数据库和事件清单；
- 为四模块建立最小回归路径；
- 备份 `ai_bole_core.db`、`story_cocreate.db`、`career_sim.db` 和聊天数据目录；
- 固定现有功能保留矩阵；
- 不改变运行行为。

### 阶段 1：建立契约与模块注册表

- 将 OpenAPI 和 JSON Schema 作为事实来源，定义 Manifest、LaunchContext、Evidence Envelope、各 Event Payload、Construct Registry、Evidence Policy 和 Artifact；
- 实现一次性 launch code、短期 scoped token 和 token 撤销；
- 建立 Modules + Module Versions，不覆盖历史 manifest；
- 建立并由服务器执行 Assessment Session 状态机；
- 新建模块配置读取和校验；
- Portal 从模块目录渲染入口；
- 实现 SDK V1 和 V0 桥接适配器；
- 保持当前 10 项服务和模块路径不变。

### 阶段 2：统一核心数据库

- 增加 child_profiles、modules、module_versions、assessment_sessions、module_authorizations、source_events、evidence_records、artifacts、reports 和关联表；
- 将现有 evidence_events 映射到 source event 与 derived evidence，并补充 session 归属、行为发生时间和策略版本；
- 开启 WAL、外键和迁移版本；
- 编写可重复执行的数据迁移和回滚备份；
- Core API 成为唯一访问者。

### 阶段 3：收拢 Portal 与 Core

- 将天赋报告 Vue 页面迁入 Portal；
- 将 report-agent 合并为 Core API 内部 reports 模块；
- 将作品和成长足迹改为查询正式 sessions/artifacts；
- 消除 Portal 中的 `CORE_URL`、`REPORT_URL` 和固定端口常量；
- 将服务数逐步收敛。

### 阶段 4：逐模块接入

建议顺序：

1. **深海基地**：现有事件最完整，用作 SDK 样板；
2. **故事共创**：作品和会话关系清楚；
3. **职业体验**：迁移内部会话到平台会话映射；
4. **聊天观察**：内部数据类型最多，最后接入更稳妥。

每个模块独立完成：契约接入、数据关联、回归测试和旧桥接移除。任何时点都至少保留一条可工作的生产路径。

### 阶段 5：可选技术栈收敛

只有出现明确维护成本时再执行：

- 将原生页面逐步组件化；
- 统一 Vite 构建和前端包管理；
- 迁移模块内部持久化数据；
- 抽取真正复用的 UI 组件。

该阶段不属于完成本次架构重构的必要条件。

## 15. 数据迁移与兼容策略

每一项数据库或跨模块契约变更均按 **Expand → Migrate → Contract** 执行，不允许在同一发布版本中同时增加替代路径、迁移最后一个调用者并删除旧路径。

### 15.1 Expand：先增加兼容能力

- 迁移前使用 SQLite Online Backup API 或 `VACUUM INTO` 创建可校验备份，聊天数据目录另行复制，不覆盖原文件；
- 先增加新表、新列、新索引、新 API 和 V1 Schema，旧字段与 V0 API 保持可读写；
- 新列在兼容期允许为空或具有可区分的迁移默认值，不能假装历史数据已经满足新语义；
- `window.AIBole.emitEvidence` 通过兼容层转发到 V1 事件入口；
- 新旧写入必须有明确的唯一事实来源；如短期双写不可避免，应由 Core API 在同一事务中完成并接受一致性测试。

### 15.2 Migrate：迁移与验证

- 迁移工具以旧数据只读、新结构写入方式运行；
- 每张迁移表记录来源系统、旧 ID、迁移批次和迁移时间；
- 脚本可重复执行，重复记录通过旧 ID 映射或幂等键跳过；
- 无法可靠补齐的 `occurred_at` 必须标注推断来源，不得直接等同于迁移时间；
- 迁移后至少校验账号数、儿童档案数、会话数、源事件数、证据数、模块分布、时间范围、外键完整性和抽样内容哈希；
- 在数据库临时副本上执行迁移 dry-run 和回滚演练，生产文件迁移失败时保留原文件并停止启动；
- 所有 Portal 与模块调用者切换至 V1 后，至少经过一个可回退发布周期再进入 Contract。

### 15.3 Contract：最后移除旧路径

- 仅当调用日志和仓库搜索均证明旧 API、旧字段与 V0 SDK 不再被使用时，才删除兼容路径；
- 删除前固化最终迁移报告、备份位置、恢复步骤和负责人确认；
- 删除旧列或旧表使用新的 migration 版本，禁止覆盖或改写已经执行过的 migration；
- 历史 `module_version`、manifest、Construct Registry、Evidence Policy 和已发布报告快照不得因 Contract 被覆盖；
- Contract 完成后再次运行契约测试、迁移测试和最小端到端回归。

## 16. 风险与控制

| 风险 | 影响 | 控制方式 |
|---|---|---|
| 统一数据库迁移造成历史记录丢失 | 高 | 只读迁移、备份、数量校验和回滚演练 |
| 模块契约过度抽象 | 中 | V1 只包含当前四模块共同需要的最小字段 |
| 报告规则在迁移中改变 | 高 | 先保存旧输出样本，架构迁移不调整测评结论 |
| 浏览器离线队列串号或泄露 | 高 | 队列按 session + module version 隔离且不持久化 token；恢复后重新授权，退出或会话终止即停止补交 |
| `sessionId` 被误当作凭据 | 高 | 模块接口只接受 scoped token；服务端校验 token 的 session、模块版本、scope、过期与撤销状态 |
| 模块版本覆盖导致历史不可复现 | 高 | manifest 与 module version 发布后不可变；升级只能新增版本 |
| Construct 或强弱证据语义漂移 | 高 | Construct Registry 与 Evidence Policy 版本化，报告快照保存实际使用版本 |
| 不同技术栈 SDK 行为不一致 | 中 | 使用共享契约测试，不强制共享框架代码 |
| 服务合并引入启动回归 | 中 | 每次只合并一项，并保留旧启动配置回退 |
| 模块内部 ID 与平台 ID 混淆 | 中 | LaunchContext 明确提供 sessionId，旧 ID 仅存 `sourceResourceId` |

## 17. 非目标

本次架构重构明确不包含：

- 将所有模块重写为 React 或 Vue；
- 引入微服务、消息队列、Kubernetes 或服务网格；
- 为高并发进行分库分表或缓存集群设计；
- 在架构迁移中重新定义儿童天赋理论或评分规则；
- 一次性迁移全部聊天、故事和职业内部数据；
- 建立多学校、多租户或复杂教师权限体系；
- 对现有 UI 进行全面视觉重做。

## 18. 验收标准

### 架构验收

- 新模块通过新增 manifest 即可注册，Portal 不需要修改模块专用代码；
- Portal 不再硬编码四模块 URL 和端口；
- 所有跨模块数据只通过 Core API 访问；
- Core API 是统一 SQLite 的唯一访问者；
- `sessionId` 仅用于关联，不能单独读取或写入任何会话数据；模块必须以一次性 launch code 换取 scoped token；
- 每个已发布模块版本具有不可变、可追溯且通过 Schema 校验的 manifest；
- 每条 source event 都通过 Envelope 与对应 event-type JSON Schema 的机器校验，并保存 `occurred_at`；
- 所有 construct 均来自指定版本 Construct Registry，强/参考证据由指定版本 Evidence Policy 派生，模块不能自行决定；
- Assessment Session 的每次状态变化均由服务端状态机校验，非法迁移返回 `409` 且不改变数据；
- 每条跨模块证据都关联儿童档案、探索会话、模块版本、Registry 版本和 Policy 版本；
- 作品、足迹和报告读取统一模型；
- 报告结论能够引用真实存在的证据，并可由生成器、规则、提示词、模型和证据集合哈希复现其输入条件；
- “最近报告”只返回最近一次已发布版本，不暴露草稿或生成失败记录；
- 单个体验模块故障不会阻塞其他模块。

### 功能验收

- 原功能保留矩阵全部通过；
- 四模块各完成一次真实体验后，作品、足迹和报告均有对应记录；
- 离线暂存、幂等补交和重新登录不产生重复或串号；
- 示例内容不会被标记为真实儿童数据；
- 原有数据库和文件数据均有可验证迁移结果。

### 运维验收

- 一键安装、一键启动、状态检查和停止脚本仍然可用；
- 目标状态服务数量不超过 6 项；
- 服务入口和健康检查来自同一配置；
- 数据库可通过单一命令备份和校验；
- 开发者能够从文档定位任一模块的数据入口、会话和证据来源。

## 19. 实施交付物与后续文档

阶段 1 必须先产出并纳入版本控制的机器可读契约：

1. `packages/contracts/openapi/core-api.v1.yaml`；
2. Module Manifest、LaunchContext、Evidence Envelope、各 Event Payload、Construct Registry、Evidence Policy 与 Artifact JSON Schema；
3. 可被 SDK、Core API 和契约测试共同读取的版本号与兼容性规则。

以上文件是契约事实来源，不得只在 Markdown、TypeScript 类型或服务端代码中维护另一份定义。Schema 或 OpenAPI 变更必须先通过兼容性检查，再更新实现。

配套实施文档包括：

1. 逐任务实施计划；
2. SQLite Expand → Migrate → Contract 与回滚手册；
3. 四模块功能回归清单；
4. 实验数据导出说明；
5. 模块接入示例和本地调试指南。

实施计划必须按阶段拆分，每个阶段都能独立运行和验收，不允许以“全部重写完成后才能启动”为迁移方式。
