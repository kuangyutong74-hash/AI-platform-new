export const MODULE_META = {
  registration: {
    key: "registration",
    island: "星光起点",
    collection: "加入探索星球",
    short: "我的第一颗星",
    scene: "/assets/collections/growth/starlight-camp-720.webp",
    milestoneImage: "/assets/collections/growth/starlight-camp-720.webp",
    tone: "amber",
  },
  story: {
    key: "story",
    name: "故事共创",
    island: "想象之洲",
    collection: "故事高光奖章",
    short: "参与最完整、最值得回看的一次故事",
    scene: "/assets/collections/works/highlight-story-sticker-v1.webp",
    milestoneImage: "/assets/collections/growth/story-island-720.webp",
    tone: "rose",
  },
  deep_sea: {
    key: "deep_sea",
    name: "深海基地重建",
    island: "创造之洲",
    collection: "深海高光奖章",
    short: "完成最完整、最值得回看的一次重建",
    scene: "/assets/collections/works/highlight-ocean-sticker-v1.webp",
    milestoneImage: "/assets/collections/growth/ocean-island-720.webp",
    tone: "blue",
  },
  career: {
    key: "career",
    name: "职业模拟器",
    island: "未来之洲",
    collection: "职业高光奖章",
    short: "最投入的一次角色体验",
    scene: "/assets/collections/works/highlight-career-sticker-v1.webp",
    milestoneImage: "/assets/collections/growth/future-island-720.webp",
    tone: "amber",
  },
  chat: {
    key: "chat",
    name: "聊天观察",
    island: "倾听之洲",
    collection: "表达高光奖章",
    short: "最充分表达的一次对话",
    scene: "/assets/collections/works/highlight-listening-sticker-v1.webp",
    milestoneImage: "/assets/collections/growth/listening-cloud-720.webp",
    tone: "mint",
  },
};

const DEMO_HIGHLIGHTS = [
  {
    id: "demo-story-highlight",
    module: "story",
    kind: "highlight",
    title: "会发光的雨伞",
    summary: "四篇故事里，这一篇参与得最完整，也把害怕慢慢变成了勇敢。",
    quote: "别怕，我们一起走，雨里也会有亮晶晶的路。",
    detail: "这是故事高光示例。真实数据接入后，会从你完成的故事中选择内容最完整、最值得回看的那一篇。",
    occurredAt: "2026-08-18T08:00:00+08:00",
    status: "完整创作高光",
    metricLabel: "创作记录",
    metricValue: "8 轮共创 · 结尾 86 字",
    usageCount: 4,
  },
  {
    id: "demo-sea-highlight",
    module: "deep_sea",
    kind: "highlight",
    title: "深海基地完整重建",
    summary: "这一次完成了三处基地任务，还根据检查结果认真调整了设计。",
    quote: "先给小鱼留安全通道，再把共享花园放在中间。",
    detail: "这是深海高光示例。真实记录会优先展示完成最完整、过程最值得回看的基地重建。",
    occurredAt: "2026-08-16T08:00:00+08:00",
    status: "完整重建高光",
    metricLabel: "重建记录",
    metricValue: "完成 3 个任务 · 调整 5 次",
    usageCount: 6,
  },
  {
    id: "demo-career-highlight",
    module: "career",
    kind: "highlight",
    title: "最投入的小医生体验",
    summary: "完整做完六个关键选择，还记得先听清楚对方哪里不舒服。",
    quote: "先认真听一听，再想最合适的办法。",
    detail: "这是职业高光示例。真实记录会挑选完成度最高、关键选择最丰富的一次职业体验。",
    occurredAt: "2026-08-14T08:00:00+08:00",
    status: "最投入体验高光",
    metricLabel: "体验记录",
    metricValue: "完成 6 个关键选择",
    usageCount: 3,
  },
  {
    id: "demo-chat-highlight",
    module: "chat",
    kind: "highlight",
    title: "把雨天的心情说出来",
    summary: "这次对话说得最充分，从灰灰的心情一直聊到重新看见一点太阳。",
    quote: "原来心情也会像天气一样变化。",
    detail: "这是表达高光示例。真实记录会选择交流轮次较完整、表达内容较丰富的一次对话。",
    occurredAt: "2026-08-12T08:00:00+08:00",
    status: "最充分表达高光",
    metricLabel: "表达记录",
    metricValue: "12 轮对话",
    usageCount: 8,
  },
];

