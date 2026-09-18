/**
 * 顺序阅读版（家长报告）的证据清洗与摘要规则。
 *
 * 这里集中处理三个会导致家长端“大面积重复 / 无证据”的问题：
 * 1. 语音识别把中文逐词切开、聊天入口提示被回填成“孩子的原话”，
 *    这些内容必须先还原再判断，不能直接当作行为证据；
 * 2. 同一条记录会出现在多个维度，同一段话也会在多次体验里重复，
 *    需要归一化后去重并合并近似内容；
 * 3. 卡片正文写不出具体内容时返回空串，由调用方过滤掉，
 *    绝不用一句通用文案顶上。
 */
import type { CoreEvidenceRecord } from "../api/core";
import type { Evidence } from "../data/mockReport";

export const DEEP_SEA_LEVEL_NAMES: Record<number, string> = { 1: "珊瑚公寓", 2: "洋流电网", 3: "海洋议事厅" };
export const CAREER_NAMES: Record<string, string> = { doctor: "社区医生", firefighter: "消防员", teacher: "小学教师", chef: "餐厅厨师", journalist: "报社记者", animal_caretaker: "动物保护员" };
export const CAREER_STAGE_TITLES: Record<string, string[]> = {
  doctor: ["开诊台准备", "病人分诊", "问诊检查"], firefighter: ["装备柜点检", "接警出动", "现场救援路径规划"],
  teacher: ["布置晨间教室", "课堂管理", "和朵朵聊一聊"], chef: ["后厨开档", "午餐炒饭流程", "出餐高峰应对"],
  journalist: ["编辑部线索墙", "组织报道线索", "采访调查"], animal_caretaker: ["晨间巡护打卡", "动物救助优先级", "动物健康检查"],
};

const CJK_SPACE = /(?<=[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef])\s+(?=[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef])/g;
const ECHO_EXACT = new Set(["今天最想记住的事", "我的新发现", "兴趣爱好", "朋友相处", "今天最开心的事", "今天最难过的事", "最近发生的事", "说说你的发现"]);
const ECHO_PREFIX = /^(今天最想|今天最|最近最想|最近最|说说你|你最喜欢|你最近|如果让你|请你说)/;
const FILLER_WORDS = /我|你|他|她|它|的|了|是|在|和|都|很|就|也|不|这|那|一|个|有|会|要|可以|什么|怎么|今天|最近|一起|我们|他们|自己|时候|事情|东西|然后|还有|就是|其实|真的|喜欢|觉得/g;
const PEOPLE_WORDS = ["同学", "朋友", "老师", "爸爸", "妈妈", "家人", "伙伴", "同伴", "队友", "对方", "别人", "大家", "他们", "她们"];

export function cleanWords(value: unknown): string {
  let text = String(value ?? "").replace(/\s*\n+\s*/g, "").replace(/\u3000/g, " ").trim();
  if (!text) return "";
  let previous = "";
  while (previous !== text) { previous = text; text = text.replace(CJK_SPACE, ""); }
  return text
    .replace(/\s*([，。！？；：、,.!?;:])\s*/g, "$1")
    .replace(/^[的了地得是就在和]\s*[，,、]?\s*/, "")
    .trim();
}

/** 过短的碎片、话题词回填和入口提示语都只说明“点开过聊天”，不算表达证据。 */
export function isMeaningful(words: unknown, topic = ""): boolean {
  const cleaned = cleanWords(words);
  if (!cleaned) return false;
  if (ECHO_EXACT.has(cleaned) || ECHO_PREFIX.test(cleaned)) return false;
  const cleanedTopic = cleanWords(topic);
  if (cleanedTopic && cleaned === cleanedTopic) return false;
  if (cleaned.length < 6) return false;
  return cleaned.replace(FILLER_WORDS, "").length >= 3;
}

