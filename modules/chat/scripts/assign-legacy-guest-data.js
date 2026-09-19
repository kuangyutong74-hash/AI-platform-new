/**
 * scripts/assign-legacy-guest-data.js — 把历史遗留的 guest 数据归到指定账号
 *
 * 背景：
 *   聊天模块修复账号隔离前，所有记录都以 userId="guest" 落盘，
 *   因此修复后登录账号将不再看到这些历史记录（这是正确的隔离行为，
 *   但会让老师和家长以为"数据丢了"）。
 *   本脚本用于一次性把遗留 guest 数据认领给某个账号。
 *
 * 用法（先停掉聊天服务，避免写冲突）：
 *   node scripts/assign-legacy-guest-data.js --account <账号id> --dry-run
 *   node scripts/assign-legacy-guest-data.js --account <账号id> --confirm
 *
 * 账号 id 可从 Core 数据库读取：
 *   sqlite3 modules/platform-core/data/ai_bole_core_v1.db \
 *     "SELECT id,username FROM accounts;"
 *   或者用用户名，脚本会自动去 Core 查（需要 --username）。
 *
 * 备份：默认写入 DATA_DIR/backups/legacy-guest-<时间戳>/。
 */

'use strict';

var fs = require('fs');
var path = require('path');
var { resolveDataDir } = require('../lib/infra/data-dir');
var { accountUserId } = require('../lib/infra/account-identity');

var PROJECT_ROOT = path.resolve(__dirname, '..');
var LEGACY_USER_ID = 'guest';
var ARRAY_FILES = ['history.json', 'journal.json'];
var MAP_FILES = ['tip-favorites.json'];

function parseArgs(argv) {
  var args = { account: '', dryRun: false, confirm: false };
  for (var i = 0; i < argv.length; i += 1) {
    var item = argv[i];
    if (item === '--account') { args.account = argv[i + 1] || ''; i += 1; }
    else if (item === '--dry-run') args.dryRun = true;
    else if (item === '--confirm') args.confirm = true;
  }
  return args;
}

function readJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  } catch (_) {
    return null;
  }
}

function backupFile(filePath, backupDir) {
  if (!fs.existsSync(filePath)) return;
  fs.mkdirSync(backupDir, { recursive: true });
  fs.copyFileSync(filePath, path.join(backupDir, path.basename(filePath)));
}

function main() {
  var args = parseArgs(process.argv.slice(2));
  if (!args.account) {
    console.error('缺少 --account <账号id>；可加 --dry-run 先预览。');
    return 1;
  }
  if (!args.dryRun && !args.confirm) {
    console.error('这是原地改写数据的操作；确认后请加 --confirm，或先加 --dry-run 预览。');
    return 1;
  }

  var dataDir = resolveDataDir({ envValue: process.env.DATA_DIR, projectRoot: PROJECT_ROOT });
  var targetUserId = accountUserId(args.account);
  var timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  var backupDir = path.join(dataDir, 'backups', 'legacy-guest-' + timestamp);
  var plan = [];

  ARRAY_FILES.forEach(function (name) {
    var filePath = path.join(dataDir, name);
    var parsed = readJson(filePath);
    if (!Array.isArray(parsed)) return;
    var moved = 0;
    parsed.forEach(function (entry) {
      if (!entry || entry.userId !== LEGACY_USER_ID) return;
      entry.userId = targetUserId;
      moved += 1;
    });
    if (moved > 0) plan.push({ file: filePath, kind: 'array', data: parsed, moved: moved });
  });

  MAP_FILES.forEach(function (name) {
    var filePath = path.join(dataDir, name);
    var parsed = readJson(filePath);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') return;
    var legacy = parsed[LEGACY_USER_ID];
    if (!Array.isArray(legacy) || legacy.length === 0) return;
    var existing = Array.isArray(parsed[targetUserId]) ? parsed[targetUserId] : [];
    var merged = existing.concat(legacy.filter(function (item) { return existing.indexOf(item) < 0; }));
    parsed[targetUserId] = merged;
    delete parsed[LEGACY_USER_ID];
    plan.push({ file: filePath, kind: 'map', data: parsed, moved: legacy.length });
  });

  if (plan.length === 0) {
    console.log('没有找到需要认领的 guest 数据；DATA_DIR=' + dataDir);
    return 0;
  }

  plan.forEach(function (item) {
    console.log((args.dryRun ? '[dry-run] ' : '[write] ') + path.basename(item.file) + '：' + item.moved + ' 条记录 → ' + targetUserId);
  });

  if (args.dryRun) {
    console.log('预览结束，未写入任何文件。加 --confirm 执行。');
    return 0;
  }

  plan.forEach(function (item) {
    backupFile(item.file, backupDir);
    var tmp = item.file + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(item.data, null, 2), 'utf-8');
    fs.renameSync(tmp, item.file);
  });
  console.log('完成。原文件已备份到：' + backupDir);
  return 0;
}

if (require.main === module) {
  process.exit(main());
}

module.exports = { parseArgs: parseArgs, LEGACY_USER_ID: LEGACY_USER_ID };
