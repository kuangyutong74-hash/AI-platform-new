import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const root = process.cwd();

test('career selection links directly to the illuminated career-island map', () => {
  const html = fs.readFileSync(path.join(root, 'modules/career/backend/templates/career_select.html'), 'utf8');
  assert.match(html, /class="[^"]*\bexperience-map-link\b[^"]*"/);
  assert.match(html, /href="\/my-exploration#exploration-map-title"/);
  assert.match(html, /aria-label="查看职业小岛点亮情况"/);
});

test('the map link does not crowd either in-progress experience toolbar', () => {
  for (const template of ['scenario.html', 'workday.html']) {
    const html = fs.readFileSync(path.join(root, 'modules/career/backend/templates', template), 'utf8');
    assert.doesNotMatch(html, /experience-map-link/);
  }
});

test('the career app asset version invalidates the pre-completion browser cache', () => {
  const html = fs.readFileSync(path.join(root, 'modules/career/backend/templates/base.html'), 'utf8');
  assert.match(html, /\/static\/js\/app\.js\?v=career-voice-toggle-v3/);
});
