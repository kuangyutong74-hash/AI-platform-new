const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');

const html = fs.readFileSync(path.join(__dirname, '..', 'public', 'chat.html'), 'utf8');

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