const DEMO_TIMELINE = [
  {
    id: "demo-registration",
    module: "registration",
    kind: "registration",
    title: "来到探索星球",
    summary: "这是第一颗星，也是所有探索故事的起点。",
    detail: "从注册这一天开始，四座大陆会把每一次完成的小脚印慢慢送到这里。",
    quote: "从今天起，出发去发现自己的闪光点。",
    occurredAt: "2026-08-01T08:00:00+08:00",
    status: "星光起点",
    metricLabel: "加入时间",
    metricValue: "第一次出发",
    usageCount: 0,
  },
  ...DEMO_HIGHLIGHTS.map((item, index) => ({
    ...item,
    id: `demo-summary-${item.module}`,
    kind: "module_summary",
    title: `${MODULE_META[item.module].island}的完成小结`,
    summary: `从第一次完成到最近一次，一共留下 ${item.usageCount} 个示例脚印。`,
    detail: `这是模块完成小结示例。真实页面会显示首次完成、最近完成、累计次数${index < 2 ? "和可获得的累计时长" : ""}。`,
    status: "模块已点亮",
    metricLabel: "累计完成",
    metricValue: `${item.usageCount} 次探索${index === 0 ? " · 累计 38分钟" : ""}`,
    evidenceCount: [12, 9, 8, 14][index],
    artifactCount: 1,
    observations: {
      story: ["愿意连续补充情节，让故事从开头走到结尾。", "遇到不满意的表达时，会换一种说法继续创作。"],
      deep_sea: ["会根据检查结果回头定位问题，再调整原来的方案。", "在生态配对、线路布局和角色协商中使用了不同办法。"],
      career: ["能够跟着职业情境完成连续任务，并说明自己的选择。", "获得新信息后，愿意重新比较并调整做法。"],
      chat: ["愿意把感受和原因说得更具体，让对话继续展开。", "能回应追问，也会补充生活里的真实例子。"],
    }[item.module],
    recentSessions: [0, 1, 2].slice(0, Math.min(3, item.usageCount)).map((offset) => ({
      id: `demo-${item.module}-session-${offset}`,
      occurredAt: new Date(new Date(item.occurredAt).getTime() - offset * 4 * 86400000).toISOString(),
      durationSeconds: item.module === "story" ? 760 + offset * 110 : 480 + offset * 80,
      caption: {
        story: offset === 0 ? "完成一次完整故事共创，并为结尾补充了自己的想法" : "从一个新点子出发，把故事继续讲了下去",
        deep_sea: offset === 0 ? "完成三处基地任务，并根据检查结果调整方案" : "尝试生态配对与线路布局，留下解决问题的过程",
        career: offset === 0 ? "完成小医生的一天，在关键选择后说明了理由" : "体验一个新的职业情境，完成连续任务",
        chat: offset === 0 ? "围绕雨天的心情完成一次连续对话" : "从生活小事出发，把感受慢慢说清楚",
      }[item.module],
    })),
  })),
];

function cleanText(value, fallback = "") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

const MODULE_ALIASES = {
  story: "story",
  storytelling: "story",
  deep_sea: "deep_sea",
  "deep-sea": "deep_sea",
  sea: "deep_sea",
  build: "deep_sea",
  career: "career",
  chat: "chat",
};

export function canonicalExplorerModule(value, {allowRegistration = false} = {}) {
  const key = typeof value === "string" ? value.trim().toLowerCase() : "";
  if (allowRegistration && key === "registration") return "registration";
  return Object.prototype.hasOwnProperty.call(MODULE_ALIASES, key) ? MODULE_ALIASES[key] : null;
}

export function explorerModuleName(value) {
  const key = canonicalExplorerModule(value);
  return key ? MODULE_META[key].name : "探索模块";
}

function fallbackHighlightReason(item, moduleKey) {
  const title = cleanText(item?.title, `${MODULE_META[moduleKey].island}的作品`);
  const metric = cleanText(item?.metric_value ?? item?.metricValue);
  const reasons = {
    story: `《${title}》记录了从想法到完成作品的创作过程${metric ? `，并留下了“${metric}”的完成记录` : ""}，因此被收藏为本次故事高光。`,
    deep_sea: `这件作品记录了《${title}》中完成任务和调整方案的过程${metric ? `，对应“${metric}”` : ""}，因此被收藏为本次重建高光。`,
    career: `《${title}》保留了完整参与职业任务的过程${metric ? `，对应“${metric}”` : ""}，因此被收藏为本次体验高光。`,
    chat: `《${title}》留下了连续、可回看的真实表达${metric ? `，对应“${metric}”` : ""}，因此被收藏为本次聊天高光。`,
  };
  return reasons[moduleKey] ?? "这条记录保留了可回看的探索过程。";
}

