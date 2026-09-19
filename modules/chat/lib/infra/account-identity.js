/**
 * lib/infra/account-identity.js — 聊天模块的账号身份解析
 *
 * 背景：
 *   聊天模块长期使用固定的 "guest" 身份（app.js 里的 guestIdentity 直接写死
 *   req.userId = 'guest'）。所有浏览器、所有账号共用同一份
 *   history.json / journal.json / tip-favorites.json。
 *   本地单人开发时看不出来，部署到服务器后任何账号打开"聊天观察"
 *   都会看到别人的对话记录，也就是"历史记录不属于当前账号"。
 *
 * 解决方式：
 *   1. 读取请求 Cookie 中的统一账号会话（默认 ai_bole_session）；
 *      统一账号 Cookie 不带 Domain，仅绑定主机名，因此同一主机的
 *      不同端口（4173 Portal / 8020 Core / 3000 聊天）共享同一会话；
 *   2. 向 Core 的 GET /api/account/me 换取账号；
 *   3. 用 "acct:<account_id>" 作为 userId，实现按账号隔离；
 *   4. 没有 Cookie / Core 不可达 / 会话失效 → 回退到 "guest"，
 *      保持"直接打开模块也能体验"的独立模式。
 *
 * 约束：
 *   - 任何失败都不抛异常，账号服务故障不能拖垮聊天主链路；
 *   - 使用 Node 内置 http/https，不走 global.fetch，
 *     避免被测试里的网络守卫（test/helpers.js）干扰；
 *   - 结果带 TTL 内存缓存，避免每个请求都打一次 Core。
 *
 * 可用环境变量：
 *   AI_BOLE_CORE_URL             Core 地址，默认 http://localhost:8020
 *   CORE_API_URL                 同上（兼容 Portal 的命名）
 *   AI_BOLE_SESSION_COOKIE       会话 Cookie 名，默认 ai_bole_session
 *   AI_BOLE_IDENTITY_TTL_MS      解析结果缓存时长，默认 60000
 *   AI_BOLE_IDENTITY_TIMEOUT_MS  单次解析超时，默认 1500
 *   AI_BOLE_CHAT_ACCOUNT_ISOLATION
 *                                设为 0/false/no/off 可整体关闭隔离，回到单一 guest
 */

'use strict';

var http = require('http');
var https = require('https');
var url = require('url');

var DEFAULT_COOKIE_NAME = 'ai_bole_session';
var DEFAULT_CORE_URL = 'http://localhost:8020';
var DEFAULT_TTL_MS = 60000;
var DEFAULT_TIMEOUT_MS = 1500;
var DEFAULT_MAX_ENTRIES = 500;

/** 未登录 / 无法解析时的身份 */
var GUEST_USER_ID = 'guest';
/** 账号身份前缀，避免与历史遗留的 'guest' 或任意自定义 userId 混淆 */
var ACCOUNT_PREFIX = 'acct:';

/**
 * 把 Core 账号 ID 转成聊天模块使用的 userId。
 * @param {string} accountId
 * @returns {string}
 */
function accountUserId(accountId) {
  return ACCOUNT_PREFIX + String(accountId);
}

/**
 * 从 Cookie 请求头中取出指定 Cookie 的值。
 * @param {string|undefined} header
 * @param {string} name
 * @returns {string|null}
 */
function parseCookie(header, name) {
  if (typeof header !== 'string' || header.length === 0) return null;
  var parts = header.split(';');
  for (var i = 0; i < parts.length; i += 1) {
    var part = parts[i];
    var eq = part.indexOf('=');
    if (eq < 0) continue;
    if (part.slice(0, eq).trim() !== name) continue;
    var raw = part.slice(eq + 1).trim();
    if (raw.length >= 2 && raw.charAt(0) === '"' && raw.charAt(raw.length - 1) === '"') {
      raw = raw.slice(1, -1);
    }
    // 我们的 Cookie 值由 Core 直接写入，未做 URL 编码；容错处理编码形式
    if (/%[0-9A-Fa-f]{2}/.test(raw)) {
      try { return decodeURIComponent(raw); } catch (_) { return raw; }
    }
    return raw;
  }
  return null;
}

/**
 * 用 Node 内置 http/https 发一个 GET，返回解析后的 JSON；失败返回 null。
 * @param {string} targetUrl
 * @param {string} cookieHeader
 * @param {number} timeoutMs
 * @returns {Promise<object|null>}
 */
function getJson(targetUrl, cookieHeader, timeoutMs) {
  return new Promise(function (resolve) {
    var parsed;
    try {
      parsed = new url.URL(targetUrl);
    } catch (_) {
      resolve(null);
      return;
    }
    var transport = parsed.protocol === 'https:' ? https : http;
    var settled = false;
    function done(value) {
      if (settled) return;
      settled = true;
      resolve(value);
    }
    var request = transport.request(
      {
        protocol: parsed.protocol,
        hostname: parsed.hostname,
        port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
        path: parsed.pathname + parsed.search,
        method: 'GET',
        headers: { Cookie: cookieHeader, Accept: 'application/json' },
      },
      function (response) {
        var body = '';
        response.setEncoding('utf-8');
        response.on('data', function (chunk) { body += chunk; });
        response.on('end', function () {
          if (response.statusCode < 200 || response.statusCode >= 300) {
            done(null);
            return;
          }
          try {
            done(JSON.parse(body));
          } catch (_) {
            done(null);
          }
        });
      }
    );
    request.setTimeout(timeoutMs, function () {
      request.destroy();
      done(null);
    });
    request.on('error', function () { done(null); });
    request.end();
  });
}

