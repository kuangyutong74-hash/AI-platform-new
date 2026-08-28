import assert from "node:assert/strict";
import test from "node:test";

import { getViewFromUrl, urlForView } from "../app/lib/view-state.mjs";

test("keeps student and adult views separated", () => {
  assert.equal(getViewFromUrl("http://localhost:4173/?view=works"), "works");
  assert.equal(getViewFromUrl("http://localhost:4173/?view=treasure"), "treasure");
  assert.equal(getViewFromUrl("http://localhost:4173/?view=timeline"), "planet");
  assert.equal(getViewFromUrl("http://localhost:4173/?view=timeline", "adult"), "timeline");
  assert.equal(getViewFromUrl("http://localhost:4173/?view=showcase", "adult"), "showcase");
  assert.equal(getViewFromUrl("http://localhost:4173/?view=planet", "adult"), "report");
  assert.equal(getViewFromUrl("http://localhost:4173/?view=unknown"), "planet");
});

test("keeps the planet address clean and preserves valid personal views", () => {
  assert.equal(urlForView("planet"), "/");
  assert.equal(urlForView("works"), "/?view=works");
  assert.equal(urlForView("report", "adult"), "/");
  assert.equal(urlForView("timeline", "adult"), "/?view=timeline");
});