function normalizeItem(item, index, kind) {
  const moduleKey = canonicalExplorerModule(item?.module, {allowRegistration: true}) ?? "registration";
  const meta = MODULE_META[moduleKey];
  const summary = cleanText(item?.summary, "这里收着一次认真尝试。");
  const itemKind = cleanText(item?.kind, kind === "work" ? "highlight" : "module_summary");
  return {
    id: cleanText(item?.id, `${kind}-${moduleKey}-${index}`),
    module: moduleKey,
    kind: itemKind,
    title: cleanText(item?.title, `${meta.island}的新发现`),
    summary,
    detail: cleanText(item?.detail, summary),
    highlightReason: cleanText(item?.highlight_reason ?? item?.highlightReason, fallbackHighlightReason(item, moduleKey)),
    quote: cleanText(item?.quote),
    occurredAt: cleanText(item?.occurred_at ?? item?.occurredAt, new Date(0).toISOString()),
    status: cleanText(item?.status, itemKind === "highlight" ? "高光已收藏" : "模块已点亮"),
    unlocked: item?.unlocked !== false,
    metricLabel: cleanText(item?.metric_label ?? item?.metricLabel, itemKind === "highlight" ? "高光记录" : "累计完成"),
    metricValue: cleanText(item?.metric_value ?? item?.metricValue, itemKind === "registration" ? "第一次出发" : "1 次探索"),
    usageCount: Number(item?.usage_count ?? item?.usageCount) || 0,
    firstUsedAt: cleanText(item?.first_used_at ?? item?.firstUsedAt),
    lastUsedAt: cleanText(item?.last_used_at ?? item?.lastUsedAt),
    durationSeconds: Number(item?.duration_seconds ?? item?.durationSeconds) || 0,
    durationCoverage: Math.max(0, Math.min(1, Number(item?.duration_coverage ?? item?.durationCoverage) || 0)),
    evidenceCount: Number(item?.evidence_count ?? item?.evidenceCount) || 0,
    artifactCount: Number(item?.artifact_count ?? item?.artifactCount) || 0,
    observations: Array.isArray(item?.observations)
      ? item.observations.map(value => cleanText(value)).filter(Boolean).slice(0, 3)
      : [],
    recentSessions: Array.isArray(item?.recent_sessions ?? item?.recentSessions)
      ? (item.recent_sessions ?? item.recentSessions).map((session, sessionIndex) => ({
          id: cleanText(session?.id, `${moduleKey}-session-${sessionIndex}`),
          occurredAt: cleanText(session?.occurred_at ?? session?.occurredAt),
          durationSeconds: Number(session?.duration_seconds ?? session?.durationSeconds) || 0,
          caption: cleanText(session?.caption, `完成一次${meta.name || "探索"}`),
        })).slice(0, 3)
      : [],
    island: meta.island,
    collection: meta.collection,
    scene: meta.scene,
    milestoneImage: meta.milestoneImage,
    tone: meta.tone,
    isHighlight: item?.is_highlight === true || item?.isHighlight === true || itemKind === "highlight",
    snapshotUrl: cleanText(item?.snapshot_url ?? item?.snapshotUrl),
    sourceResourceId: cleanText(item?.source_resource_id ?? item?.sourceResourceId),
    sourceSessionId: cleanText(item?.source_session_id ?? item?.sourceSessionId),
    comments: Array.isArray(item?.comments) ? item.comments.map((comment, commentIndex) => ({
      id: cleanText(comment?.id, `comment-${index}-${commentIndex}`),
      body: cleanText(comment?.body),
      authorName: cleanText(comment?.author_name ?? comment?.authorName, "老师 / 家长"),
      authorKind: cleanText(comment?.author_kind ?? comment?.authorKind),
      createdAt: cleanText(comment?.created_at ?? comment?.createdAt),
    })).filter(comment => comment.body) : [],
  };
}

