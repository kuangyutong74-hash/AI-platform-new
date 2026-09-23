# AI 伯乐：CHI / IDC / UbiComp / UIST / CSCW 近年论文综述与投稿设计

**检索日期**：2026-09-20  
**时间范围**：2023–2026  
**纳入规模**：26 篇正式主会或正式期刊轨论文（CHI 8、IDC 5、UIST 4、UbiComp/IMWUT 4、CSCW/PACM HCI 5）  
**引用格式**：APA 7（正文采用作者—年份，文末列 DOI/正式链接）

## 执行摘要

AI 伯乐最有发表潜力的研究贡献，不是“用 AI 准确识别儿童天赋”，而是：**如何从开放式、多情境儿童活动中形成可追溯、带不确定性、允许儿童及成人质疑和修订的能力反思材料**。近三年的相关顶会论文普遍把生成式 AI 定位为脚手架、共同创作者或沟通媒介，而不是权威裁判；高质量论文通常同时保留任务结果、过程日志、用户解释和利益相关者分歧。

在五个目标会议中，**CHI 最适合作为当前主目标，IDC 是最稳妥且主题最匹配的目标**。若把重点进一步收束为儿童对画像的理解、质疑、撤回和改写，IDC 尤其合适；若强调儿童—家长—教师如何协商证据、权限和分歧，则可转向 CSCW。UIST 需要把贡献压缩成一个可验证的新交互机制；UbiComp/IMWUT 则需要至少数周的自然环境部署、跨情境感知模型和跨儿童验证，距离当前产品形态最远。

推荐论文主标题方向：**Designing Traceable and Contestable AI-Supported Ability Reflections for Young Children Across Open-Ended Activities**。核心实验应比较“结论式画像”和“证据链接、带不确定性、可校准的画像”，主要结果不是满意度，而是证据追溯、过度概括、纠错、跨角色理解一致性和后续行动建议质量。

## 1. 项目研究化定义

AI 伯乐是面向低年级儿童的小规模实验平台。儿童通过聊天观察、故事共创、空间与生态任务、职业情境决策留下过程行为；平台把行为片段、作品和任务语境组织为阶段性能力反思，并向儿童、家长和教师展示。

论文中应坚持以下边界：

- 不声称识别稳定、内在或先天“天赋”；使用 *situated behavioral evidence*、*ability reflection*、*evidence-linked feedback*。
- 不输出排名、诊断或单一能力分；证据不足时明确“不足以说明”。
- 区分儿童原始行为、系统推断、家长补充和教师观察，并保留来源与版本。
- 把质疑、拒绝、修改和撤回画像视为儿童能动性，而不是系统失败。

## 2. 检索与筛选方法

采用会议定向检索：核查 ACM Digital Library、会议正式 program/proceedings、PACM HCI/IMWUT、作者或机构开放全文。关键词围绕 children/child、generative AI/LLM、storytelling、creative learning、AI literacy、trust、parent、evidence、learning analytics、sensing、agency、explainability、collaboration。

纳入标准：2023–2026；正式 CHI/IDC/UIST full paper、PACM HCI CSCW 正式论文或 IMWUT 正式论文；与儿童 AI 交互、过程证据、家庭协作、可解释画像或相邻方法直接相关。排除 workshop、demo、competition、Extended Abstract 和尚未确认正式录用的预印本。若公开全文未给出某项实验细节，标记“未报告/待全文核验”，不推测。

局限：这是一轮面向论文设计的定向综述，不是穷尽式数据库元分析；若后续正式投稿，应补充 Scopus/Web of Science 检索式、双人筛选、PRISMA 流程和质量评价表。

## 3. 跨论文主题综合

### 3.1 从“AI 给答案”转向“AI 提供受约束的脚手架”

Mathemyths、StoryPal、CharacterCritique、Oak Story 和 Scratch Copilot 都把 AI 限制在明确的教育或创作目标内：追问、提示、挑战理由、生成候选方案或调整叙事顺序。共同结论是，儿童需要保留选择、拒绝和改写空间；AI 的流畅不等于学习有效。Storyfier 甚至发现用户更喜欢 AI 条件，但学习表现反而更差，说明“减负”可能移除本应观察的认知努力。

### 3.2 最终作品不足以证明能力，过程行为才是关键证据

ChatScratch、From Words to Wonder、Scratch Copilot 和 CharacterCritique 都结合了作品、日志、交互行为和访谈。可复用的过程指标包括：AI 建议采纳/拒绝/改写、分支探索、求助、错误恢复、解释长度、视角转换、策略调整和任务坚持。AI 伯乐应把“孩子做出了什么”与“如何做到、在何种提示下做到”同时展示。

### 3.3 可解释性必须包含“孩子如何理解推断来源”

儿童可能把 AI 视为具有内在智慧、能看见人的本质。Children’s Mental Models of AI Reasoning 和 Hey Curio 表明，低龄儿童既会信任 AI，也会受到外观、声音和准确性线索影响。因此，仅展示“证据”并不自动等于解释成功；需要测量儿童和家长是否理解画像来自有限行为样本、是否知道它可能错、能否指出依据并提出反例。

### 3.4 家长不是替代儿童的代理人，而是校准与治理参与者

CHI、CSCW 的多方研究一致指出：儿童、家长和教师对 AI 的价值与风险理解不同。良好系统应支持选择性分享、逐次同意、记忆隔离、角色化权限和分歧保留，而不是让成人覆盖儿童原始声音。画像最有价值的角色是打开对话，而不是成为第三个权威裁判。

### 3.5 跨情境推断需要情境归一化与构念验证

