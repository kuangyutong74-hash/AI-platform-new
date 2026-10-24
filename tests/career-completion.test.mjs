import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const root = process.cwd();
const read = relative => fs.readFileSync(path.join(root, relative), 'utf8');

test('career completion is persisted before the success screen opens', () => {
  const frontend = read('modules/career/backend/static/js/app.js');
  const completion = frontend.slice(
    frontend.indexOf('async showCompletion()'),
    frontend.indexOf('  hideAll()', frontend.indexOf('async showCompletion()')),
  );
  assert.match(completion, /\/api\/session\/[^'"+]+.*\/complete/);
  assert.ok(
    completion.indexOf('/complete') < completion.indexOf("this.state='complete'"),
    'the backend completion request must finish before the UI claims success',
  );
});

test('career completion endpoint verifies every scenario has a choice', () => {
  const backend = read('modules/career/backend/main.py');
  const route = backend.slice(
    backend.indexOf('@app.post("/api/session/{session_id}/complete")'),
    backend.indexOf('# === API:', backend.indexOf('@app.post("/api/session/{session_id}/complete")') + 1),
  );
  assert.match(route, /completed_indices/);
  assert.match(route, /len\(completed_indices\) != total/);
  assert.match(route, /session\.status = "completed"/);
  assert.match(route, /session\.completed_at/);
});
