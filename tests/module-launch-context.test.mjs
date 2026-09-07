import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

const moduleEntrypoints = [
  ["深海基地", "../modules/deep-sea/index.html"],
  ["故事共创", "../modules/story/frontend/index.html"],
  ["职业体验", "../modules/career/backend/templates/base.html"],
  ["聊天观察", "../modules/chat/public/home.html"],
  ["聊天观察 · 聊天页", "../modules/chat/public/chat.html"],
];

test("module entrypoints load the shared V1 SDK without a V0 bridge", async () => {
  for (const [name, path] of moduleEntrypoints) {
    const html = await readFile(new URL(path, import.meta.url), "utf8");
    const sdk = html.indexOf("/sdk/module-sdk.js");
    assert.ok(sdk >= 0, `${name} must load the Module SDK`);
    assert.equal(html.includes("ai-bole-bridge.js"), false, `${name} must not load the V0 bridge`);
  }
});

test("SDK consumes and clears the same-page LaunchContext without persisting its token", async () => {
  const sdk = await readFile(new URL("../packages/module-sdk/module-sdk.js", import.meta.url), "utf8");
  assert.match(sdk, /ai-bole\.launch-context\.v1/);
  assert.match(sdk, /global\.name = ""/);
  assert.match(sdk, /module-authorizations:exchange/);
  assert.match(sdk, /evidence-events:batch/);
  assert.match(sdk, /connectOptional/);
  assert.match(sdk, /context \|\| readContext\(\)/);
  assert.match(sdk, /captureSnapshot/);
  assert.match(sdk, /publishArtifact/);
  assert.match(sdk, /completeSession/);
  assert.match(sdk, /interruptOnPageHide/);
  assert.doesNotMatch(sdk, /localStorage|sessionStorage/);
});

test("chat connects on entry and only marks completion after platform sync", async () => {
  const chat = await readFile(new URL("../modules/chat/public/chat.html", import.meta.url), "utf8");
  assert.match(chat, /DOMContentLoaded[^\n]*connectChatPlatform/);
  assert.ok(
    chat.indexOf("await saveConversationToPlatform()") < chat.indexOf("finalized=true"),
    "chat must not suppress a retry before the timeline and artifact are saved",
  );
});

test("story and career keep works and timeline completion in the same successful flow", async () => {
  const story = await readFile(new URL("../modules/story/frontend/src/pages/StoryPlayPage.tsx", import.meta.url), "utf8");
  const career = await readFile(new URL("../modules/career/backend/static/js/workday.js", import.meta.url), "utf8");
  assert.match(story, /syncCompletedStory[\s\S]*emitStoryCompleted[\s\S]*addStoryToMyWorks/);
  assert.ok(
    career.indexOf("await platformSdk.completeSession") < career.indexOf("sessionStorage.setItem(marker,'1')"),
    "career must remain retryable until its artifact and timeline session are complete",
  );
});

test("career restores a missing launch context from the shared account session", async () => {
  const career = await readFile(new URL("../modules/career/backend/templates/career_select.html", import.meta.url), "utf8");
  assert.match(career, /readCareerLaunchContext/);
  assert.match(career, /\/api\/v1\/assessment-sessions/);
  assert.match(career, /credentials:'include'/);
  assert.match(career, /JSON\.stringify\(\{module_id:'career'\}\)/);
  assert.match(career, /window\.name=JSON\.stringify\(\{namespace:'ai-bole\.launch-context\.v1',context:context\}\)/);
  assert.ok(
    career.indexOf("resolvePlatformConnection()") < career.indexOf("fd.set('student_name'"),
    "career must restore platform identity before creating its local scenario session",
  );
});

test("platform module launch and career sessions do not reject students by age", async () => {
  const core = await readFile(new URL("../modules/platform-core/main.py", import.meta.url), "utf8");
  const createLaunch = core.slice(
    core.indexOf("def create_assessment_session"),
    core.indexOf("@app.post(\"/api/v1/module-authorizations:exchange\")"),
  );
  assert.doesNotMatch(createLaunch, /if\s+not\s+manifest\[\"targetAge\"\]/);
  assert.doesNotMatch(createLaunch, /当前年龄不在该体验模块的适用范围/);

  const career = await readFile(new URL("../modules/career/backend/main.py", import.meta.url), "utf8");
  const startSession = career.slice(
    career.indexOf("async def api_start_session"),
    career.indexOf("# === API: SCENARIO ==="),
  );
  assert.doesNotMatch(startSession, /MIN_AGE|MAX_AGE/);
});

test("career scenario floating controls start outside the dialogue action area", async () => {
  const base = await readFile(new URL("../modules/career/backend/templates/base.html", import.meta.url), "utf8");
  const styles = await readFile(new URL("../modules/career/backend/static/css/style.css", import.meta.url), "utf8");
  assert.match(base, /font-size-pos-scenario-v2/);
  assert.match(base, /localStorage\.setItem\(positionKey/);
  assert.match(styles, /\.page-scenario \.replay-guide-btn\{top:[^}]+bottom:auto\}/);
  assert.match(styles, /\.page-scenario \.font-size-control\{top:[^}]+bottom:auto\}/);
});
