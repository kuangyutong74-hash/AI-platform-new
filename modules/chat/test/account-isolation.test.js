/**
 * test/account-isolation.test.js — 聊天观察账号隔离回归测试
 *
 * 背景（线上问题）：
 *   app.js 的 guestIdentity 曾把 req.userId 写死为 'guest'，
 *   所有浏览器、所有账号共用同一份 history.json。
 *   本地单人开发无感，部署到服务器后任何账号打开"聊天观察"
 *   都会看到别人的对话历史。
 *
 * 本测试用本地假 Core（/api/account/me）验证：
 *   1. 同一 Cookie → 只看到自己的记录
 *   2. 不同账号 Cookie → 互相看不到对方的记录
 *   3. 没有 Cookie（直接打开模块）→ guest 身份，看不到账号记录
 *   4. 其他账号无法用 convId 覆盖/续写别人的记录
 *   5. 关闭隔离开关时回退到旧的单一 guest 行为
 */

'use strict';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const http = require('http');
const os = require('os');
const path = require('path');

const { httpRequest, cleanup } = require('./helpers');

// node:test 的每个测试文件都是一个子进程，结果通过 stdout 回传。
// app.js 的"结束流程"/history 日志量较大，在整包高并发运行时实测会与结果通道
// 互相干扰（父进程报 `Unable to deserialize cloned data`，文件级测试被误判失败）。
// 本文件只验证 HTTP 行为，静音这些业务日志；失败信息仍走 stderr 保留。
const _originalConsoleLog = console.log;
console.log = function () {};

// ============================================================
//  临时数据目录
// ============================================================
const originalDataDir = process.env.DATA_DIR;
const originalCoreUrl = process.env.AI_BOLE_CORE_URL;
const originalIsolation = process.env.AI_BOLE_CHAT_ACCOUNT_ISOLATION;

const tempDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ai-chat-account-iso-'));
process.env.DATA_DIR = tempDataDir;
process.env.SKIP_MIGRATION = 'true';

// ============================================================
//  假 Core：cookie token → 账号 id
// ============================================================
const ACCOUNTS = {
  'token-student-a': 'acct-id-student-a',
  'token-student-b': 'acct-id-student-b',
};

let fakeCore;
let fakeCoreUrl;
let server;
let testPort;
let serverModule;

before(async function () {
  fakeCore = http.createServer(function (req, res) {
    if (req.url !== '/api/account/me') {
      res.writeHead(404).end();
      return;
    }
    const cookie = String(req.headers.cookie || '');
    const match = /(?:^|;\s*)ai_bole_session=([^;]+)/.exec(cookie);
    const token = match ? match[1] : '';
    const accountId = ACCOUNTS[token];
    if (!accountId) {
      res.writeHead(401, { 'Content-Type': 'application/json' }).end(JSON.stringify({ detail: '登录状态已失效' }));
      return;
    }
    res.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify({
      account: { id: accountId, username: token, display_name: token, age: 9, role: 'student' },
    }));
  });
  await new Promise(function (resolve) { fakeCore.listen(0, '127.0.0.1', resolve); });
  fakeCoreUrl = 'http://127.0.0.1:' + fakeCore.address().port;

  process.env.AI_BOLE_CORE_URL = fakeCoreUrl;

  serverModule = require('../app');
  testPort = await new Promise(function (resolve, reject) {
    const s = http.createServer(serverModule.app);
    s.listen(0, '127.0.0.1', function () { resolve(s.address().port); });
    s.on('error', reject);
    server = s;
  });
});

after(function () {
  console.log = _originalConsoleLog;
  if (server) { try { server.close(); } catch (_) {} }
  if (fakeCore) { try { fakeCore.close(); } catch (_) {} }
  delete require.cache[require.resolve('../app')];
  cleanup(tempDataDir);

  if (originalDataDir === undefined) delete process.env.DATA_DIR; else process.env.DATA_DIR = originalDataDir;
  if (originalCoreUrl === undefined) delete process.env.AI_BOLE_CORE_URL; else process.env.AI_BOLE_CORE_URL = originalCoreUrl;
  if (originalIsolation === undefined) delete process.env.AI_BOLE_CHAT_ACCOUNT_ISOLATION; else process.env.AI_BOLE_CHAT_ACCOUNT_ISOLATION = originalIsolation;
});

// ============================================================
//  小工具
// ============================================================
function cookieFor(token) {
  return { Cookie: 'ai_bole_session=' + token };
}

function conversation(sessionId, text) {
  return {
    sessionId: sessionId,
    turnCount: 1,
    weather: '晴天',
    // completed=false：只验证账号归属与隔离，不触发后台 analysis/journal 管线。
    // 那些后台任务会在测试结束时继续打印日志，可能干扰 node:test 的结果通道。
    completed: false,
    messages: [
      { role: 'user', content: text },
      { role: 'assistant', content: '我在听。' },
    ],
  };
}

function readRawHistory() {
  return JSON.parse(fs.readFileSync(path.join(tempDataDir, 'history.json'), 'utf-8'));
}

