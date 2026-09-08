var test = require('node:test');
var assert = require('node:assert/strict');
var fs = require('node:fs');
var path = require('node:path');

var html = fs.readFileSync(path.join(__dirname, '..', 'public', 'chat.html'), 'utf8');

test('互动卡只在三个主题入口之后、正式聊天之前运行', function () {
  assert.match(html, /var PRE_CHAT_PLANS=/);
  assert.match(html, /if\(key==='free'\)openConversationFromEntry\(key,''\);else startPreChatFlow\(key\)/);
  assert.doesNotMatch(html, /maybeOfferInteractiveTask/);
});

test('故事、观察和职业入口拥有不同的小卡内容', function () {
  assert.match(html, /故事从哪里开始/);
  assert.match(html, /你想先观察什么/);
  assert.match(html, /什么样的工作吸引你/);
  assert.match(html, /安排你的体验路线/);
});

test('三个主题入口都固定完成三轮互动', function () {
  var plansSource = html.slice(html.indexOf('var PRE_CHAT_PLANS='), html.indexOf('function startPreChatFlow'));
  ['story', 'deepsea', 'career'].forEach(function (key, index, keys) {
    var start = plansSource.indexOf(key + ':{');
    var next = index < keys.length - 1 ? plansSource.indexOf(keys[index + 1] + ':{', start) : plansSource.length;
    var plan = plansSource.slice(start, next);
    assert.equal((plan.match(/type:'/g) || []).length, 3, key + ' 入口应有三轮互动');
  });
  assert.match(html, /前三个入口会先玩 3 张小卡/);
});

test('三个主题入口都把孩子自由补句放在第三轮', function () {
  var plansSource = html.slice(html.indexOf('var PRE_CHAT_PLANS='), html.indexOf('function startPreChatFlow'));
  ['story', 'deepsea', 'career'].forEach(function (key, index, keys) {
    var start = plansSource.indexOf(key + ':{');
    var next = index < keys.length - 1 ? plansSource.indexOf(keys[index + 1] + ':{', start) : plansSource.length;
    var plan = plansSource.slice(start, next);
    assert.ok(plan.lastIndexOf("type:'sentence_completion'") > plan.lastIndexOf("type:'picture_choice'"), key + ' 的自由补句应在选择题之后');
    assert.ok(plan.lastIndexOf("type:'sentence_completion'") > plan.lastIndexOf("type:'sequence_order'"), key + ' 的自由补句应是第三轮');
  });
});

test('完成前置小卡后，选择会组成正式聊天的开场内容', function () {
  assert.match(html, /opening=flow\.responses\.join\('；'\)/);
  assert.match(html, /openConversationFromEntry\(flow\.key,opening\+'。'\)/);
  assert.match(html, /interactionActivities\.push\(currentTask\)/);
  assert.doesNotMatch(html, /preChatWelcome/);
});

test('小新通过模型自然重述互动线索，不在前端直接复述', function () {
  assert.match(html, /if\(openingText\)\{msgInput\.value=openingText;sendMessage\(\)\}/);
});