/** 按句读截断，绝不留下半句话或未闭合的引号。 */
export function clip(value: unknown, limit: number): string {
  const text = String(value ?? "").replace(/\s*\n+\s*/g, "").trim();
  if (text.length <= limit) return text;
  let window = text.slice(0, limit);
  let cut = false;
  for (const pattern of [/[。！？!?]/g, /[；;]/g, /[，,]/g]) {
    const matches = [...window.matchAll(pattern)];
    const last = matches.length ? matches[matches.length - 1] : null;
    if (last) {
      const end = (last.index ?? 0) + last[0].length;
      if (end >= Math.max(10, Math.floor(limit / 3))) { window = window.slice(0, end); cut = true; break; }
    }
  }
  if (!cut) window = `${window.replace(/[，。；：、,.!?;:]+$/, "")}…`;
  if ((window.match(/“/g)?.length || 0) > (window.match(/”/g)?.length || 0)) {
    const opening = window.lastIndexOf("“");
    window = opening >= 10 ? `${window.slice(0, opening).replace(/[，。；：、]+$/, "")}…` : window.replace(/“/g, "");
  }
  return window;
}

export function clipPhrase(value: unknown, limit: number): string {
  return clip(value, limit).replace(/[，、；：。]+$/, "").trim();
}

/**
 * 把孩子原话包成引语。原话本身可能已经带引号（例如“我想从“一个从没去过
 * 的地方”开始”），外层再用“”就会出现读不通的嵌套，这时改用「」。
 */
export function quoteChild(value: unknown): string {
  const text = String(value ?? "").trim();
  if (!text) return "";
  return /[“”"]/.test(text) ? `「${text}」` : `“${text}”`;
}

export function mentionedPeople(words: string): string[] {
  return PEOPLE_WORDS.filter(name => words.includes(name));
}

export function coerceRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? value as Record<string, unknown> : {};
}

export function isLevelThree(event: CoreEvidenceRecord) {
  return event.moduleId === "deep_sea" && event.eventType === "deep-sea.spatial-task-completed.v1" && Number(event.payload.level) === 3;
}

export function levelThreeReview(event: CoreEvidenceRecord) {
  const value = event.sessionSummary?.levelThreeReview;
  return value && typeof value === "object" ? value as Record<string, unknown> : {};
}

export function childWords(event: CoreEvidenceRecord) {
  const summary = cleanWords(event.sessionSummary?.childWords);
  if (summary) return summary;
  const turns = Array.isArray(event.payload.childTurns) ? event.payload.childTurns : [];
  return turns.map(turn => turn && typeof turn === "object" ? cleanWords((turn as Record<string, unknown>).text) : "").filter(Boolean).slice(-2).join("；");
}

export function mentorAnswers(event: CoreEvidenceRecord): string[] {
  const reflections = Array.isArray(event.sessionSummary?.mentorReflections) ? event.sessionSummary.mentorReflections : [];
  return reflections.map(item => item && typeof item === "object" ? cleanWords((item as Record<string, unknown>).answer) : "").filter(Boolean);
}

export function careerSummary(event: CoreEvidenceRecord): string {
  const name = String(event.sessionSummary?.careerName || "").trim() || CAREER_NAMES[String(event.payload.taskKey || "")] || "这次职业";
  const stages = Array.isArray(event.sessionSummary?.stageTitles) ? event.sessionSummary.stageTitles.map(item => String(item).trim()).filter(Boolean) : [];
  const list = stages.length ? stages : (CAREER_STAGE_TITLES[String(event.payload.taskKey || "")] || []);
  const attempts = Number(event.payload.attemptCount || 0), hints = Number(event.payload.hintCount || 0);
  const extra = [attempts ? `主动尝试 ${attempts} 次` : "", hints ? `查看提示 ${hints} 次` : ""].filter(Boolean).join("，");
  if (list.length) return `在“${name}”体验里，孩子完成了${list.join("、")}这几个环节${extra ? `，${extra}` : ""}。`;
  return extra ? `孩子在“${name}”体验里${extra}。` : `孩子完成了“${name}”职业体验。`;
}

/** 每次通关都会额外产生一条“完整重建”记录，内容已被各关卡卡片覆盖。 */
export function isAggregatedDeepSeaEvent(event: CoreEvidenceRecord) {
  return event.moduleId === "deep_sea" && event.eventType === "deep-sea.session-completed.v1";
}

