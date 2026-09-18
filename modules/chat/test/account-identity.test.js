'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  _resolveRequestUserId: resolveRequestUserId,
  _userSessionKey: userSessionKey,
} = require('../app');

test('没有平台会话 Cookie 时使用 guest，且不请求 Core', async function () {
  let called = false;
  const userId = await resolveRequestUserId('', async function () {
    called = true;
    throw new Error('不应调用');
  });

  assert.equal(userId, 'guest');
  assert.equal(called, false);
});

test('登录学生使用 selected_student.id', async function () {
  const userId = await resolveRequestUserId(
    'theme=night; ai_bole_session=token-a',
    async function (url, init) {
      assert.match(url, /\/api\/account\/me$/);
      assert.equal(init.headers.Cookie, 'theme=night; ai_bole_session=token-a');
      return {
        ok: true,
        json: async function () {
          return {
            account: { id: 'adult-1' },
            selected_student: { id: 'student-7' },
          };
        },
      };
    }
  );

  assert.equal(userId, 'student-7');
});

test('没有选中学生时回退到 account.id', async function () {
  const userId = await resolveRequestUserId(
    'ai_bole_session=token-b',
    async function () {
      return {
        ok: true,
        json: async function () {
          return { account: { id: 'student-2' }, selected_student: null };
        },
      };
    }
  );

  assert.equal(userId, 'student-2');
});

test('无效会话或 Core 异常时安全回退 guest', async function () {
  const unauthorized = await resolveRequestUserId(
    'ai_bole_session=expired',
    async function () { return { ok: false }; }
  );
  const unavailable = await resolveRequestUserId(
    'ai_bole_session=valid-looking',
    async function () { throw new Error('Core unavailable'); }
  );

  assert.equal(unauthorized, 'guest');
  assert.equal(unavailable, 'guest');
});

test('相同 sessionId 在不同账号下使用不同内存键', function () {
  assert.notEqual(
    userSessionKey('student-a', 'session-1'),
    userSessionKey('student-b', 'session-1')
  );
});
