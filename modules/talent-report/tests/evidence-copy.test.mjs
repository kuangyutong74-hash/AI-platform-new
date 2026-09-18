/**
 * 顺序阅读版渲染规则回归测试。
 *
 * 用真实采集到的原始记录（含语音识别分词、入口提示回填、深海重复通关）
 * 断言家长端最终看到的卡片：没有重复、没有通用占位文案、每条都能回溯。
 *
 * 运行：node --test modules/talent-report/tests/evidence-copy.test.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";

import {
  buildTalentEvidence,
  childWords,
  cleanWords,
  clip,
  clipPhrase,
  dimensionSummary,
  evidenceEventIds,
  hasUsableDimensionEvidence,
  isMeaningful,
  isNearDuplicate,
  mentionedPeople,
  quoteChild,
} from "../src/lib/evidenceCopy.ts";

const sourceNames = { story: "故事共创", deep_sea: "深海基地重建", chat: "聊天观察", career: "职业模拟器" };
const noExtraDetails = (_key, _event, fallback) => fallback;

function chatEvent(id, words, topicKey, occurredAt = "2026-09-05T11:44:00Z", dimensions = ["interpersonal", "intrapersonal"]) {
  return {
    id, sourceEventId: id, sessionId: `s-${id}`, moduleId: "chat", moduleVersion: "1.0.0",
    eventType: "chat.observation-shared.v1", occurredAt, evidenceLevel: "reference",
    constructs: [], reportDimensions: dimensions, behaviorSummary: "分享了一次观察或想法",
    payload: { turnCount: 2, topicKey }, sessionSummary: { childWords: words },
  };
}

function deepSeaEvent(id, level, occurredAt, payload = {}, sessionSummary = {}) {
  return {
    id, sourceEventId: id, sessionId: `s-${Math.floor(level)}-${id}`, moduleId: "deep_sea", moduleVersion: "1.0.0",
    eventType: "deep-sea.spatial-task-completed.v1", occurredAt, evidenceLevel: "reference",
    constructs: [], reportDimensions: level === 3 ? ["linguistic", "interpersonal"] : ["spatial", "logical", "naturalistic"],
    behaviorSummary: "完成深海基地建造任务", payload: { level, ...payload }, sessionSummary,
  };
}

const deepSeaSessionCompleted = (id, sessionId, occurredAt) => ({
  id, sourceEventId: id, sessionId, moduleId: "deep_sea", moduleVersion: "1.0.0",
  eventType: "deep-sea.session-completed.v1", occurredAt, evidenceLevel: "strong",
  constructs: [], reportDimensions: ["spatial", "logical"], behaviorSummary: "完成深海基地三关完整重建",
  payload: { completedLevels: 3, totalLevels: 3, adjustmentCount: 14 }, sessionSummary: { completedLevels: 3 },
});

test("入口提示词和口头碎片不会被当成孩子的表达", () => {
  assert.equal(cleanWords("的 我 今天 什么 事 都 不用 干"), "我今天什么事都不用干");
  assert.equal(isMeaningful("今天最想记住的事", "我的新发现"), false);
  assert.equal(isMeaningful("游泳", "运动"), false);
  assert.equal(isMeaningful("我", "运动"), false);
  assert.equal(isMeaningful("我最近在折纸飞机，可好玩啦！", "学习"), true);
  // 话题词被原样回填时同样不算证据。
  assert.equal(isMeaningful("朋友相处", "朋友相处"), false);
});

test("写不出具体内容的记录不进入证据列表", () => {
  const events = [chatEvent("chat-echo", "今天最想记住的事", "我的新发现"), chatEvent("chat-ok", "我最近在折纸飞机，可好玩啦！", "学习")];
  const cards = buildTalentEvidence("intrapersonal", events, [], sourceNames, "未来之洲", noExtraDetails);
  assert.equal(cards.length, 1);
  assert.match(cards[0].behavior, /折纸飞机/);
  assert.equal(dimensionSummary("intrapersonal", events[0]), "");
  assert.equal(hasUsableDimensionEvidence("intrapersonal", events[0]), false);
});

test("人际维度只在真的提到具体对象时才出证据", () => {
  const withPeople = chatEvent("chat-people", "开学了，我能见到我的同学们并且一起学习", "兴趣爱好");
  const withoutPeople = chatEvent("chat-solo", "我最近在折纸飞机，可好玩啦！", "学习");
  assert.equal(mentionedPeople(childWords(withPeople)).includes("同学"), true);
  assert.equal(hasUsableDimensionEvidence("interpersonal", withPeople), true);
  assert.equal(hasUsableDimensionEvidence("interpersonal", withoutPeople), false);
  assert.equal(dimensionSummary("interpersonal", withoutPeople), "");
});

test("同一段表达被多次采集时只保留信息量最大的一条", () => {
  const events = [
    chatEvent("chat-a", "我最近在折纸飞机，可好玩啦！", "学习", "2026-09-05T11:44:00Z"),
    chatEvent("chat-b", "我最近在折纸飞机，可好玩啦", "学习", "2026-09-05T11:44:20Z"),
  ];
  const cards = buildTalentEvidence("intrapersonal", events, [], sourceNames, "未来之洲", noExtraDetails);
  assert.equal(cards.length, 1);
  assert.match(cards[0].behavior, /可好玩啦/);
});

test("深海基地按关卡聚合，并保留该关的真实内容", () => {
  const review = { levelOneReview: { matchedRelationships: ["双锯鱼 → 海葵", "花园鳗 → 沙地"] } };
  const events = [
    deepSeaEvent("l1-a", 1, "2026-09-02T07:07:00Z", { successfulPairs: 4, totalPairs: 4 }),
    deepSeaEvent("l1-b", 1, "2026-09-07T03:40:00Z", { successfulPairs: 4, totalPairs: 4 }, review),
    deepSeaEvent("l1-c", 1, "2026-09-08T14:13:00Z", { successfulPairs: 4, totalPairs: 4 }, review),
  ];
  const cards = buildTalentEvidence("naturalistic", events, [], sourceNames, "创造之洲", noExtraDetails);
  assert.equal(cards.length, 1);
  assert.match(cards[0].behavior, /3 次挑战/);
  assert.match(cards[0].behavior, /双锯鱼/);
  assert.doesNotMatch(cards[0].behavior, /共留下 \d+ 轮观察记录/);
  // 三次挑战里两条描述相同被合并，一次细节较少的挑战保留为独立轮次。
  assert.equal(cards[0].rounds.length, 2);
  assert.equal(cards[0].logDetails.length, 2);
});

test("完整通关记录不会重复成额外卡片，但会算作已引用证据", () => {
  const completed = deepSeaSessionCompleted("done", "s-2-l2-a", "2026-09-08T14:15:00Z");
  const events = [
    deepSeaEvent("l2-a", 2, "2026-09-08T14:13:50Z", { adjustmentCount: 13 }, { levelTwoReview: { rotateCount: 13, connected: true } }),
    completed,
  ];
  const cards = buildTalentEvidence("spatial", events, [], sourceNames, "创造之洲", noExtraDetails);
  assert.equal(cards.length, 1);
  assert.equal(cards.some(card => card.id === completed.id), false);
  // 聚合后仍标记为“较完整记录”：同一次会话确实完整通关。
  assert.equal(cards[0].level, "strong");
  assert.match(cards[0].behavior, /13 次旋转调整后接通了起点与终点/);
});

test("完整通关记录只挂在别的维度上时，本维度照样认得出这次挑战是完整的", () => {
  // 真实库里“完整通关”事件只挂在 logical/spatial 上，自然观察维度只看得到
  // 第一关记录。若按维度切片判断，同一关会被误标成“参考线索”。
  const completed = deepSeaSessionCompleted("done", "s-1-l1-a", "2026-09-02T07:20:00Z");
  const events = [
    deepSeaEvent("l1-a", 1, "2026-09-02T07:07:00Z", { successfulPairs: 4, totalPairs: 4 }),
    completed,
  ];
  const cards = buildTalentEvidence("naturalistic", events, [], sourceNames, "创造之洲", noExtraDetails);
  assert.equal(cards.length, 1);
  assert.equal(cards[0].level, "strong");
  // 聚合摘要那条不会因为被看到就多出一张卡片。
  assert.equal(cards.some(card => card.id === "done"), false);
});

test("整屏雷同的聊天卡片在真实数据上被收敛", () => {
  // 这四条来自真实库：同一分钟内两次转写的同一次表达、一条入口提示、一条过短碎片。
  const events = [
    chatEvent("c1", "暑假 作业 做完 了 我 有 非常 重 的 时间 去 干 自己 喜欢 的 事情", "学习", "2026-09-05T11:44:03Z"),
    chatEvent("c2", "最近 是 暑假 我 完成 暑假 作业 之后 就 没有 什么 压力 了 每天 可以 干我自己 喜欢 的 事情", "运动", "2026-09-05T11:44:22Z"),
    chatEvent("c3", "今天最想记住的事", "我的新发现", "2026-09-16T13:38:59Z"),
    chatEvent("c4", "游泳", "运动", "2026-09-05T11:22:33Z"),
  ];
  const cards = buildTalentEvidence("intrapersonal", events, [], sourceNames, "倾听之洲", noExtraDetails);
  // 同一分钟的两次转写合并成一条，保留信息更完整的那句。
  assert.equal(cards.length, 1);
  const bodies = cards.map(card => card.behavior);
  assert.equal(bodies.some(body => body.includes("今天最想记住的事")), false);
  assert.equal(bodies.some(body => body.includes("游泳")), false);
  // 分词空格被还原，家长读到的是正常句子。
  assert.equal(bodies.some(body => body.includes("最近是暑假我完成暑假作业之后就没有什么压力了")), true);
});

test("同一分钟内讲不同事情的聊天不会被误合并", () => {
  const events = [
    chatEvent("c1", "我今天在公园里看到一只很胖的橘猫", "我的新发现", "2026-09-05T11:44:03Z"),
    chatEvent("c2", "妈妈的生日我想画一张贺卡送给她", "兴趣爱好", "2026-09-05T11:44:40Z"),
  ];
  const cards = buildTalentEvidence("intrapersonal", events, [], sourceNames, "倾听之洲", noExtraDetails);
  assert.equal(cards.length, 2);
  const bodies = cards.map(card => card.behavior);
  assert.equal(bodies.some(body => body.includes("橘猫")), true);
  assert.equal(bodies.some(body => body.includes("贺卡")), true);
});

test("原话自带引号时外层改用「」，不产生嵌套引号", () => {
  const event = chatEvent("q1", "我想从“一个从没去过的地方”开始，然后写一只迷路的猫", "我的新发现", "2026-09-17T05:42:00Z");
  const text = dimensionSummary("intrapersonal", event);
  assert.match(text, /「我想从“一个从没去过的地方”开始/);
  assert.doesNotMatch(text, /“我想从“/);
  assert.equal(quoteChild("我今天去游泳了"), "“我今天去游泳了”");
});

test("整个维度的卡片文案都不出现嵌套引号", () => {
  const quoted = "我想从“一个从没去过的地方”开始";
  const events = [
    chatEvent("q-chat", quoted, "我的新发现", "2026-09-17T05:42:00Z"),
    deepSeaEvent("q-l3", 3, "2026-09-17T07:10:00Z", {}, {
      levelThreeReview: { solutionSummary: "轮流先说各自的需要。", childUtterances: [quoted] },
    }),
  ];
  const blob = ["linguistic", "interpersonal", "intrapersonal"]
    .flatMap(key => buildTalentEvidence(key, events, [], sourceNames, "倾听之洲", noExtraDetails))
    .map(card => JSON.stringify(card))
    .join("\n");
  assert.doesNotMatch(blob, /“[^”]{0,80}“/);
  assert.match(blob, /「我想从“一个从没去过的地方”开始」/);
});

test("分组卡片能回溯到它包含的每一条原始记录", () => {
  const review = { levelOneReview: { matchedRelationships: ["双锯鱼 → 海葵"] } };
  const events = [
    deepSeaEvent("l1-a", 1, "2026-09-02T07:07:00Z", { successfulPairs: 4, totalPairs: 4 }),
    deepSeaEvent("l1-b", 1, "2026-09-07T03:40:00Z", { successfulPairs: 4, totalPairs: 4 }, review),
  ];
  const cards = buildTalentEvidence("naturalistic", events, [], sourceNames, "创造之洲", noExtraDetails);
  assert.equal(cards.length, 1);
  const ids = evidenceEventIds(cards[0]);
  assert.equal(ids.includes("l1-a"), true);
  assert.equal(ids.includes("l1-b"), true);
  cards[0].rounds.forEach(round => assert.equal(ids.includes(round.id), true));
});

test("长梗概按句读截断，不留半句话或未闭合引号", () => {
  const synopsis = "舷窗外，蓝白相间的地球渐渐缩小成一颗弹珠。小Q坐在“萤火号”飞船的驾驶舱里，金属手指轻轻搭在操控板上。它刚刚把飞船调成自动驾驶，准备前往木星的第二颗卫星——欧罗巴，去检查那里新发现的冰下信号。小Q习惯性地整理数据，小声嘀咕：“起飞时间是标准时07:12:33，比计划晚了0.4秒。”";
  const event = {
    id: "story-1", sourceEventId: "story-1", sessionId: "s-story", moduleId: "story", moduleVersion: "1.0.0",
    eventType: "story.contribution-completed.v1", occurredAt: "2026-09-03T12:16:49Z", evidenceLevel: "reference",
    constructs: [], reportDimensions: ["linguistic"], behaviorSummary: "完成故事共创表达",
    payload: { contributionCount: 5, storyTitle: "小Q的星空探险" },
    sessionSummary: { storyTitle: "小Q的星空探险", storySynopsis: synopsis },
  };
  const text = dimensionSummary("linguistic", event);
  assert.equal((text.match(/“/g) || []).length, (text.match(/”/g) || []).length);
  assert.match(text, /故事讲到/);
  assert.doesNotMatch(text, /起飞时间是标准/);
  assert.equal(clip(synopsis, 26).endsWith("；") || clip(synopsis, 26).endsWith("。") || clip(synopsis, 26).endsWith("…"), true);
  assert.equal(clipPhrase("每天轮换优先使用时段；设置可移动屏风。", 12).endsWith("；"), false);
});

test("同一次故事共创只出一张卡片", () => {
  const storyEvent = (id, eventType, occurredAt, payload, sessionSummary) => ({
    id, sourceEventId: id, sessionId: "s-story", moduleId: "story", moduleVersion: "1.0.0",
    eventType, occurredAt, evidenceLevel: "reference", constructs: [], reportDimensions: ["linguistic"],
    behaviorSummary: "完成故事共创表达", payload, sessionSummary,
  });
  const events = [
    storyEvent("story-module", "story.contribution-completed.v1", "2026-09-05T11:49:57Z", { contributionCount: 2, storyTitle: "小小的丛林探险记" }, { completionMode: "director" }),
    // 平台侧收集记录只比模块记录晚一秒，且时间会截断到分钟，顺序不可依赖。
    storyEvent("story-collected", "story.contribution-completed.v1", "2026-09-05T11:49:58Z", { contributionCount: 1, storyTitle: "小小的丛林探险记" }, { storyTitle: "小小的丛林探险记", storySynopsis: "小小住在魔法森林边的一朵蓝色蘑菇屋里，每天早晨推开小圆窗。", collectedFromStoryModule: true }),
  ];
  const cards = buildTalentEvidence("linguistic", events, [], sourceNames, "想象之洲", noExtraDetails);
  assert.equal(cards.length, 1);
  assert.match(cards[0].behavior, /蘑菇屋/);
  assert.match(cards[0].behavior, /共写下 2 个情节片段/);
  assert.equal(cards[0].rounds.length, 2);
});

test("近似重复判定不误伤不同内容", () => {
  assert.equal(isNearDuplicate("在《童话王国》的共创中，孩子写下了一句话", "在《小Q的星空探险》的共创中，孩子写下了另一句话"), false);
  assert.equal(isNearDuplicate("孩子谈到同学，并说了自己的期待", "孩子谈到同学，并说了自己的想法"), true);
});
