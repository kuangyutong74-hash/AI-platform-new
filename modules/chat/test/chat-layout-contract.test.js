/**
 * 聊天页布局静态合同：返回入口应位于顶部导航，不能悬浮遮挡聊天文字。
 */
'use strict';

var { describe, it } = require('node:test');
var assert = require('node:assert/strict');
var fs = require('fs');
var path = require('path');

var chatHtml = fs.readFileSync(path.join(__dirname, '..', 'public', 'chat.html'), 'utf-8');

describe('chat return control layout', function () {
  it('keeps the return action in the top navigation', function () {
    assert.ok(chatHtml.includes('id="btnReturnPlanet"'));
    assert.ok(chatHtml.includes("btnReturnPlanet.addEventListener('click'"));
  });

  it('does not render the obsolete floating return control', function () {
    assert.strictEqual(chatHtml.includes('platform-return'), false);
    assert.strictEqual(chatHtml.includes('platformReturnLink'), false);
  });
});
