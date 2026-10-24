import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

test("career narration uses a warm neural voice profile with cache-busting prosody", async () => {
  const backend = await readFile(new URL("../modules/career/backend/main.py", import.meta.url), "utf8");
  const requirements = await readFile(new URL("../modules/career/backend/requirements.txt", import.meta.url), "utf8");
  assert.match(requirements, /^edge-tts==7\.3\.1$/m);
  assert.match(backend, /"mentor": \{"voice": "zh-CN-XiaoxiaoNeural"/);
  assert.match(backend, /pitch=pitch, volume=volume/);
  assert.match(backend, /voice\}\|\{rate\}\|\{pitch\}\|\{volume\}/);
  assert.match(backend, /target\.stat\(\)\.st_size == 0/);
  assert.match(backend, /pending\.replace\(target\)/);
  assert.match(backend, /pending\.unlink\(\)/);
  assert.match(backend, /target\.exists\(\) and target\.stat\(\)\.st_size == 0/);
});

test("career reader speaks with Chinese punctuation and a natural local fallback pace", async () => {
  const client = await readFile(new URL("../modules/career/backend/static/js/app.js", import.meta.url), "utf8");
  assert.match(client, /d\.speaker\+'说：'\+d\.text/);
  assert.match(client, /'。请听选项：'/);
  assert.match(client, /utterance\.rate=\.94/);
  assert.doesNotMatch(client, /d\.speaker\+'\?'\+d\.text/);
  const base = await readFile(new URL("../modules/career/backend/templates/base.html", import.meta.url), "utf8");
  assert.match(base, /app\.js\?v=career-voice-toggle-v3/);
});

test('career reader toggles play, pause and resume without restarting narration', async () => {
  const client = await readFile(new URL("../modules/career/backend/static/js/app.js", import.meta.url), "utf8");
  assert.match(client, /onclick=\(\)=>this\.toggleCurrentNarration\(\)/);
  assert.match(client, /this\.voicePlaybackState==='playing'/);
  assert.match(client, /this\.ttsAudio\.pause\(\)/);
  assert.match(client, /window\.speechSynthesis\.pause\(\)/);
  assert.match(client, /this\.voicePlaybackState==='paused'/);
  assert.match(client, /this\.ttsAudio\.play\(\)/);
  assert.match(client, /window\.speechSynthesis\.resume\(\)/);
  assert.match(client, /playing:'暂停',paused:'继续'/);
});
