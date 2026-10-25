const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');

const html = fs.readFileSync(path.join(__dirname, '..', 'public', 'chat.html'), 'utf8');
const server = fs.readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');

function extractFunction(name) {
  const marker = `function ${name}(`;
  const start = html.indexOf(marker);
  assert.notEqual(start, -1, `${name} should exist`);
  const bodyStart = html.indexOf('{', start);
  let depth = 0;
  for (let index = bodyStart; index < html.length; index += 1) {
    if (html[index] === '{') depth += 1;
    if (html[index] === '}') depth -= 1;
    if (depth === 0) return html.slice(bodyStart, index + 1);
  }
  throw new Error(`${name} body is incomplete`);
}

test('话题气泡只填入表达提示，不代替孩子发送', () => {
  const body = extractFunction('showQuickReplies');
  assert.match(body, /msgInput\.value=topicText/);
  assert.match(body, /msgInput\.focus\(\)/);
  assert.doesNotMatch(body, /sendMessage\(\)/);
});

test('话题文字经过 HTML 转义', () => {
  const body = extractFunction('showQuickReplies');
  assert.match(body, /escapeHTML\(String\(v\)\)/);
});

test('侧栏提示始终是孩子可以输入的第一人称开场白', () => {
  const pool = html.match(/var QUICK_REPLY_POOL=(\[[^\n]+\]);/);
  assert.ok(pool);
  for (const item of JSON.parse(pool[1].replaceAll("'", '"'))) assert.match(item, /^我/);
  const entryChips = [...html.matchAll(/chips:(\[[^\]]+\])/g)];
  assert.equal(entryChips.length, 4);
  for (const [, chips] of entryChips) {
    for (const item of JSON.parse(chips.replaceAll("'", '"'))) assert.match(item, /^我/);
  }
  const compassPrompts = [...html.matchAll(/class="compass-action"[^>]*data-prompt="([^"]+)"/g)];
  assert.equal(compassPrompts.length, 4);
  for (const [, prompt] of compassPrompts) assert.match(prompt, /^我/);
  assert.match(extractFunction('normalizeTopicItem'), /\^我/);
  assert.match(server, /每条必须以“我”开头/);
  assert.match(server, /\^我.*test\(t\.trim\(\)\)/);
});

test('公网 HTTP 页面说明安全上下文要求，避免误导用户修改 localhost 权限', () => {
  assert.match(html, /window\.isSecureContext/);
  assert.match(html, /HTTP 公网地址访问，浏览器不会开放麦克风/);
  assert.doesNotMatch(html, /把 localhost:3000 改为允许/);
});