export function hasUsableDimensionEvidence(key: string, event: CoreEvidenceRecord): boolean {
  if (isAggregatedDeepSeaEvent(event)) return false;
  if (event.moduleId === "chat") {
    const words = childWords(event);
    if (!isMeaningful(words, String(event.payload.topicKey || ""))) return false;
    if (key === "interpersonal") return mentionedPeople(words).length > 0;
    if (key === "intrapersonal") return true;
  }
  if (isLevelThree(event)) {
    const review = levelThreeReview(event);
    if (key === "linguistic") return Array.isArray(review.childUtterances) && review.childUtterances.some(item => String(item).trim());
    if (key === "interpersonal") return Boolean(String(review.solutionSummary || "").trim());
  }
  return true;
}

/**
 * 卡片正文。写不出具体内容时返回空串，由调用方过滤，
 * 这样家长端不会出现“没有保存可确认细节”这类占位卡片。
 */
export function dimensionSummary(key: string, event: CoreEvidenceRecord, fallback = ""): string {
  if (event.moduleId === "chat") {
    const words = childWords(event);
    if (!isMeaningful(words, String(event.payload.topicKey || ""))) return "";
    const people = mentionedPeople(words);
    if (key === "interpersonal") return people.length ? `孩子谈到${people.slice(0, 3).join("、")}，并说：${quoteChild(clipPhrase(words, 100))}。` : "";
    if (key === "intrapersonal") return `孩子在聊天中说：${quoteChild(clipPhrase(words, 110))}。`;
  }
  if (event.moduleId === "story") {
    const title = String(event.sessionSummary?.storyTitle || event.payload.storyTitle || "这次故事").trim();
    const highlight = String(event.sessionSummary?.childHighlight || "").trim();
    const synopsis = String(event.sessionSummary?.storySynopsis || event.sessionSummary?.storyOutline || "").trim();
    const count = Number(event.payload.contributionCount || 0);
    if (highlight) return `在《${title}》的共创中，孩子写下：${quoteChild(clipPhrase(highlight, 100))}。`;
    if (synopsis) return `孩子参与《${title}》的情节创作，故事讲到${clip(synopsis, 110)}`;
    if (count > 0) return `孩子完成《${title}》的共创，写下 ${count} 个故事片段。`;
  }
  if (event.moduleId === "career") {
    if (key === "intrapersonal") {
      const answers = mentorAnswers(event);
      if (answers.length) return `孩子在职业导师追问中回答：${quoteChild(clipPhrase(answers[answers.length - 1], 110))}。`;
    }
    return careerSummary(event);
  }
  if (event.moduleId === "deep_sea" && event.eventType === "deep-sea.spatial-task-completed.v1") {
    const level = Number(event.payload.level);
    if (level === 1) {
      const raw = coerceRecord(event.sessionSummary?.levelOneReview);
      const pairs = Array.isArray(raw.matchedRelationships) ? raw.matchedRelationships.map(item => String(item).trim()).filter(Boolean) : [];
      const successful = Number(event.payload.successfulPairs || 0), total = Number(event.payload.totalPairs || 0);
      const result = successful && total ? `，成功配对 ${successful}/${total} 组` : "";
      if (key === "naturalistic") return pairs.length ? `在第一关“珊瑚公寓”里，孩子依据栖息地和共生关系完成生态配对：${pairs.join("、")}${result}。` : `在第一关“珊瑚公寓”里，孩子比较生物特征、栖息地和共生关系后完成配对${result}。`;
      if (key === "logical") return `在第一关“珊瑚公寓”里，孩子先比较生物与住处的匹配条件，再检查配对结果是否正确${result}。`;
      if (key === "spatial") return `在第一关“珊瑚公寓”里，孩子按生物的栖息位置摆放卡片、检查每一组是否放对${result}。`;
    }
    if (level === 2) {
      const raw = coerceRecord(event.sessionSummary?.levelTwoReview);
      const rotations = Number(raw.rotateCount ?? event.payload.adjustmentCount ?? 0);
      const result = raw.connected === false ? "仍在尝试接通线路" : "接通了起点与终点";
      if (key === "spatial") return `在第二关“洋流电网”里，孩子摆放并旋转管件规划线路，经过 ${rotations} 次旋转调整后${result}。`;
      if (key === "logical") return `在第二关“洋流电网”里，孩子沿线路检查断点和方向，经过 ${rotations} 次调整后${result}。`;
    }
    if (level === 3) {
      const review = levelThreeReview(event);
      const utterances = Array.isArray(review.childUtterances) ? review.childUtterances.map(item => String(item).trim()).filter(Boolean) : [];
      const solution = String(review.solutionSummary || "").trim();
      if (key === "linguistic" && utterances.length) return `在第三关“海洋议事厅”的调解中，孩子说：${quoteChild(clipPhrase(utterances[utterances.length - 1], 110))}。`;
      if (key === "interpersonal" && solution) return `在第三关“海洋议事厅”里，孩子听取双方需要后提出协调办法：${clipPhrase(solution, 120)}。`;
      return "";
    }
  }
  return fallback;
}

