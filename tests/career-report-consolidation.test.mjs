import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

test("career exploration center no longer exposes a separate adult observer surface", async () => {
  const html = await readFile(new URL("../modules/career/backend/templates/my_exploration.html", import.meta.url), "utf8");
  assert.doesNotMatch(html, /class="observer-entry"/);
  assert.doesNotMatch(html, /class="my-avatar"/);
  assert.doesNotMatch(html, />探索者</);
  assert.doesNotMatch(html, /id="cross-career-teacher"/);
});

test("career exploration center omits the redundant local growth feed but keeps its data loader", async () => {
  const html = await readFile(new URL("../modules/career/backend/templates/my_exploration.html", import.meta.url), "utf8");
  assert.doesNotMatch(html, /class="exploration-feed-section"/);
  assert.doesNotMatch(html, /id="exploration-feed-title"/);
  assert.match(html, /loadExplorationFeed\(\)/);
  assert.match(html, /renderExplorationDashboard\(activities, records/);
});

test("legacy observer route redirects to the unified platform report", async () => {
  const source = await readFile(new URL("../modules/career/backend/main.py", import.meta.url), "utf8");
  const route = source.slice(source.indexOf('@app.get("/observer"'), source.indexOf('@app.get("/scenario/'));
  assert.match(route, /RedirectResponse\(url="http:\/\/localhost:4173\/\?view=report", status_code=302\)/);
  assert.doesNotMatch(route, /observer_dashboard\.html/);
});

test("workday and scenario evidence are consolidated before platform completion", async () => {
  const workday = await readFile(new URL("../modules/career/backend/static/js/workday.js", import.meta.url), "utf8");
  const scenario = await readFile(new URL("../modules/career/backend/static/js/app.js", import.meta.url), "utf8");
  assert.match(workday, /emitEvidence[\s\S]*publishArtifact/);
  assert.doesNotMatch(workday, /await platformSdk\.completeSession/);
  assert.match(scenario, /taskKey:careerId\+'\:scenario'/);
  assert.ok(scenario.indexOf("emitEvidence") < scenario.indexOf("completeSession"));
  assert.ok(scenario.indexOf("completeSession") < scenario.indexOf("sessionStorage.setItem(marker,'1')"));
});
