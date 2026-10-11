import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const root = process.cwd();
const read = relative => fs.readFileSync(path.join(root, relative), 'utf8');

test('career pinyin control is provided by the shared layout', () => {
  const base = read('modules/career/backend/templates/base.html');
  assert.match(base, /id="career-pinyin-toggle"/);
  assert.match(base, /global-pinyin\.css/);
  assert.match(base, /global-pinyin\.js/);
  assert.match(base, /pinyin-pro\.js/);
});

test('workday no longer owns a page-local pinyin control', () => {
  const template = read('modules/career/backend/templates/workday.html');
  const script = read('modules/career/backend/static/js/workday.js');
  assert.doesNotMatch(template, /wd-pinyin-toggle|workday-pinyin\.css/);
  assert.doesNotMatch(script, /initPinyinAssist\(\)|applyPinyinAssist\(\)/);
});

test('global helper persists and annotates dynamic content', () => {
  const script = read('modules/career/backend/static/js/global-pinyin.js');
  assert.match(script, /career-pinyin-enabled/);
  assert.match(script, /career-workday-pinyin/);
  assert.match(script, /new MutationObserver/);
  assert.match(script, /pinyin\(text/);
});
