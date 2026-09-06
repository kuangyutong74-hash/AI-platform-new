/**
 * test/tip-favorites.test.js — 小知识收藏契约测试
 *
 * 回归测试：tip-favorites.json 曾被写成数组 `[]`，
 * 服务器在数组上挂 userId 键后 JSON.stringify 会静默丢弃，
 * 导致收藏永远无法持久化、"我的收藏"始终为空。
 * 本测试验证：
 *   1. 历史错误结构（数组）会被自愈为 { userId: [tipId...] }
 *   2. 收藏后 GET /api/favorites 能返回完整 tip 数据
 *   3. 取消收藏后列表恢复为空
 */

'use strict';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');

const { httpRequest } = require('./helpers');

// ============================================================
//  设置：临时目录 + 随机端口
// ============================================================

const originalSkipMigration = process.env.SKIP_MIGRATION;
const originalDataDir = process.env.DATA_DIR;

const tempDataDir = fs.mkdtempSync(
  path.join(os.tmpdir(), 'ai-talent-scout-tip-favs-')
);

process.env.SKIP_MIGRATION = 'true';
process.env.DATA_DIR = tempDataDir;

let testPort;
let server;
let serverModule;

before(async function () {
  // 模拟历史错误状态：收藏表被写成数组
  fs.writeFileSync(path.join(tempDataDir, 'tip-favorites.json'), '[]\n', 'utf-8');
  fs.writeFileSync(path.join(tempDataDir, 'tips.json'), '[]\n', 'utf-8');

  serverModule = require('../app');

  testPort = await new Promise(function (resolve, reject) {
    var s = http.createServer(serverModule.app);
    s.listen(0, '127.0.0.1', function () {
      resolve(s.address().port);
    });
    s.on('error', reject);
    server = s;
  });
});

after(function () {
  if (server) { try { server.close(); } catch (_) {} }
  delete require.cache[require.resolve('../app')];
  try { fs.rmSync(tempDataDir, { recursive: true, force: true }); } catch (_) {}

  if (originalSkipMigration === undefined) {
    delete process.env.SKIP_MIGRATION;
  } else {
    process.env.SKIP_MIGRATION = originalSkipMigration;
  }
  if (originalDataDir === undefined) {
    delete process.env.DATA_DIR;
  } else {
    process.env.DATA_DIR = originalDataDir;
  }
});

// ============================================================
//  测试
// ============================================================

describe('小知识收藏（/api/favorites）', function () {

  it('历史数组结构会被自愈为对象结构', async function () {
    var res = await httpRequest('/api/favorites', { port: testPort });
    assert.strictEqual(res.status, 200);
    assert.deepStrictEqual(res.body, []);

    // 第一次读取后，文件应已被写回为对象结构
    var raw = fs.readFileSync(path.join(tempDataDir, 'tip-favorites.json'), 'utf-8');
    var parsed = JSON.parse(raw);
    assert.ok(!Array.isArray(parsed) && typeof parsed === 'object', '收藏表应为 { userId: [...] } 对象');
  });

  it('收藏一条小知识后，"我的收藏"能返回完整数据', async function () {
    var addRes = await httpRequest('/api/favorites', {
      method: 'POST',
      port: testPort,
      data: {
        id: 'disc-测试小知识',
        action: 'add',
        title: '测试小知识',
        text: '这是一条用于测试收藏的小知识。',
        cat: 'nature',
        emoji: '🌱',
      },
    });
    assert.strictEqual(addRes.status, 200);
    assert.deepStrictEqual(addRes.body, ['disc-测试小知识']);

    // 收藏列表返回完整 tip 数据（而不是只有 id）
    var listRes = await httpRequest('/api/favorites', { port: testPort });
    assert.strictEqual(listRes.status, 200);
    assert.strictEqual(listRes.body.length, 1);
    assert.strictEqual(listRes.body[0].id, 'disc-测试小知识');
    assert.strictEqual(listRes.body[0].title, '测试小知识');
    assert.strictEqual(listRes.body[0].text, '这是一条用于测试收藏的小知识。');
    assert.strictEqual(listRes.body[0].emoji, '🌱');
  });

  it('收藏记录真正持久化到磁盘（对象结构 + guest 列表）', async function () {
    var raw = fs.readFileSync(path.join(tempDataDir, 'tip-favorites.json'), 'utf-8');
    var parsed = JSON.parse(raw);
    assert.deepStrictEqual(parsed, { guest: ['disc-测试小知识'] });

    // tip 数据也已落盘
    var tipsRaw = fs.readFileSync(path.join(tempDataDir, 'tips.json'), 'utf-8');
    var tips = JSON.parse(tipsRaw);
    assert.strictEqual(tips.length, 1);
    assert.strictEqual(tips[0].id, 'disc-测试小知识');
  });

  it('取消收藏后列表恢复为空', async function () {
    var rmRes = await httpRequest('/api/favorites', {
      method: 'POST',
      port: testPort,
      data: { id: 'disc-测试小知识', action: 'remove' },
    });
    assert.strictEqual(rmRes.status, 200);
    assert.deepStrictEqual(rmRes.body, []);

    var listRes = await httpRequest('/api/favorites', { port: testPort });
    assert.deepStrictEqual(listRes.body, []);
  });

  it('缺少 id 或 action 时返回 400', async function () {
    var res = await httpRequest('/api/favorites', {
      method: 'POST',
      port: testPort,
      data: { action: 'add' },
    });
    assert.strictEqual(res.status, 400);
  });
});