LemurDx、CASES 和 gaze-mouse 融合工作证明，行为只有结合“当时在做什么”才有解释力。活动识别、投入和能力是不同构念；高分类准确率不能直接支持“天赋”结论。AI 伯乐应把任务语义、提示强度和行为序列共同纳入证据，并以独立任务、成人观察或经验证量表验证构念。

## 4. 逐篇结构化提炼

### 4.1 CHI

#### CHI-1 Teachers, Parents, and Students’ Perspectives on Integrating Generative AI into Elementary Literacy Education（2024）

- **动机 / 问题**：小学写作引入生成式 AI，但儿童、家长、教师对机会、作者权、能动性和安全的看法缺乏整体理解。
- **系统 / 交互**：儿童使用 ChatGPT 与 Stable Diffusion 创作视觉故事，成人观察并讨论。
- **实验**：12 名 8–12 岁儿童、12 名家长、16 名教师；家庭工作坊约 2 小时，教师访谈约 1 小时；观察、录音、作品、照片与主题分析，无对照实验。
- **结果 / 叙事**：三方对 AI 的角色理解不同；价值冲突本身构成贡献。成人监督、明确人机角色、保留儿童编辑空间很重要。
- **局限 / 未来**：便利样本、文化与收入偏倚、单次活动、无修订史；需课堂纵向部署和作者权测量。
- **对 AI 伯乐**：分层保存原始行为、AI 推断和成人补充，报告必须可质疑、可回溯。

#### CHI-2 Mathemyths（2024）

- **动机 / 问题**：LLM 共创伙伴能否像熟练人类伙伴一样支持儿童数学语言学习。
- **系统 / 交互**：语音故事代理把 sum、estimate、equal 等概念嵌入轮流续写，困难时简化或提示。
- **实验**：35 名 4–8 岁儿童；AI 组 19、人类伙伴组 16；前测—两则故事—后测。指标含 24 题知识测验、迁移/运用、故事质量、回答长度、投入与愉悦；混合 ANOVA。
- **结果 / 叙事**：两组均显著提升且增益相当；人类伙伴条件回答更长、犹豫更少。论文把 LLM 写成明确能力目标下的可扩展脚手架。
- **局限 / 未来**：短时、图书馆样本、云端语音隐私；需长期保持、迁移和自适应负荷研究。
- **对 AI 伯乐**：宽泛天赋应拆成可观察构念，并用过程编码加独立前后测验证。

#### CHI-3 ChatScratch（2024）

- **动机 / 问题**：儿童自主 Scratch 学习面临构思、素材和代码指导困难。
- **系统 / 交互**：故事板规划、图像生成、意图到积木映射和分步语音辅导。
- **实验**：形成期 6 位教师；主试 24 名 6–12 岁 Scratch 初学者，被试内 ChatScratch vs Scratch，条件与主题反平衡、间隔 48 小时。指标含作品专家评分、CSI、Dr. Scratch、AI 模板保留/扩展率、行为编码和访谈。
- **结果 / 叙事**：作品、代码、表达、探索和投入提升；论文通过“计划—素材—实现”全过程论证系统价值。
- **局限 / 未来**：短期、小样本、中文初学者、仅两个主题；需可解释错误与逐步撤除脚手架。
- **对 AI 伯乐**：记录采纳、扩展、停顿、求助和错误恢复，比只保存成品更有研究价值。

#### CHI-4 Scientific and Fantastical（2024）

- **动机 / 问题**：文化相关 AR 叙事与 LLM 个性化能否改善儿童科学学习和投入。
- **系统 / 交互**：以嫦娥故事串联 AR 天文/生态活动；GPT-4 个性化回信与硬编码回信对照。
- **实验**：50 名儿童，LLM vs 硬编码组间实验；两次会话与一周随访。指标含知识保持、科学动机、环境态度、Giggle Gauge、回答相关性、字数和访谈。
- **结果 / 叙事**：两组均有增益；LLM 组相关性更高、后段投入更稳定。组件消融隔离了个性化回复的增量。
- **局限 / 未来**：单地点短期、文化分组较粗、事实与幻想可能混淆。
- **对 AI 伯乐**：固定任务流程，仅开/关个性化或证据编排组件，避免整套系统对空白基线。

#### CHI-5 Exploring AI Problem Formulation with Children via Teachable Machines（2024）

- **动机 / 问题**：儿童会定义什么 AI 问题、采用什么隐喻、体现什么价值。
- **系统 / 交互**：体验 Teachable Machine 后，用 Big Paper 故事板定义目的、数据、输入输出、错误和恢复。
- **实验**：10 名 8–13 岁儿童与 9 名成人代际共创；故事板、音视频、谈话、田野笔记，多框架双研究者编码。
- **结果 / 叙事**：儿童能讨论假阳性、假阴性、补充数据和人类控制；贡献从“教儿童用 AI”转向“儿童决定什么值得 AI 解决”。
- **局限 / 未来**：探索性、支持密集、无前后测或方法对照。
- **对 AI 伯乐**：先收集儿童自述的兴趣、价值和生活实例，再与系统证据并置，避免标签先行。

#### CHI-6 From Words to Wonder（2025）

