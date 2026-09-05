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
