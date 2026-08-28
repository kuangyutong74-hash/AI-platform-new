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
    island: "想象之洲",
    collection: "故事高光奖章",
    short: "参与最完整、最值得回看的一次故事",
    scene: "/assets/collections/works/highlight-story-sticker-v1.webp",
    milestoneImage: "/assets/collections/growth/story-island-720.webp",
    tone: "rose",
  },
  deep_sea: {
    key: "deep_sea",
    island: "创造之洲",
    collection: "深海高光奖章",
    short: "完成最完整、最值得回看的一次重建",
    scene: "/assets/collections/works/highlight-ocean-sticker-v1.webp",
    milestoneImage: "/assets/collections/growth/ocean-island-720.webp",
    tone: "blue",
  },
  career: {
    key: "career",
    island: "未来之洲",
    collection: "职业高光奖章",
    short: "最投入的一次角色体验",
    scene: "/assets/collections/works/highlight-career-sticker-v1.webp",
    milestoneImage: "/assets/collections/growth/future-island-720.webp",
    tone: "amber",
  },
  chat: {
    key: "chat",
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
  })),
];

function cleanText(value, fallback = "") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function normalizeModule(value) {
  if (value === "sea" || value === "build") return "deep_sea";
  return MODULE_META[value] ? value : "chat";
}

function normalizeItem(item, index, kind) {
  const moduleKey = normalizeModule(item?.module);
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
    island: meta.island,
    collection: meta.collection,
    scene: meta.scene,
    milestoneImage: meta.milestoneImage,
    tone: meta.tone,
    isHighlight: item?.is_highlight === true || item?.isHighlight === true || itemKind === "highlight",
    snapshotUrl: cleanText(item?.snapshot_url ?? item?.snapshotUrl),
    comments: Array.isArray(item?.comments) ? item.comments.map((comment, commentIndex) => ({
      id: cleanText(comment?.id, `comment-${index}-${commentIndex}`),
      body: cleanText(comment?.body),
      authorName: cleanText(comment?.author_name ?? comment?.authorName, "老师 / 家长"),
      authorKind: cleanText(comment?.author_kind ?? comment?.authorKind),
      createdAt: cleanText(comment?.created_at ?? comment?.createdAt),
    })).filter(comment => comment.body) : [],
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
  return {
    account: {displayName, age, createdAt},
    works,
    milestones,
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
    ? payload.works.map((item, index) => normalizeItem(item, index, "work"))
    : [];
  const realMilestones = Array.isArray(payload?.milestones)
    ? payload.milestones.map((item, index) => normalizeItem(item, index, "milestone"))
    : [];
  const demo = createDemoCollection(account);
  const worksAreDemo = realWorks.length === 0;
  const timelineIsDemo = realMilestones.length === 0;
  const works = worksAreDemo ? demo.works : realWorks;
  const milestones = timelineIsDemo ? demo.milestones : realMilestones;
  const worksNotice = worksAreDemo
    ? "还没有足够的真实高光记录，这里先展示示例奖章。完成探索后，会自动换成你的代表性高光。"
    : "每座大陆只保留一枚真实高光：表达最充分、参与最完整或过程最值得回看的一次。";
  const timelineNotice = timelineIsDemo
    ? "还没有收到账号使用历程，这里先展示清楚标注的示例。"
    : "这条星路从注册日开始，记录四个模块的首次完成、最近完成和累计次数。";
  return {
    account,
    works,
    milestones,
    isDemo: worksAreDemo && timelineIsDemo,
    worksAreDemo,
    timelineIsDemo,
    worksNotice,
    timelineNotice,
    notice: worksNotice,
  };
}