function normalizeGrowthSession(session, index) {
  const moduleKey = canonicalExplorerModule(session?.module ?? session?.moduleId);
  if (!moduleKey) return null;
  return {
    id: cleanText(session?.id, `growth-session-${index}`),
    module: moduleKey,
    occurredAt: cleanText(session?.occurred_at ?? session?.occurredAt),
    durationSeconds: Number(session?.duration_seconds ?? session?.durationSeconds) || 0,
    caption: cleanText(session?.caption, `完成一次${MODULE_META[moduleKey].name}探索`),
    evidenceCount: Number(session?.evidence_count ?? session?.evidenceCount) || 0,
    artifactCount: Number(session?.artifact_count ?? session?.artifactCount) || 0,
    observations: Array.isArray(session?.observations)
      ? session.observations.map(value => cleanText(value)).filter(Boolean).slice(0, 3)
      : [],
  };
}

function normalizeGrowthOverview(value = {}) {
  const sessions = Array.isArray(value?.sessions)
    ? value.sessions.map(normalizeGrowthSession).filter(Boolean)
    : [];
  const todaySessions = Array.isArray(value?.today_sessions ?? value?.todaySessions)
    ? (value.today_sessions ?? value.todaySessions).map(normalizeGrowthSession).filter(Boolean)
    : [];
  const longTermSignals = Array.isArray(value?.long_term_signals ?? value?.longTermSignals)
    ? (value.long_term_signals ?? value.longTermSignals).map((signal, index) => ({
        key: cleanText(signal?.key, `growth-signal-${index}`),
        label: cleanText(signal?.label, "成长线索"),
        evidenceCount: Number(signal?.evidence_count ?? signal?.evidenceCount) || 0,
        moduleCount: Number(signal?.module_count ?? signal?.moduleCount) || 0,
        modules: Array.isArray(signal?.modules)
          ? signal.modules.map(module => canonicalExplorerModule(module)).filter(Boolean)
          : [],
        firstSeenAt: cleanText(signal?.first_seen_at ?? signal?.firstSeenAt),
        lastSeenAt: cleanText(signal?.last_seen_at ?? signal?.lastSeenAt),
        observation: cleanText(signal?.observation, "这条线索正在从多次探索中慢慢积累。"),
        status: cleanText(signal?.status, "正在积累"),
      })).slice(0, 6)
    : [];
  return {
    sessions,
    todaySessions,
    todayCompletedCount: Number(value?.today_completed_count ?? value?.todayCompletedCount) || 0,
    todayDurationSeconds: Number(value?.today_duration_seconds ?? value?.todayDurationSeconds) || 0,
    todayEvidenceCount: Number(value?.today_evidence_count ?? value?.todayEvidenceCount) || 0,
    todayModules: Array.isArray(value?.today_modules ?? value?.todayModules)
      ? (value.today_modules ?? value.todayModules).map(module => canonicalExplorerModule(module)).filter(Boolean)
      : [],
    totalCompletedCount: Number(value?.total_completed_count ?? value?.totalCompletedCount) || sessions.length,
    totalDurationSeconds: Number(value?.total_duration_seconds ?? value?.totalDurationSeconds) || 0,
    activeDays: Number(value?.active_days ?? value?.activeDays) || 0,
    exploredModuleCount: Number(value?.explored_module_count ?? value?.exploredModuleCount) || 0,
    firstCompletedAt: cleanText(value?.first_completed_at ?? value?.firstCompletedAt),
    lastCompletedAt: cleanText(value?.last_completed_at ?? value?.lastCompletedAt),
    longTermSignals,
  };
}