- **动机 / 问题**：生成式 AI 是否能提高儿童故事质量和创造性，并维持儿童的规划与选择。
- **系统 / 交互**：StoryPrompt 支持角色/场景/情绪规划、AI 词语提示、语音/文本编辑与漫画生成。
- **实验**：40 名二至六年级儿童，StoryPrompt vs 传统 storyboard；故事创造性与丰富度、规划与 AI 使用行为、偏好、访谈和教师反馈。公开材料未给各组人数和完整统计量。
- **结果 / 叙事**：AI 条件作品更丰富、更有创造性；过程观察解释量化差异。
- **局限 / 未来**：短时、作品评分主观、图像准确性和过度依赖风险；需长期迁移与作者权研究。
- **对 AI 伯乐**：创造力应由盲评作品加过程策略共同论证，而非模型单一评分。

#### CHI-7 CharacterCritique（2025）

- **动机 / 问题**：多代理故事讨论能否支持低龄儿童批判思维与亲子对话。
- **系统 / 交互**：固定角色代理围绕冲突情境追问、挑战方案并要求理由，不直接给答案。
- **实验**：32 组 5–6 岁亲子，16 组系统、16 组相同内容纸质故事及提示；约 1 小时。指标含投入、家长填写的批判思维量表、461 条对话日志和亲子访谈。
- **结果 / 叙事**：系统组深入讨论和问题解决更多；效果来自代理与家长共同作用。
- **局限 / 未来**：短时、语音与非语言信号缺失、图像风格不稳；需多模态和纵向验证。
- **对 AI 伯乐**：用多立场冲突诱发理由、修正和视角转换，把这些行为编码为证据。

#### CHI-8 Enhancing Pediatric Communication: ARCH（2025）

- **动机 / 问题**：AI 如何促进儿童—家长—专业人员沟通，同时避免成为权威主体。
- **系统 / 交互**：Child Bot 帮助儿童表达担忧，Expert Bot 向家长提供匿名化情境与指导。
- **实验**：12 组 9–12 岁癌症儿童与家长共创；15 名美/韩儿科沟通专家走查原型；主题分析，无疗效实验。
- **结果 / 叙事**：AI 可成为表达出口和辅助沟通空间；发展阶段、文化、隐私和危机升级是核心边界。
- **局限 / 未来**：原型与期望研究，未真实部署；需安全性、准确性和权力关系验证。
- **对 AI 伯乐**：画像应成为沟通空间；儿童、家长、教师采用分层权限，高风险结论需人工复核。

### 4.2 IDC

#### IDC-1 StoryPal（2025）

- **动机 / 问题**：对话式阅读有效，但家长时间、资源和语言有限；LLM 如何动态生成适龄问题与脚手架。
- **系统 / 交互**：语音阅读伙伴，基于 PEER/CROWD；答错提示或选择题、答对升阶、沉默鼓励。
- **实验**：23 名 4–7 岁儿童，约 15 分钟绘本阅读；儿童 8 项四点态度量表、家长 15 分钟访谈。指标含问题类型、回答率、相关性、字数、视觉参与和轮替；人工复核 IRR=.89，家长编码 ICC=.80。
- **结果 / 叙事**：高言语参与，脚手架可按困难程度调整；家长视其为补充而非替代。
- **局限 / 未来**：单次、单书、无对照和学习前后测；双语和多儿童交互不足。
- **对 AI 伯乐**：证据不仅看结果，还要看提示后恢复、主动关联与协作。

#### IDC-2 Scratch Copilot（2025）

- **动机 / 问题**：AI 如何支持儿童把创意变为程序，同时不削弱能动性。
- **系统 / 交互**：Scratch-like 编辑器旁嵌 GPT-4o 和 DALL-E 3；支持构思、调试、导航和素材，提示词要求多问少代做。
- **实验**：18 名 7–14 岁儿童、来自 11 国；20 场远程 think-aloud 创作与访谈；178,105 词转录，演绎加归纳编码。
- **结果 / 叙事**：缓解 blank canvas 并支持调试；同时存在意图误解、文化不贴合和步骤不全，儿童会拒绝和修改建议。
- **局限 / 未来**：小样本、远程、研究者在场、无学习增益和对照。
- **对 AI 伯乐**：把采纳、拒绝、重问和改写作为能动性证据。

#### IDC-3 Children’s Mental Models of AI Reasoning（2025）

- **动机 / 问题**：儿童如何理解 AI“推理”，年龄与心智模型有何关联。
- **系统 / 交互**：不是产品评测；先共设计研究工具，再进行现场研究。
- **实验**：8 名儿童共设计，106 名三至八年级儿童现场研究；公开摘要未充分报告任务量表和统计细节。
- **结果 / 叙事**：归纳出演绎、归纳和“内在智能”三类模型；低年级更易认为 AI 本身聪明，高年级更能理解模式识别。
- **局限 / 未来**：横断面年龄差异不能证明发展因果。
- **对 AI 伯乐**：必须测孩子如何理解画像来源，并说明它是有限行为模式的暂时推断。

#### IDC-4 Hey Curio, Can You Tell Me More?（2025）

- **动机 / 问题**：儿童在自然环境中如何向生成式 AI 求知并校准信任。
- **系统 / 交互**：具吸引力的语音角色 Curio，支持连续追问，并嵌入相信/质疑反馈。
- **实验**：22 名 6–10 岁儿童，两周居家研究；日志、问题链、信任/准确性感知和访谈。
- **结果 / 叙事**：儿童会扩展追问，整体较信任 AI，但对明显准确性问题有反应；亲和角色同时可能放大过度信任。
- **局限 / 未来**：样本小、设备与家庭环境差异；需长期、年龄和内容域比较。
- **对 AI 伯乐**：目标是信任校准而非提高信任；展示反例、来源和“我不确定”。

#### IDC-5 Children Envision Future GenAI Chatbots that are Bounded, Helpful, and Safe（2026）