function normalizeForCompare(value: string): string {
  return cleanWords(value).replace(/[^\u4e00-\u9fffA-Za-z0-9]/g, "");
}

/** 说法几乎相同的两张卡片要合并，否则家长会看到成片的雷同内容。 */
export function isNearDuplicate(left: string, right: string): boolean {
  if (!left || !right) return false;
  if (left === right || left.includes(right) || right.includes(left)) return true;
  const grams = (value: string) => { const set = new Set<string>(); for (let index = 0; index < value.length - 1; index++) set.add(value.slice(index, index + 2)); return set; };
  const a = grams(left), b = grams(right);
  if (!a.size || !b.size) return false;
  let shared = 0; a.forEach(gram => { if (b.has(gram)) shared++; });
  return shared / (a.size + b.size - shared) >= 0.62;
}

export function deduplicateEvidence(items: Evidence[]): Evidence[] {
  const kept: Evidence[] = [], fingerprints: string[] = [];
  [...items].sort((a, b) => b.time.localeCompare(a.time)).forEach(item => {
    const fingerprint = `${item.source}|${normalizeForCompare(item.behavior)}`;
    const body = fingerprint.split("|")[1];
    const duplicateIndex = fingerprints.findIndex(existing => existing.split("|")[0] === item.source && isNearDuplicate(existing.split("|")[1], body));
    if (duplicateIndex >= 0) {
      // 保留信息量更大的那条，其余视为同一次表达的不同采集副本。
      if (body.length > fingerprints[duplicateIndex].split("|")[1].length) {
        kept.splice(duplicateIndex, 1); fingerprints.splice(duplicateIndex, 1);
        kept.push(item); fingerprints.push(fingerprint);
      }
      return;
    }
    kept.push(item); fingerprints.push(fingerprint);
  });
  return kept;
}

function deepSeaGroupBehavior(level: number, ordered: Evidence[], totalRounds: number): string {
  const content = clip(ordered[ordered.length - 1].behavior, 150);
  if (totalRounds <= 1) return content;
  return `第 ${level} 关“${DEEP_SEA_LEVEL_NAMES[level]}”共 ${totalRounds} 次挑战。最近一次：${content}`;
}

