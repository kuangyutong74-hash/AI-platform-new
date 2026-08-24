import assert from "node:assert/strict";
import test from "node:test";

import { getViewFromUrl, urlForView } from "../app/lib/view-state.mjs";

test("opens works and growth views from shareable query addresses", () => {
  assert.equal(getViewFromUrl("http://localhost:4173/?view=works"), "works");
  assert.equal(getViewFromUrl("http://localhost:4173/?view=timeline"), "timeline");
  assert.equal(getViewFromUrl("http://localhost:4173/?view=unknown"), "planet");
});

test("keeps the planet address clean and preserves valid personal views", () => {
  assert.equal(urlForView("planet"), "/");
  assert.equal(urlForView("works"), "/?view=works");
  assert.equal(urlForView("timeline"), "/?view=timeline");
});