export function createDemoCollection(account = {}) {
  const displayName = cleanText(account.displayName ?? account.display_name, "小小探索家");
  const age = Number(account.age) || 8;
  const createdAt = cleanText(account.createdAt ?? account.created_at, DEMO_TIMELINE[0].occurredAt);
  const works = DEMO_HIGHLIGHTS.map((item, index) => normalizeItem(item, index, "work"));
  const milestones = DEMO_TIMELINE.map((item, index) => normalizeItem(
    index === 0 ? {...item, title: `${displayName}来到探索星球`, occurredAt: createdAt} : item,
    index,
    "milestone",
  ));
  const now = new Date();
  const demoSessions = milestones
    .filter(item => item.module !== "registration")
    .flatMap(item => item.recentSessions.map(session => ({...session, module: item.module})))
    .map((session, index) => index < 2
      ? {...session, occurredAt: new Date(now.getTime() - (index + 1) * 3600000).toISOString()}
      : session);
  const todaySessions = demoSessions.slice(0, 2);
  const growthOverview = normalizeGrowthOverview({
    sessions: demoSessions,
    todaySessions,
    todayCompletedCount: todaySessions.length,
    todayDurationSeconds: todaySessions.reduce((sum, item) => sum + item.durationSeconds, 0),
    todayEvidenceCount: 5,
    todayModules: todaySessions.map(item => item.module),
    totalCompletedCount: demoSessions.length,
    totalDurationSeconds: demoSessions.reduce((sum, item) => sum + item.durationSeconds, 0),
    activeDays: 8,
    exploredModuleCount: 4,
    firstCompletedAt: milestones[1]?.firstUsedAt || milestones[1]?.occurredAt,
    lastCompletedAt: todaySessions[0]?.occurredAt,
    longTermSignals: [
      {key:"problem_solving.planning",label:"规划",evidenceCount:6,moduleCount:2,modules:["deep_sea","career"],firstSeenAt:milestones[2]?.occurredAt,lastSeenAt:todaySessions[0]?.occurredAt,observation:"在基地重建和职业任务中，都能先想办法再行动。",status:"跨情境出现"},
      {key:"creativity.narrative_expression",label:"叙事表达",evidenceCount:4,moduleCount:1,modules:["story"],firstSeenAt:milestones[1]?.occurredAt,lastSeenAt:todaySessions[0]?.occurredAt,observation:"多次继续补充情节，让故事从想法走向完整。",status:"反复出现"},
      {key:"self_reflection.interest_expression",label:"兴趣表达",evidenceCount:3,moduleCount:1,modules:["chat"],firstSeenAt:milestones[4]?.occurredAt,lastSeenAt:milestones[4]?.occurredAt,observation:"愿意说出喜欢什么，也会补充自己的原因。",status:"反复出现"},
    ],
  });
  return {
    account: {displayName, age, createdAt},
    works,
    milestones,
    growthOverview,
    isDemo: true,
    worksAreDemo: true,
    timelineIsDemo: true,
    worksNotice: "还没有足够的真实高光记录，这里先展示四枚示例奖章。完成探索后，会自动换成你的代表性高光。",
    timelineNotice: "这里先展示一份使用历程示例。真实记录会从你的注册日开始。",
    notice: "当前展示的是清楚标注的示例内容。",
  };
}

export function normalizeCollectionResponse(payload) {
  const account = {
    displayName: cleanText(payload?.account?.display_name ?? payload?.account?.displayName, "小小探索家"),
    age: Number(payload?.account?.age) || 8,
    createdAt: cleanText(payload?.account?.created_at ?? payload?.account?.createdAt),
  };
  const realWorks = Array.isArray(payload?.works)
    ? payload.works
      .filter(item => canonicalExplorerModule(item?.module))
      .map((item, index) => normalizeItem(item, index, "work"))
    : [];
  const realMilestones = Array.isArray(payload?.milestones)
    ? payload.milestones
      .filter(item => canonicalExplorerModule(item?.module, {allowRegistration: true}))
      .map((item, index) => normalizeItem(item, index, "milestone"))
    : [];
  const demo = createDemoCollection(account);
  const worksAreDemo = realWorks.length === 0;
  const timelineIsDemo = realMilestones.length === 0;
  const works = worksAreDemo ? demo.works : realWorks;
  const milestones = timelineIsDemo ? demo.milestones : realMilestones;
  const growthOverview = timelineIsDemo
    ? demo.growthOverview
    : normalizeGrowthOverview(payload?.growth_overview ?? payload?.growthOverview);
  const worksNotice = worksAreDemo
    ? "还没有作品，这里先展示四座大陆的示例。你可以自行探索，也可以自己添加第一件作品。"
    : "这里展示着探索星球时留下的作品，也珍藏着学生自己添加的创作。";
  const timelineNotice = timelineIsDemo
    ? "还没有收到账号使用历程，这里先展示清楚标注的示例。"
    : "这条星路从注册日开始，按真实会话整理完成节奏、过程观察和可继续尝试的方向。";
  return {
    account,
    works,
    milestones,
    growthOverview,
    isDemo: worksAreDemo && timelineIsDemo,
    worksAreDemo,
    timelineIsDemo,
    worksNotice,
    timelineNotice,
    notice: worksNotice,
  };
}