- **动机 / 问题**：儿童声音在 GenAI 设计中不足；儿童如何想象理想聊天机器人。
- **系统 / 交互**：跨文化工作坊中体验、讨论并设计未来 chatbot。
- **实验**：32 名 9–12 岁儿童，越南、芬兰、日本；公开摘要未报告分组、时长和编码可靠性。
- **结果 / 叙事**：儿童希望 AI 领域有边界、帮助学习且安全；儿童从被动用户转为技术塑造者。
- **局限 / 未来**：愿景研究不是部署效果，年龄高于 AI 伯乐核心用户。
- **对 AI 伯乐**：四模块应有清晰边界；用儿童共设计检验“天赋”概念的文化偏置。

### 4.3 UIST

#### UIST-1 Oak Story（2025）

- **动机 / 问题**：开放 LLM 容易偏离教学目标；受约束动态叙事能否兼顾个性化、学习与能动性。
- **系统 / 交互**：橡树林生态移动应用，动态解释儿童兴趣、调整角色对话和场景顺序，并连接 AR/现实活动。
- **实验**：47 名四至六年级儿童；动态适配 vs 相同 LLM 对话、相同 AR 活动但静态顺序。前后知识、兴趣、投入、享受、能动性、响应性和访谈。
- **结果 / 叙事**：动态组学习增益、投入和感知能动性更高；贡献是约束型架构，不是“LLM 会讲故事”。
- **局限 / 未来**：单主题、短期、年龄偏高；需长期迁移、安全与文化适配。
- **对 AI 伯乐**：固定内容与底层模型，只移除跨模块个性化编排，验证平台核心机制。

#### UIST-2 Storyfier（2023）

- **动机 / 问题**：为任意词汇生成连贯语境并支持主动使用是否有助学习。
- **系统 / 交互**：生成目标词故事、完形填空、人机轮流续写和写作帮助。
- **实验**：形成期多轮教师/学习者研究；主实验 28 名中国大学生，AI/无 AI × read-only/read-cloze-write 被试内。指标为词义回忆、目标词使用、作文和体验。
- **结果 / 叙事**：用户更喜欢 AI，但需要主动产出的条件中 AI 组反而更差，揭示 AI 可能替代必要认知努力。
- **局限 / 未来**：大学生、短时、无延迟保持，不能直接外推儿童。
- **对 AI 伯乐**：AI 不应替孩子完成本应被观察的思考；同时测主观体验和客观表现。

#### UIST-3 VizGroup（2024）

- **动机 / 问题**：教师难实时理解大班协作行为和未预定义的异常模式。
- **系统 / 交互**：可视分析与事件驱动监控单元；LLM 推荐规则、追踪器和提醒。
- **实验**：12 名有编程教学经验者，基于真实课堂回放比较基础可视分析、无建议和有 LLM 建议的系统条件。指标含时间、准确率/召回、规则数量与多样性、NASA-TLX、轨迹和访谈。
- **结果 / 叙事**：LLM 扩大教师的可见性和假设空间，不替教师判定。
- **局限 / 未来**：小样本、回放非真实干预；长期依赖与错误建议不足。
- **对 AI 伯乐**：让 AI 提供候选证据模式，测新发现、覆盖、误报、耗时与判断变化。

#### UIST-4 Story-Driven（2024）

- **动机 / 问题**：实时情境信息如何改善自动生成故事的沉浸与连贯。
- **系统 / 交互**：持续注入路线、GPS、交通、地点与预计到达时间，使故事与现实移动同步。
- **实验**：两项真实车辆研究，总 N=30（探索 5、比较 25），与非情境化/传统故事比较；体验、沉浸、环境感知和访谈。
- **结果 / 叙事**：情境同步改善体验，贡献是端到端实时生成与情境改写机制。
- **局限 / 未来**：成人车内、小样本、网络与延迟依赖；安全和长期新鲜感未知。
- **对 AI 伯乐**：把任务中正在发生的行为作为情境输入，并隔离验证 context synchronization。

### 4.4 UbiComp / IMWUT

#### IMWUT-1 LemurDx（2023）

- **动机 / 问题**：能否以低负担自然感知客观测量儿童活动性，同时避免完全依赖家长报告。
- **系统 / 交互**：Apple Watch 被动加速度，结合活动情境归一化；临床人员需要可解释的跨情境风险信号。
- **实验**：61 名 5–12 岁儿童，佩戴 2–7 天；LOPO 交叉验证和五折调参，比较人工情境、自动情境、无情境模型，并访谈 5 位临床人员。
- **结果 / 叙事**：自动情境模型准确率 82.0%，无情境仅 67.2%；强调补充而非替代诊断。
- **局限 / 未来**：极端组、小样本、短期、药物与设备偏差。
- **对 AI 伯乐**：对不同模块作情境归一化，使用跨儿童验证和情境消融，输出信号而非诊断。

#### IMWUT-2 Eggly（2023）

- **动机 / 问题**：如何为 ASD 儿童设计有故事性、即时且个性化的神经反馈游戏。
- **系统 / 交互**：消费级 EEG、平板 AR、自适应难度；神经反馈改变速度、音乐和角色表情。
- **实验**：10 个月与 4 位专家迭代；5 名儿童现场研究，其中 1 名三周部署；日志、观察和照护者/家长访谈。
- **结果 / 叙事**：支持场域可用性和投入，但证据不足以声称疗效。
- **局限 / 未来**：N=5、纵向仅 1 人、无对照、部分 Wizard-of-Oz。
- **对 AI 伯乐**：采用“专家共创—儿童可行性—纵向部署”的分阶段证据链，并做多源三角验证。