/**
 * 依据环境变量解析布尔开关（0/false/no/off 视为关闭）。
 * @param {string|undefined} value
 * @param {boolean} fallback
 * @returns {boolean}
 */
function readBooleanEnv(value, fallback) {
  if (value === undefined || value === null || String(value).trim() === '') return fallback;
  return ['0', 'false', 'no', 'off'].indexOf(String(value).trim().toLowerCase()) < 0;
}

/**
 * 创建账号身份解析器。
 *
 * @param {object} [options]
 * @param {string}   [options.cookieName]  会话 Cookie 名
 * @param {string}   [options.coreUrl]     Core 基地址
 * @param {number}   [options.ttlMs]       缓存时长
 * @param {number}   [options.timeoutMs]   单次请求超时
 * @param {number}   [options.maxEntries]  缓存条数上限
 * @param {boolean}  [options.enabled]     是否启用账号隔离
 * @param {Function} [options.requestJson] 自定义取数函数（测试注入）
 * @param {Function} [options.now]         自定义时钟（测试注入）
 * @returns {{resolve: Function, cookieName: string, coreUrl: string, enabled: boolean}}
 */
function createAccountResolver(options) {
  var opts = options || {};
  var cookieName = opts.cookieName || DEFAULT_COOKIE_NAME;
  var coreUrl = String(opts.coreUrl || DEFAULT_CORE_URL).replace(/\/+$/, '');
  var ttlMs = Number.isFinite(opts.ttlMs) && opts.ttlMs >= 0 ? opts.ttlMs : DEFAULT_TTL_MS;
  var timeoutMs = Number.isFinite(opts.timeoutMs) && opts.timeoutMs > 0 ? opts.timeoutMs : DEFAULT_TIMEOUT_MS;
  var maxEntries = Number.isFinite(opts.maxEntries) && opts.maxEntries > 0 ? opts.maxEntries : DEFAULT_MAX_ENTRIES;
  var requestJson = typeof opts.requestJson === 'function'
    ? opts.requestJson
    : function (target, cookieHeader) { return getJson(target, cookieHeader, timeoutMs); };
  var now = typeof opts.now === 'function' ? opts.now : Date.now;
  var enabled = opts.enabled !== false;

  // token → { userId, accountId, expiresAt }
  var cache = new Map();

  function cacheGet(token) {
    var hit = cache.get(token);
    if (!hit) return null;
    if (hit.expiresAt <= now()) {
      cache.delete(token);
      return null;
    }
    // LRU：命中后重新插入，保持最近使用的在尾部
    cache.delete(token);
    cache.set(token, hit);
    return hit;
  }

  /**
   * @param {string} token
   * @param {string|null} accountId
   * @param {string} userId
   */
  function cacheSet(token, accountId, userId) {
    if (ttlMs <= 0) return;
    if (cache.has(token)) cache.delete(token);
    cache.set(token, {
      accountId: accountId,
      userId: userId,
      expiresAt: now() + ttlMs,
    });
    while (cache.size > maxEntries) {
      var oldest = cache.keys().next();
      if (oldest.done) break;
      cache.delete(oldest.value);
    }
  }

  /**
   * 解析请求身份。
   * @param {string|undefined} cookieHeader 请求的 Cookie 头
   * @returns {Promise<{userId: string, accountId: string|null, source: string}>}
   */
  async function resolve(cookieHeader) {
    if (!enabled) return { userId: GUEST_USER_ID, accountId: null, source: 'disabled' };

    var token = parseCookie(cookieHeader, cookieName);
    if (!token) return { userId: GUEST_USER_ID, accountId: null, source: 'anonymous' };

    var cached = cacheGet(token);
    if (cached) {
      return { userId: cached.userId, accountId: cached.accountId, source: 'cache' };
    }

    var payload = await requestJson(coreUrl + '/api/account/me', cookieName + '=' + token);
    var subject = payload && (payload.selected_student || payload.account);
    var accountId = subject && typeof subject.id === 'string'
      ? subject.id
      : null;
    if (!accountId) {
      // 有会话但 Core 不可达或会话失效时保持 unresolved，交给中间件拒绝写入，
      // 不能缓存成 guest，否则后续请求可能落入共享访客数据。
      return { userId: GUEST_USER_ID, accountId: null, source: 'unresolved' };
    }

    cacheSet(token, accountId, accountUserId(accountId));
    return { userId: accountUserId(accountId), accountId: accountId, source: 'account' };
  }

  return {
    resolve: resolve,
    cookieName: cookieName,
    coreUrl: coreUrl,
    enabled: enabled,
    _cacheSize: function () { return cache.size; },
  };
}

module.exports = {
  createAccountResolver: createAccountResolver,
  accountUserId: accountUserId,
  parseCookie: parseCookie,
  readBooleanEnv: readBooleanEnv,
  GUEST_USER_ID: GUEST_USER_ID,
  ACCOUNT_PREFIX: ACCOUNT_PREFIX,
  DEFAULT_COOKIE_NAME: DEFAULT_COOKIE_NAME,
  DEFAULT_CORE_URL: DEFAULT_CORE_URL,
};
