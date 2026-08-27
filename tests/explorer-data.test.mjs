import assert from "node:assert/strict";
import test from "node:test";

import {
  createDemoCollection,
  normalizeCollectionResponse,
} from "../app/lib/explorer-data.mjs";

test("normalizes account-owned works and milestones without replacing them with demo records", () => {
  const result = normalizeCollectionResponse({
    account: { id: "child-1", display_name: "小航", age: 8, created_at: "2026-08-01T08:00:00Z" },
    works: [
      {
        id: "work-1",
        module: "story",
        title: "会发光的雨伞",
        summary: "我给怕黑的小龙做了一把伞。",
        occurred_at: "2026-08-20T08:00:00+00:00",
        quote: "这样它就不怕黑啦。",
        kind: "highlight",
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
  assert.equal(result.works[0].quote, "这样它就不怕黑啦。");
  assert.equal(result.works[0].metricValue, "386 字");
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