#### IMWUT-3 Integrating Gaze and Mouse…（2023）

- **动机 / 问题**：眼动和鼠标的协调是否能更准确、较可接受地识别数字学习活动。
- **系统 / 交互**：Joint Cross-Attention Fusion Net 融合注视和鼠标序列。
- **实验**：先调查 200 名大学生的感知接受度；再采集 8 类学习活动多模态数据，公开摘要未可靠报告采集 N。指标为分类 F1 和单模态消融。
- **结果 / 叙事**：最高 F1 94.87%，比单眼动或单鼠标高至少 7.44%。
- **局限 / 未来**：受控活动、大学生、特定硬件；活动识别不等于投入或能力。
- **对 AI 伯乐**：可以比较单一日志与多模态融合，但必须另做能力构念验证。

#### IMWUT-4 CASES（2023）

- **动机 / 问题**：仅靠眼动难解释阅读状态，需把行为与文本语义同步。
- **系统 / 交互**：智能眼镜对齐凝视与词句语义，多任务网络估计阅读状态并提供语义解释。
- **实验**：实验室消融 N=25；真实环境 N=13、3.5 个月；准确率、日志、访谈和自我觉察。
- **结果 / 叙事**：语义+眼动相较 eye-only 句级准确率提高 20.90%；长期部署显示自我觉察潜力。
- **局限 / 未来**：配准和校准负担、样本小、field 阶段因果有限、语言泛化未知。
- **对 AI 伯乐**：融合任务语义与行为序列，并把相应证据片段呈现给成人，而非只给黑箱总分。

### 4.5 CSCW

#### CSCW-1 Exploring Parent’s Needs for Children-Centered AI…（2024）

- **动机 / 问题**：AI 故事技术进入家庭后是否真正满足学前儿童及家长需求。
- **系统 / 交互**：体验现有 AI 互动故事/阅读技术并讨论家庭使用。
- **实验**：17 名 3–6 岁儿童的家长，质性体验和访谈；公开摘要未报告完整时长和编码可靠性。
- **结果 / 叙事**：AI 能提高沉浸，但年龄/语境适配、可控性、质量、安全和亲子角色仍存在落差。
- **局限 / 未来**：只有家长、小样本、短期主观数据，无儿童结果。
- **对 AI 伯乐**：家长是校准者而不是儿童代理人，需并列保留儿童声音。

#### CSCW-2 Re-orienting Parental Control for Children（2024）

- **动机 / 问题**：家长控制工具偏限制和监控，如何转向开放沟通和儿童自律。
- **系统 / 交互**：发展心理学驱动的低保真方案，用活动洞察促谈、给儿童 nudges、按情境细化控制。
- **实验**：21 位家长访谈/think-aloud、3 位 UX 专家迭代；随后 MTurk N=156 比较 Google Family Link 基线和新方案。
- **结果 / 叙事**：家长重视对话、自律和情境化控制；论文把“控制”重构为发展性脚手架。
- **局限 / 未来**：低保真、自报、无儿童参与或真实部署。
- **对 AI 伯乐**：家长端应是对话与证据解释界面，不是监控排名台。

#### CSCW-3 Families’ Vision of Generative AI Agents for Household Safety（2025）

- **动机 / 问题**：家庭如何协商 AI 代理的角色、信任和隐私边界。
- **系统 / 交互**：通过家庭构想活动讨论多代理、记忆与分享机制。
- **实验**：13 组亲子 dyads，两阶段个别访谈加亲子协作会话；公开摘要未报告完整年龄和编码可靠性。
- **结果 / 叙事**：偏好多代理分工；提出 memory segregation、conversational consent、selective sharing、progressive memory。
- **局限 / 未来**：愿景性、小样本、无部署；敏感场景需危机机制。
- **对 AI 伯乐**：模块记忆隔离、逐次同意跨模块汇总、选择性分享、随年龄渐进管理画像。

#### CSCW-4 They Don’t Come With a Handbook（2024）

- **动机 / 问题**：技术如何支持家庭中复杂、日常的亲子情绪互动。
- **系统 / 交互**：从心理理论推导设计空间，再以情境原型让家长评议。
- **实验**：22 位有 6–10 岁孩子的家长参加 co-design workshops。
- **结果 / 叙事**：提出 child support、parent support、parent-child interaction 三层框架；storytelling 脚手架最受认可。
- **局限 / 未来**：仅家长、概念设计、无儿童或部署；不是 AI 研究。
- **对 AI 伯乐**：让具体事件成为亲子共同反思对象，同时支持个体和关系层面。

#### CSCW-5 Supporting Communication and Well-being with a Multi-Stakeholder Mobile App（2025）

- **动机 / 问题**：如何支持 ADHD 儿童、照护者和治疗师沟通，同时避免过度披露。
- **系统 / 交互**：儿童选择是否分享、分享哪些部分、分享给谁；专业端按授权查看。
- **实验**：field study 加形成性迭代；当前公开证据未可靠核验 N、年龄、部署周期和量表，正式引用前需回查全文。
- **结果 / 叙事**：贡献聚焦跨角色沟通、儿童选择性披露和共同照护。
- **局限 / 未来**：临床特定群体，不能直接外推普通儿童；不宜据公开片段声称效果量。
- **对 AI 伯乐**：按证据片段和角色分享；儿童可预览、编辑、撤回，不同角色视图不必相同。

## 5. 五会偏好与项目适配