// ============================================================
//  账号隔离
// ============================================================
describe('聊天观察账号隔离', function () {

  it('学生 A 保存的对话能自己读到', async function () {
    const saved = await httpRequest('/api/history', {
      method: 'POST', port: testPort, headers: cookieFor('token-student-a'),
      data: conversation('sess-a-1', '我今天在学校踢了足球'),
    });
    assert.strictEqual(saved.status, 200);

    const list = await httpRequest('/api/history', { port: testPort, headers: cookieFor('token-student-a') });
    assert.strictEqual(list.status, 200);
    assert.ok(Array.isArray(list.body), '历史列表应为数组');
    assert.strictEqual(list.body.length, 1, '学生 A 应只看到自己的 1 条记录');
    assert.match(list.body[0].preview, /足球/);
  });

  it('学生 B 看不到学生 A 的历史记录', async function () {
    const list = await httpRequest('/api/history', { port: testPort, headers: cookieFor('token-student-b') });
    assert.strictEqual(list.status, 200);
    assert.deepStrictEqual(list.body, [], '学生 B 不应看到学生 A 的记录');
  });

  it('未登录（无 Cookie）访问时为 guest，同样看不到账号记录', async function () {
    const list = await httpRequest('/api/history', { port: testPort });
    assert.strictEqual(list.status, 200);
    assert.deepStrictEqual(list.body, [], 'guest 不应看到任何账号记录');
  });

  it('落盘记录的 userId 为 acct:<账号id>，不再是统一的 guest', async function () {
    const raw = readRawHistory();
    assert.strictEqual(raw.length, 1);
    assert.strictEqual(raw[0].userId, 'acct:acct-id-student-a');
  });

  it('学生 B 用学生 A 的 convId 自动保存时不会覆盖 A 的记录', async function () {
    const rawBefore = readRawHistory();
    const targetId = rawBefore[0].id;

    const res = await httpRequest('/api/history/auto-save', {
      method: 'PUT', port: testPort, headers: cookieFor('token-student-b'),
      data: { sessionId: 'sess-b-x', convId: targetId, turnCount: 1, messages: [{ role: 'user', content: '我要覆盖别人的记录' }] },
    });
    assert.strictEqual(res.status, 200);

    const rawAfter = readRawHistory();
    const aRecord = rawAfter.find(function (item) { return item.id === targetId; });
    assert.ok(aRecord, '学生 A 的记录应仍然存在');
    assert.strictEqual(aRecord.userId, 'acct:acct-id-student-a', 'A 的记录归属不能被改写');
    assert.match(aRecord.messages[0].content, /足球/, 'A 的消息内容不能被覆盖');

    const listA = await httpRequest('/api/history', { port: testPort, headers: cookieFor('token-student-a') });
    assert.strictEqual(listA.body.length, 1, '学生 A 仍然只有自己的 1 条记录');

    const listB = await httpRequest('/api/history', { port: testPort, headers: cookieFor('token-student-b') });
    assert.strictEqual(listB.body.length, 1, '学生 B 的覆盖请求应落成自己的新记录');
    assert.match(listB.body[0].preview, /覆盖/);
  });

  it('学生 B 不能读取学生 A 的单条对话详情', async function () {
    const targetId = readRawHistory().find(function (item) { return item.userId === 'acct:acct-id-student-a'; }).id;
    const denied = await httpRequest('/api/history/' + encodeURIComponent(targetId), { port: testPort, headers: cookieFor('token-student-b') });
    assert.strictEqual(denied.status, 404, '越权读取应返回 404');

    const allowed = await httpRequest('/api/history/' + encodeURIComponent(targetId), { port: testPort, headers: cookieFor('token-student-a') });
    assert.strictEqual(allowed.status, 200);
  });

  it('学生 B 不能删除学生 A 的记录', async function () {
    const targetId = readRawHistory().find(function (item) { return item.userId === 'acct:acct-id-student-a'; }).id;
    await httpRequest('/api/history/' + encodeURIComponent(targetId), { method: 'DELETE', port: testPort, headers: cookieFor('token-student-b') });
    const stillThere = readRawHistory().some(function (item) { return item.id === targetId; });
    assert.ok(stillThere, 'A 的记录不应被 B 删除');
  });

  it('收藏也按账号隔离', async function () {
    await httpRequest('/api/tips/favorites', {
      method: 'POST', port: testPort, headers: cookieFor('token-student-a'),
      data: { id: 'disc-测试小知识', action: 'add' },
    });
    const favA = await httpRequest('/api/tips/favorites', { port: testPort, headers: cookieFor('token-student-a') });
    const favB = await httpRequest('/api/tips/favorites', { port: testPort, headers: cookieFor('token-student-b') });
    assert.deepStrictEqual(favA.body, ['disc-测试小知识']);
    assert.deepStrictEqual(favB.body, [], '学生 B 不应看到学生 A 的收藏');
  });

});

// ============================================================
//  解析器单元行为
// ============================================================
describe('账号身份解析器', function () {

  it('关闭隔离开关时整体回退到 guest', async function () {
    const { createAccountResolver } = require('../lib/infra/account-identity');
    const resolver = createAccountResolver({ enabled: false, coreUrl: fakeCoreUrl });
    const identity = await resolver.resolve('ai_bole_session=token-student-a');
    assert.strictEqual(identity.userId, 'guest');
    assert.strictEqual(identity.source, 'disabled');
  });

  it('Core 不可达时回退到 guest，不抛异常', async function () {
    const { createAccountResolver } = require('../lib/infra/account-identity');
    const resolver = createAccountResolver({ coreUrl: 'http://127.0.0.1:1', timeoutMs: 300 });
    const identity = await resolver.resolve('ai_bole_session=whatever');
    assert.strictEqual(identity.userId, 'guest');
    assert.strictEqual(identity.source, 'unresolved');
  });

  it('Cookie 解析支持带空格与引号的形式', function () {
    const { parseCookie } = require('../lib/infra/account-identity');
    assert.strictEqual(parseCookie('a=1; ai_bole_session=token-student-a; b=2', 'ai_bole_session'), 'token-student-a');
    assert.strictEqual(parseCookie('ai_bole_session="token-student-b"', 'ai_bole_session'), 'token-student-b');
    assert.strictEqual(parseCookie('', 'ai_bole_session'), null);
    assert.strictEqual(parseCookie(undefined, 'ai_bole_session'), null);
  });

});