/** 深海基地按关卡聚合成一条，并保留该关的真实内容而不是“共留下 N 轮记录”。 */
export function groupDeepSeaRounds(items: Evidence[], events: CoreEvidenceRecord[]): Evidence[] {
  const eventById = new Map(events.map(event => [event.id, event]));
  const completedSessions = new Set(events.filter(event => event.eventType === "deep-sea.session-completed.v1").map(event => event.sessionId));
  const totalByLevel = new Map<number, number>();
  events.forEach(event => {
    if (event.moduleId !== "deep_sea" || event.eventType !== "deep-sea.spatial-task-completed.v1") return;
    const level = Number(event.payload.level);
    totalByLevel.set(level, (totalByLevel.get(level) || 0) + 1);
  });
  const groups = new Map<number, Evidence[]>(), result: Evidence[] = [];
  items.forEach(item => {
    const event = eventById.get(item.id);
    const level = event?.moduleId === "deep_sea" && event.eventType === "deep-sea.spatial-task-completed.v1" ? Number(event.payload.level) : 0;
    if (!level) { result.push(item); return; }
    const rounds = groups.get(level) || []; rounds.push(item); groups.set(level, rounds);
  });
  groups.forEach((rounds, level) => {
    const ordered = [...rounds].sort((a, b) => a.time.localeCompare(b.time)), latest = ordered[ordered.length - 1];
    const totalRounds = Math.max(totalByLevel.get(level) || ordered.length, ordered.length);
    const complete = ordered.some(round => completedSessions.has(eventById.get(round.id)?.sessionId || ""));
    result.push({
      ...latest, id: `deep-sea-level-${level}-${latest.id}`,
      behavior: deepSeaGroupBehavior(level, ordered, totalRounds),
      time: ordered.length > 1 ? `${ordered[0].time.slice(5)} — ${latest.time.slice(5)}` : latest.time,
      level: complete ? "strong" : latest.level,
      logTitle: `深海基地第 ${level} 关“${DEEP_SEA_LEVEL_NAMES[level]}”`,
      logSummary: totalRounds > 1 ? `同一关卡共有 ${totalRounds} 次真实挑战，可按时间对照。` : "这一次挑战留下的过程记录如下。",
      logDetails: ordered.map(round => `${round.time}｜${round.behavior}`),
      rounds: ordered,
    });
  });
  return result.sort((a, b) => b.time.localeCompare(a.time));
}

/**
 * 同一次故事共创会同时留下两条记录：模块侧的情节摘要和平台侧收集的作品
 * 概要。它们讲的是同一件事，合并成一条，避免同一本书出现两张卡片。
 */
export function groupStorySessions(items: Evidence[], events: CoreEvidenceRecord[]): Evidence[] {
  const eventById = new Map(events.map(event => [event.id, event]));
  const groups = new Map<string, Evidence[]>(), result: Evidence[] = [];
  items.forEach(item => {
    const event = eventById.get(item.id);
    const title = event?.moduleId === "story" ? String(event.sessionSummary?.storyTitle || event.payload.storyTitle || "").trim() : "";
    if (!title) { result.push(item); return; }
    const rounds = groups.get(title) || []; rounds.push(item); groups.set(title, rounds);
  });
  groups.forEach(rounds => {
    if (rounds.length === 1) { result.push(rounds[0]); return; }
    const ordered = [...rounds].sort((a, b) => a.time.localeCompare(b.time));
    let richest = ordered[0];
    ordered.forEach(round => { if (round.behavior.length > richest.behavior.length) richest = round; });
    // 只有模块侧记录才有可靠的片段数，平台侧收集记录的数字会重复计数。
    // 卡片的 time 只精确到分钟，同一分钟内两条记录的顺序不稳定，所以按
    // “是否来自平台收集”来判断，而不是靠排序取第一条。
    const candidates = ordered.map(round => eventById.get(round.id)).filter((event): event is CoreEvidenceRecord => Boolean(event));
    const moduleEvent = candidates.find(event => event.sessionSummary?.collectedFromStoryModule !== true) || candidates[0];
    const contributions = Number(moduleEvent?.payload.contributionCount || 0);
    const needsCount = contributions >= 2 && !/写下 \d+ 个/.test(richest.behavior);
    result.push({
      ...richest,
      behavior: needsCount ? `${clip(richest.behavior, 150).replace(/。$/, "")}。这次共创共写下 ${contributions} 个情节片段。` : richest.behavior,
      time: ordered[ordered.length - 1].time,
      logSummary: richest.behavior,
      logDetails: ordered.flatMap(round => round.logDetails?.length ? round.logDetails : [round.behavior]),
      rounds: ordered,
    });
  });
  return result;
}

/**
 * 同一次表达可能在同一分钟里留下两条聊天记录（两段会话各自转写了一次，
 * 结果有长有短、有对有错）。它们指向同一个时间点，同时展示会让家长以为
 * 孩子说了两遍，因此按时段合并，保留信息更完整的一条。
 *
 * 合并前后都要确认是在讲同一件事：共享的双字词少于 3 个时视为两次不同的
 * 表达，仍然各出一张卡片。
 */