| 会议 | 最看重什么 | AI 伯乐需要强化什么 | 当前适配度 |
|---|---|---|---|
| **CHI** | 清晰的人本问题、理论/设计知识、严谨且与主张匹配的方法、多源证据、伦理和边界 | 把“可追溯、可争议的儿童能力反思”写成通用 HCI 问题；三方形成性研究加对照实验 | **最高，首选** |
| **IDC** | 儿童中心设计、发展适切性、儿童能动性、AI 素养、共设计和真实儿童体验 | 儿童如何理解、质疑、修改画像；儿童参与定义构念与展示方式 | **很高，最稳妥** |
| **CSCW** | 多方协作、关系与权力、协调工作、隐私治理、长期社会技术实践 | 儿童—家长—教师如何协商证据、权限、分歧和行动 | **中高，需重写主叙事** |
| **UIST** | 新交互能力/机制、完整原型、技术新颖性、机制隔离、基线与消融 | 聚焦一个交互技术：跨模块证据编排、可解释校准或儿童可争议画像界面 | **中等，需明显技术收束** |
| **UbiComp/IMWUT** | 自然环境长期部署、低负担感知、跨情境鲁棒性、系统+算法+field evidence | 2–4 周以上部署、跨儿童 LOPO、情境消融、缺失数据、隐私公平和构念验证 | **目前较低，中长期方向** |

官方标准也支持该判断：CHI 强调 originality、significance、validity、research quality 与清晰呈现；UIST 要求系统主张有实验/分析证据并整体评价；CSCW 明确要求系统贡献必须体现协作或社会计算；UbiComp 主轨通过 IMWUT，重点是泛在计算技术与其人类经验和社会影响。

## 6. 推荐研究问题与贡献声明

### 推荐研究问题

- **RQ1**：儿童、家长和教师如何理解由开放式活动产生的 AI 能力画像，其理解和关注点有何差异？
- **RQ2**：相较只给结论的画像，证据链接、带不确定性且可争议的画像是否减少过度概括并提高证据追溯与纠错质量？
- **RQ3**：儿童与家长如何使用“像我 / 不像我 / 不确定”、反例补充和局部撤回来协商画像？这些操作暴露出哪些设计张力？
- **可选 RQ4**：同一能力线索在多个任务中重复出现时，用户是否更愿意接受画像；这种接受是否来自真正理解而非自动化偏见？

### 推荐贡献声明

1. 一个面向儿童多情境活动的 **traceable and contestable ability reflection** 设计框架。
2. 一个把任务语义、提示强度、过程行为和原始片段连接到临时画像的可运行系统。
3. 一项儿童—家长研究，揭示证据呈现、不确定性和反驳机制如何影响理解、过度概括、能动性与家庭对话。
4. 关于儿童 AI 画像中来源、权限、分歧保留和非诊断表达的设计建议。

## 7. 可直接执行的实验模板

### 7.1 阶段 A：形成性研究

- **参与者**：8–12 名儿童、8–12 名家长、6–10 名教师/儿童教育专业人员；不必三者完全配对。
- **任务**：让参与者阅读 3–4 张真实但匿名的行为证据卡和一页画像；逐项 think-aloud，排序“可信/不可信/需要更多证据”，共同设计纠错、分享和不确定性表达。
- **材料**：故事修订、空间策略、观点采择、反思调整等不同构念与证据强度案例。
- **分析**：反思式主题分析；双人建码、讨论分歧；输出设计需求和威胁模型。

### 7.2 阶段 B：核心对照实验

推荐 **2×2 被试内设计**：

- 因素 A：仅结论画像 vs 证据链接画像。
- 因素 B：不可修改 vs 可质疑/补充/撤回。
- 使用四套预先固定的儿童案例，拉丁方平衡条件和案例，避免真实能力差异成为混淆。
- 家长主样本建议 N=32–48；若资源有限，先做 N=20–24 的机制验证并诚实定位为探索性研究。

**主要量化指标**：

- 证据追溯正确率：能否把结论连回正确行为片段。
- 过度概括率：是否把单一任务表现外推为稳定人格/能力。
- 错误检测率与纠错质量：识别故意植入的不充分或矛盾结论。
- 不确定性理解：能否区分“证据不足”和“能力较弱”。
- 校准：对正确和错误结论的信心是否匹配。
- 行动建议质量：由盲评者按具体性、证据相关性、非比较性、可执行性评分。
- 操作行为：查看原证据、提出反例、局部修改、撤回、保留分歧、耗时。

**次要体验指标**：感知能动性、信任校准、NASA-TLX、可用性、对儿童尊重感；不要把“信任越高”当目标。

**定性方法**：刺激回忆访谈，逐条问“哪里像/不像这个孩子”“什么证据会让你改主意”“谁应该有权改”。对分歧进行案例分析，不强制合并为唯一真相。

**统计建议**：二项结果用混合效应 logistic regression；评分/信心用线性混合模型或有序 logistic；条件为固定效应，参与者和案例为随机截距；报告效应量、置信区间和多重比较校正。预注册主要结果和排除标准。

### 7.3 阶段 C：真实儿童纵向研究

- **周期**：至少 2–4 周，每名儿童完成四模块中至少 3 个模块、每模块 2 次以上。
- **重点**：不是训练“识别天赋”的分类器，而是检验跨情境证据是否可理解、是否产生有价值的反思与对话。
- **验证**：跨儿童 LOPO；按模块和任务难度做情境消融；用教师观察、独立任务和儿童自述做构念三角验证。
- **伦理**：最小化原始数据；儿童可预览/拒绝/撤回；跨模块汇总逐次同意；家长补充不能覆盖儿童原话；高风险内容人工升级。

