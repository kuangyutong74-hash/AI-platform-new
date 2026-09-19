import assert from "node:assert/strict";
import test from "node:test";

import {
  canonicalExplorerModule,
  createDemoCollection,
  explorerModuleName,
  normalizeCollectionResponse,
} from "../app/lib/explorer-data.mjs";

test("uses one canonical Chinese mapping for the four exploration modules", () => {
  assert.equal(canonicalExplorerModule("deep_sea"), "deep_sea");
  assert.equal(canonicalExplorerModule("deep-sea"), "deep_sea");
  assert.equal(canonicalExplorerModule("build"), "deep_sea");
  assert.equal(explorerModuleName("chat"), "聊天观察");
  assert.equal(explorerModuleName("story"), "故事共创");
  assert.equal(explorerModuleName("deep_sea"), "深海基地重建");
  assert.equal(explorerModuleName("career"), "职业模拟器");
  assert.equal(canonicalExplorerModule("unexpected_module"), null);
});

test("does not misclassify an unknown module as chat", () => {
  const result = normalizeCollectionResponse({
    account: {display_name: "小芽", age: 8},
    works: [{id: "unknown-work", module: "unexpected_module", title: "未知记录"}],
    milestones: [{id: "unknown-step", module: "unexpected_module", title: "未知足迹"}],
  });
  assert.equal(result.worksAreDemo, true);
  assert.equal(result.timelineIsDemo, true);
  assert.equal(result.works.some(item => item.id === "unknown-work"), false);
});

test("normalizes account-owned works and milestones without replacing them with demo records", () => {
  const result = normalizeCollectionResponse({
    account: { id: "child-1", display_name: "小航", age: 8, created_at: "2026-08-01T08:00:00Z" },
    works: [
      {
        id: "work-1",
        module: "story",
        title: "会发光的雨伞",
        summary: "我给怕黑的小龙做了一把伞。",
        detail: "故事讲的是小龙撑着发光的雨伞走过黑夜。",
        highlight_reason: "连续参与了 6 轮共创，并主动为故事补写了结尾。",
        occurred_at: "2026-08-20T08:00:00+00:00",
        quote: "这样它就不怕黑啦。",
        kind: "highlight",
        is_highlight: true,
        comments: [{ id: "c-1", body: "这个结尾很有想象力。", author_name: "李老师", author_kind: "teacher", created_at: "2026-08-21T08:00:00Z" }],
        metric_label: "故事长度",
        metric_value: "386 字",
      },
    ],
    milestones: [
      {
        id: "registration-child-1",
        module: "registration",
        kind: "registration",
        title: "小航来到探索星球",
        summary: "第一颗星",
        occurred_at: "2026-08-01T08:00:00+00:00",
        unlocked: true,
        duration_seconds: 0,
        duration_coverage: 0,
      },
    ],
  });

  assert.equal(result.account.displayName, "小航");
  assert.equal(result.isDemo, false);
  assert.equal(result.works.length, 1);
  assert.equal(result.works[0].module, "story");
  assert.equal(result.works[0].detail, "故事讲的是小龙撑着发光的雨伞走过黑夜。");
  assert.equal(result.works[0].highlightReason, "连续参与了 6 轮共创，并主动为故事补写了结尾。");
  assert.notEqual(result.works[0].highlightReason, result.works[0].detail);
  assert.equal(result.works[0].quote, "这样它就不怕黑啦。");
  assert.equal(result.works[0].metricValue, "386 字");
  assert.equal(result.works[0].isHighlight, true);
  assert.equal(result.works[0].comments[0].authorName, "李老师");
  assert.equal(result.milestones.length, 1);
  assert.equal(result.milestones[0].module, "registration");
  assert.equal(result.milestones[0].durationSeconds, 0);
  assert.equal(result.milestones[0].durationCoverage, 0);
  assert.equal(result.worksAreDemo, false);
  assert.equal(result.timelineIsDemo, false);
});

test("creates an honestly labelled child-friendly demo collection when no evidence exists", () => {
  const result = createDemoCollection({ displayName: "小小探索家", age: 8 });

  assert.equal(result.isDemo, true);
  assert.equal(result.worksAreDemo, true);
  assert.equal(result.timelineIsDemo, true);
  assert.match(result.worksNotice, /示例/);
  assert.equal(new Set(result.works.map((item) => item.module)).size, 4);
  assert.equal(result.milestones[0].kind, "registration");
  const moduleReview = result.milestones.find((item) => item.module === "career");
  assert.ok(moduleReview.observations.length > 0);
  assert.ok(moduleReview.recentSessions.length > 0);
});

test("normalizes process observations and recent sessions for growth reviews", () => {
  const result = normalizeCollectionResponse({
    account: { display_name: "小满", age: 9 },
    works: [],
    milestones: [{
      id: "career-summary",
      module: "career",
      kind: "module_summary",
      title: "职业模拟器的完成小结",
      observations: ["完成职业任务并留下过程记录"],
      evidence_count: 3,
      artifact_count: 1,
      recent_sessions: [{
        id: "career-session",
        occurred_at: "2026-09-01T08:00:00Z",
        duration_seconds: 420,
        caption: "完成小医生体验的 3/3 个阶段",
      }],
    }],
  });
  const review = result.milestones[0];
  assert.equal(review.evidenceCount, 3);
  assert.equal(review.artifactCount, 1);
  assert.deepEqual(review.observations, ["完成职业任务并留下过程记录"]);
  assert.equal(review.recentSessions[0].durationSeconds, 420);
  assert.match(review.recentSessions[0].caption, /3\/3/);
});

test("falls back to the labelled demo collection for an empty backend response", () => {
  const result = normalizeCollectionResponse({
    account: { id: "child-2", display_name: "小雨", age: 7 },
    works: [],
    milestones: [],
  });

  assert.equal(result.isDemo, true);
  assert.equal(result.account.displayName, "小雨");
  assert.match(result.worksNotice, /示例/);
});

test("keeps a real registration timeline when highlights still need examples", () => {
  const result = normalizeCollectionResponse({
    account: { id: "child-3", display_name: "小星", age: 8, created_at: "2026-08-03T08:00:00Z" },
    works: [],
    milestones: [
      {
        id: "registration-child-3",
        module: "registration",
        kind: "registration",
        title: "小星来到探索星球",
        occurred_at: "2026-08-03T08:00:00Z",
      },
    ],
  });

  assert.equal(result.worksAreDemo, true);
  assert.equal(result.timelineIsDemo, false);
  assert.equal(result.milestones[0].title, "小星来到探索星球");
  assert.equal(result.works.length, 4);
});