export function groupChatCaptures(items: Evidence[], events: CoreEvidenceRecord[]): Evidence[] {
  const eventById = new Map(events.map(event => [event.id, event]));
  const groups = new Map<string, { item: Evidence; words: string }[]>(), result: Evidence[] = [];
  items.forEach(item => {
    const event = eventById.get(item.id);
    if (event?.moduleId !== "chat") { result.push(item); return; }
    const key = `${item.source}|${item.time}`;
    const group = groups.get(key) || [];
    group.push({ item, words: childWords(event) });
    groups.set(key, group);
  });
  groups.forEach(group => {
    if (group.length === 1) { result.push(group[0].item); return; }
    // 比较的是孩子原话本身。卡片正文带着同一句模板（“孩子在聊天中说：…”），
    // 直接比正文会把同一分钟里两条无关的表达也判成同一件事。
    const ordered = [...group].sort((a, b) => b.words.length - a.words.length);
    const kept: { item: Evidence; words: string }[] = [];
    ordered.forEach(candidate => {
      if (!kept.some(existing => sharesContent(existing.words, candidate.words))) kept.push(candidate);
    });
    kept.forEach(candidate => result.push(candidate.item));
  });
  return result.sort((a, b) => b.time.localeCompare(a.time));
}

function contentGrams(value: string): Set<string> {
  const text = normalizeForCompare(value), grams = new Set<string>();
  for (let index = 0; index < text.length - 1; index++) grams.add(text.slice(index, index + 2));
  return grams;
}

/** 两条摘录是否在讲同一件事：共享的双字词够多。 */
function sharesContent(left: string, right: string, minimum = 3): boolean {
  const a = contentGrams(left), b = contentGrams(right);
  if (!a.size || !b.size) return false;
  let shared = 0; a.forEach(gram => { if (b.has(gram)) shared++; });
  return shared >= minimum;
}

/** 一张卡片对应的原始事件 id：分组后的卡片要展开它包含的每一轮记录。 */
export function evidenceEventIds(item: Evidence): string[] {
  const rounds = (item.rounds || []).map(round => round.id).filter(Boolean);
  return rounds.length ? [...new Set(rounds)] : [item.id];
}

/** 把一个维度的原始事件整理成最终展示的卡片。 */
export function buildTalentEvidence(
  key: string,
  events: CoreEvidenceRecord[],
  explanations: { evidence_ref: string | null; title: string; summary: string; details: string[] }[],
  sourceNames: Record<string, string>,
  continent: string,
  detailsFor: (key: string, event: CoreEvidenceRecord, fallback: string[]) => string[],
): Evidence[] {
  // 分组时需要看到「完整通关」记录才能判断某次挑战是否走完全流程，
  // 但它本身不单独出卡片，所以过滤前后的集合要分开用。
  const dimensionEvents = events.filter(event => event.reportDimensions.includes(key));
  const usable = dimensionEvents.filter(event => hasUsableDimensionEvidence(key, event));
  const items = usable.map(event => {
    const explanation = explanations.find(item => item.evidence_ref === event.id);
    const summary = dimensionSummary(key, event, explanation?.summary || event.behaviorSummary);
    return {
      id: event.id, behavior: summary, source: sourceNames[event.moduleId] || "探索活动",
      continent: `${continent} · ${sourceNames[event.moduleId] || "探索活动"}`,
      time: event.occurredAt.replace("T", " ").slice(0, 16), level: event.evidenceLevel, raw: "",
      logTitle: explanation?.title || "这次探索的过程记录", logSummary: summary,
      logDetails: detailsFor(key, event, explanation?.details || ["生成完成后会显示这次活动中具体发生的过程。"]),
    } as Evidence;
  }).filter(item => item.behavior.trim());
  const deduped = deduplicateEvidence(items);
  const grouped = groupChatCaptures(deduped, events);
  // 分组时传入全部记录（而不是本维度的切片）：完整通关记录可能只挂在别的
  // 维度上，只看切片会让同一关在别的维度里被误标成“参考线索”。
  return groupStorySessions(groupDeepSeaRounds(grouped, events), events);
}