## 8. 可直接复用的研究缺口写法

### 中文版

> 现有儿童 AI 系统已能在故事创作、编程和对话学习中提供个性化脚手架，但其评估多聚焦于单次任务结果、投入或学习增益。较少研究考察：当系统跨多个开放式活动推断儿童能力线索时，如何让这些推断保持可追溯、表达不确定性，并允许儿童及照护者提出反例、修订或拒绝。缺少这些机制，流畅的 AI 总结可能把情境性行为固化为稳定标签，并遮蔽儿童、家长和教师之间有意义的分歧。为此，我们研究如何设计一种证据链接、可争议且非诊断的儿童能力反思系统。

### 英文版

> Prior child–AI systems have demonstrated the value of personalized scaffolding for storytelling, creative coding, and dialogic learning. However, evaluations have largely focused on task outcomes, engagement, or short-term learning gains. We know comparatively little about how AI-generated reflections should be designed when they aggregate behavioral traces across multiple open-ended activities: how their evidential basis can remain traceable, how uncertainty should be communicated, and how children and caregivers can contest, revise, or reject an inference. Without such mechanisms, fluent AI summaries risk turning situated behavior into stable labels while obscuring meaningful disagreements among children, caregivers, and educators. We therefore investigate the design of evidence-linked, contestable, and non-diagnostic ability reflections for young children.

## 9. 论文结构大纲

1. **Introduction**：儿童画像的吸引力与风险；现有工作聚焦任务成效而缺少可追溯和可争议机制；列出 RQ 与四项贡献。
2. **Related Work**：儿童与生成式 AI；过程证据与学习分析；可解释/可争议 AI；家庭与学校中的多方协商。
3. **Formative Study**：儿童、家长、教师对证据、标签、不确定性、权限的需求；形成设计目标。
4. **System**：四模块只作研究情境；重点描述证据模型、来源链接、不确定性、校准交互、权限和安全边界。
5. **Study Design**：条件、案例、参与者、随机化/平衡、任务、指标、定性与定量分析、伦理。
6. **Results**：先主要量化结果，再用分歧案例解释机制；负结果照实报告。
7. **Discussion**：可追溯性是否足够、何时增加认知负担；儿童能动性；家庭权力；跨情境推断边界；对其他儿童 AI 系统的设计知识。
8. **Limitations and Future Work**：小样本、短期、文化与语言、构念效度、LLM 漂移、非诊断边界、长期后果。
9. **Conclusion**：强调支持反思与协商，而非自动发现稳定天赋。

## 10. 投稿路线建议

### 首选路线：CHI

以“可追溯且可争议的儿童能力反思”为通用 HCI 问题。完成形成性三方研究、一个受控对照实验和有代表性的真实儿童案例；明确交互/实证/设计知识三类贡献。现有多模块平台是研究载体，不是贡献本身。

### 稳妥路线：IDC

把研究主角进一步还给儿童：儿童如何理解 AI 画像、如何表达“不像我”、如何撤回或改写、何种可视化适合低识字量儿童。减少成人判断效果的篇幅，加强儿童共设计、发展适切性和 AI 素养。

### 备选路线：CSCW

把单位从“一个孩子的画像”改成“家庭与学校如何协商一个可争议的儿童模型”。系统贡献围绕协调工作、权限、选择性披露、版本历史、分歧保留和跨角色行动。

### 暂不优先：UIST / UbiComp

UIST 只有在跨模块证据编排、校准或儿童可争议界面本身形成新的交互机制，并有机制隔离实验时才值得主投。UbiComp/IMWUT 需要长期自然部署、传感/日志算法、跨儿童鲁棒性和 field evidence，建议作为下一阶段论文。

## 11. 参考文献（APA 7，精选正式链接）

Arakawa, R., Ahuja, K., Mak, K., Thompson, G., Shaaban, S., Lindhiem, O., & Goel, M. (2023). LemurDx: Using unconstrained passive sensing for an objective measurement of hyperactivity in children with no parent input. *Proceedings of the ACM on Interactive, Mobile, Wearable and Ubiquitous Technologies, 7*(2). https://doi.org/10.1145/3596244

Belz, J. H., Weilke, L. M., Winter, A., Hallgarten, P., Rukzio, E., & Grosse-Puppendahl, T. (2024). Story-driven: Real-time context-synchronized storytelling in mobile environments. *Proceedings of UIST 2024*. https://doi.org/10.1145/3654777.3676372

Chen, L., Xiao, S., Chen, Y., Wu, R., Song, Y., & Sun, L. (2024). ChatScratch: An AI-augmented system toward autonomous visual programming learning for children aged 6–12. *Proceedings of CHI 2024*. https://doi.org/10.1145/3613904.3642229

Cheng, A. Y., et al. (2024). Scientific and fantastical: Creating immersive, culturally-relevant learning experiences with augmented reality and large language models. *Proceedings of CHI 2024*. https://doi.org/10.1145/3613904.3642041

Cheng, A. Y., et al. (2025). Oak Story: Improving learner outcomes with LLM-mediated interactive narratives. *Proceedings of UIST 2025*. https://doi.org/10.1145/3746059.3747698

Dangol, A., et al. (2025). Children’s mental models of AI reasoning: Implications for AI literacy education. *Proceedings of IDC 2025*. https://doi.org/10.1145/3713043.3728856

Druga, S., et al. (2025). Scratch Copilot: Supporting youth creative coding with AI. *Proceedings of IDC 2025*. https://arxiv.org/abs/2505.03867

Dumaru, P., Atashpanjeh, H., & Al-Ameen, M. N. (2024). “It’s hard for him to make choices sometimes and he needs guidance”: Re-orienting parental control for children. *Proceedings of the ACM on Human-Computer Interaction, 8*(CSCW1). https://doi.org/10.1145/3637359

Dwivedi, U., Elsayed-Ali, S., Bonsignore, E., & Kacorri, H. (2024). Exploring AI problem formulation with children via teachable machines. *Proceedings of CHI 2024*. https://doi.org/10.1145/3613904.3642692

Fan, M., Cui, X., Ma, W., Li, H., Tong, X., Yang, L., & Wang, Y. (2025). From words to wonder: Designing and evaluating an AI-empowered creative storytelling system for elementary children. *Proceedings of CHI 2025*. https://doi.org/10.1145/3706598.3713478

Han, A., et al. (2024). Teachers, parents, and students’ perspectives on integrating generative AI into elementary literacy education. *Proceedings of CHI 2024*. https://doi.org/10.1145/3613904.3642438

He, K., et al. (2025). StoryPal: Supporting young children’s dialogic reading with large language models. *Proceedings of IDC 2025*. https://doi.org/10.1145/3713043.3728867

Hong, T. L., et al. (2026). Children envision future GenAI chatbots that are bounded, helpful, and safe. *Proceedings of IDC 2026*. https://doi.org/10.1145/3773077.3806128

Lyu, Y., et al. (2023). Eggly: Designing mobile augmented reality neurofeedback training games for children with autism spectrum disorder. *Proceedings of the ACM on Interactive, Mobile, Wearable and Ubiquitous Technologies, 7*. https://doi.org/10.1145/3596251

Oh, S., et al. (2025). Hey Curio, can you tell me more?: Children’s information-seeking and trust in AI. *Proceedings of IDC 2025*. https://doi.org/10.1145/3713043.3727059

Peng, Z., Wang, X., Han, Q., Zhu, J., Ma, X., & Qu, H. (2023). Storyfier: Exploring vocabulary learning support with text generation models. *Proceedings of UIST 2023*. https://doi.org/10.1145/3586183.3606786

Qi, X., et al. (2023). CASES: A cognition-aware smart eyewear system for understanding how people read. *Proceedings of the ACM on Interactive, Mobile, Wearable and Ubiquitous Technologies, 7*(3). https://doi.org/10.1145/3610910

Seo, W., et al. (2025). Enhancing pediatric communication: The role of an AI-driven chatbot in facilitating child-parent-provider interaction. *Proceedings of CHI 2025*. https://doi.org/10.1145/3706598.3713134

Stefanidi, E., et al. (2025). Supporting communication and well-being with a multi-stakeholder mobile app: Lessons learned from a field study with ADHD children and their caregivers. *Proceedings of the ACM on Human-Computer Interaction, 9*(2). https://doi.org/10.1145/3711075

Sun, Y., et al. (2024). Exploring parent’s needs for children-centered AI to support preschoolers’ interactive storytelling and reading activities. *Proceedings of the ACM on Human-Computer Interaction, 8*(CSCW2). https://doi.org/10.1145/3687035

Tang, X., et al. (2024). VizGroup: An AI-assisted event-driven system for real-time collaborative programming learning analytics. *Proceedings of UIST 2024*. https://doi.org/10.1145/3654777.3676347

Theofanopoulou, N., Antle, A. N., & Slovak, P. (2024). “They don’t come with a handbook”: Exploring design opportunities for supporting parent-child interaction around emotions in the family context. *Proceedings of the ACM on Human-Computer Interaction, 8*(CSCW1). https://doi.org/10.1145/3637409

Voysey, I., et al. (2026). Agency in child–AI interaction: A review of how it is conceptualised, studied, and supported in HCI. *Proceedings of IDC 2026*. https://doi.org/10.1145/3773077.3806105

Wang, Z., et al. (2025). CharacterCritique: Supporting children’s development of critical thinking through multi-agent interaction in story reading. *Proceedings of CHI 2025*. https://doi.org/10.1145/3706598.3713602

Wen, Z., Liu, L., & Yao, Y. (2025). Families’ vision of generative AI agents for household safety against digital and physical threats. *Proceedings of the ACM on Human-Computer Interaction, 9*(7). https://doi.org/10.1145/3757598

Zhu, R., Shi, L., Song, Y., & Cai, Z. (2023). Integrating gaze and mouse via joint cross-attention fusion net for students’ activity recognition in e-learning. *Proceedings of the ACM on Interactive, Mobile, Wearable and Ubiquitous Technologies, 7*(3). https://doi.org/10.1145/3610876

Zhang, C., Liu, X., Ziska, K., Jeon, S., Yu, C.-L., & Xu, Y. (2024). Mathemyths: Leveraging large language models to teach mathematical language through child-AI co-creative storytelling. *Proceedings of CHI 2024*. https://doi.org/10.1145/3613904.3642647

## 12. 提交前必须补做的核验

- 从正式 PDF 补齐 From Words to Wonder 的分组人数和统计量。
- 从正式 PDF 补齐 Children’s Mental Models of AI Reasoning 的任务、量表和统计细节。
- 从正式 PDF 补齐 CSCW 多利益相关者 ADHD app 的 N、年龄、周期和量表。
- 对全部儿童研究登记伦理审批、监护人同意和儿童 assent 流程。
- 将“六类/八类智能”从理论真值降为界面组织方式；主论文采用可观察构念注册表。
- 在真实投稿版本中增加完整检索日志、去重清单和排除理由。
