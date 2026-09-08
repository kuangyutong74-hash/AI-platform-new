/**
 * v2-turn-runner.js — V2 单轮对话执行器
 *
 * 纯编排模块。协调 conversation-state、analyze-event-adapter、
 * runtime-state、response-validator 完成单轮 V2 对话。
 *
 * 不读文件、不访问网络、不调用模型。所有模型调用通过
 * 依赖注入的 async 回调完成。
 *
 * 导出：
 *   runV2Turn(input) → { finalReply, nextState, analysis, validation, ... }
 */

'use strict';

var cs = require('./conversation-state');
var adapter = require('./analyze-event-adapter');
var rs = require('../infra/runtime-state');
var validator = require('./response-validator');

// ============================================================
//  确定性 fallback 回复
// ============================================================

var FALLBACK_CLOSING = '今天说到的这些，小新会好好收进手账里。下次我们可以从这里继续。';
var FALLBACK_BUDGET_ZERO = '我记住你刚才说的这个细节了。想继续时，可以从发生的变化或你最在意的部分往下说。';
var FALLBACK_DEFAULT = '你刚才说的内容里藏着一个很值得展开的细节。要是把镜头停在那一刻，你最想先说说什么？';
var FALLBACK_REFLECTION = '刚才的小任务已经完成了。哪一步最像你自己的想法？';
var FALLBACK_HARD = '我想顺着你刚才的想法继续听下去。你最想先展开哪个细节？';

function selectFallback(stage, questionBudget, studentMessage) {
  if (stage === 'closing') {
    return FALLBACK_CLOSING;
  }

  if (stage === 'reflection') {
    return FALLBACK_REFLECTION;
  }

  if (questionBudget === 0) {
    return FALLBACK_BUDGET_ZERO;
  }

  var message = String(studentMessage || '');
  if (/职业|工作|导师|小任务/.test(message)) {
    return '你已经不只是在想一份工作，还在琢磨遇到困难时人会怎样继续。真正走进工作现场，最有意思的也许正是那些计划之外的时刻。你最想先看看哪个瞬间？';
  }

  if (/故事|伙伴|秘密|发生/.test(message)) {
    return '你已经给故事留出了一扇门，门后还有一个没有揭开的变化。顺着刚才的开场，接下来最可能发生什么？';
  }

  if (/观察|线索|答案|弄明白/.test(message)) {
    return '你不是只想知道答案，还想沿着线索一步步找到它。哪条线索最让你想追下去？';
  }

  return FALLBACK_DEFAULT;
}

// ============================================================
//  辅助函数
// ============================================================

function isNonArrayObject(value) {
  return Boolean(
    value &&
    typeof value === 'object' &&
    !Array.isArray(value)
  );
}

function isValidReplyText(value) {
  return (
    typeof value === 'string' &&
    value.trim().length > 0
  );
}

function cloneHistory(history) {
  if (!Array.isArray(history)) {
    return [];
  }

  return history.map(function (m) {
    if (!isNonArrayObject(m)) {
      return { role: 'unknown', content: '' };
    }

    return {
      role: String(m.role || 'unknown'),
      content: String(m.content || ''),
    };
  });
}

// ============================================================
//  runV2Turn
// ============================================================

/**
 * 执行一次完整的 V2 单轮对话。
 *
 * @param {object} input
 * @param {object} input.previousState - 上一轮对话状态
 * @param {Array}  input.history - 对话历史
 * @param {string} input.studentMessage - 学生本轮消息
 * @param {Function} input.analyze - async (ctx) => analysisJSON
 * @param {Function} input.generateReply - async (ctx) => replyText
 * @param {Function} [input.repairReply] - async (ctx) => repairText
 * @returns {Promise<object>} 本轮结果
 */
async function runV2Turn(input) {
  if (!isNonArrayObject(input)) {
    throw new Error('runV2Turn: input must be a non-array object');
  }

  var previousState = cs.normalizeConversationState(
    input.previousState
  );

  var history = cloneHistory(input.history);

  var studentMessage =
    typeof input.studentMessage === 'string'
      ? input.studentMessage
      : '';

  var analyze = input.analyze;
  var generateReply = input.generateReply;
  var repairReply = input.repairReply || null;

  if (typeof analyze !== 'function') {
    throw new Error('runV2Turn: analyze must be a function');
  }

  if (typeof generateReply !== 'function') {
    throw new Error('runV2Turn: generateReply must be a function');
  }

  // ---- Step 2: 调用 analyze ----

  var preAdvanceRuntime = rs.serializeRuntimeState(
    previousState
  );

  var analysis = null;

  try {
    analysis = await analyze({
      previousState: previousState,
      history: history,
      studentMessage: studentMessage,
      runtimeState: preAdvanceRuntime,
    });
  } catch (_) {
    // analyze 失败不终止本轮
    analysis = null;
  }

  // ---- Step 4: 构建事件 ----

  var event = adapter.buildConversationEvent({
    previousState: previousState,
    analysis: analysis,
    studentMessage: studentMessage,
  });

  // ---- Step 5: 推进状态 ----

  var advancedState = cs.advanceConversationState(
    previousState,
    event
  );

  // ---- Step 6-7: 序列化 + 生成回复 ----

  var advancedRuntime = rs.serializeRuntimeState(
    advancedState
  );

  var generateCtx = {
    state: advancedState,
    runtimeState: advancedRuntime,
    history: history,
    studentMessage: studentMessage,
    analysis: analysis,
  };

  var rawReply;

  try {
    rawReply = await generateReply(generateCtx);
  } catch (err) {
    // generateReply 抛错 → 直接抛出，不 repair，不返回 nextState
    throw err;
  }

  // ---- Step 8: 校验首次回复 ----

  var repairAttempted = false;
  var repairSucceeded = false;
  var usedFallback = false;

  var finalReply;
  var finalValidation;

  if (!isValidReplyText(rawReply)) {
    // 首次回复无效 → 视为校验失败，尝试 repair
    rawReply = '';
  }

  var initialValidation = validator.validateReply(
    rawReply,
    {
      stage: advancedState.stage,
      question_budget: advancedState.question_budget,
      turn_index: advancedState.turn_index,
      known_facts: advancedState.known_facts,
      student_message: studentMessage,
    }
  );

  if (initialValidation.valid && isValidReplyText(rawReply)) {
    // 首次回复有效 → 直接采用
    finalReply = rawReply;
    finalValidation = initialValidation;
  } else if (repairReply !== null) {
    // 首次无效 → 尝试一次 repair
    repairAttempted = true;

    var errorCodes = initialValidation.errors.map(
      function (e) {
        return e.code;
      }
    );

    var repairCtx = {
      state: advancedState,
      runtimeState: advancedRuntime,
      history: history,
      studentMessage: studentMessage,
      originalReply: rawReply,
      validationErrors: errorCodes,
    };

    var repairedText;

    try {
      repairedText = await repairReply(repairCtx);
    } catch (_) {
      repairedText = null;
    }

    if (isValidReplyText(repairedText)) {
      var repairValidation = validator.validateReply(
        repairedText,
        {
          stage: advancedState.stage,
          question_budget: advancedState.question_budget,
          turn_index: advancedState.turn_index,
          known_facts: advancedState.known_facts,
          student_message: studentMessage,
        }
      );

      if (repairValidation.valid) {
        finalReply = repairedText;
        finalValidation = repairValidation;
        repairSucceeded = true;
      }
    }
  }

  // ---- Step 11-12: fallback ----

  if (!finalReply) {
    usedFallback = true;

    var stageFallback = selectFallback(
      advancedState.stage,
      advancedState.question_budget,
      studentMessage
    );

    var fbValidation = validator.validateReply(
      stageFallback,
      {
        stage: advancedState.stage,
        question_budget: advancedState.question_budget,
        turn_index: advancedState.turn_index,
        known_facts: advancedState.known_facts,
        student_message: studentMessage,
      }
    );

    if (fbValidation.valid) {
      finalReply = stageFallback;
      finalValidation = fbValidation;
    } else {
      // 阶段 fallback 也失败 → 硬 fallback
      var hardFallback = advancedState.question_budget > 0 && advancedState.stage !== 'closing'
        ? FALLBACK_HARD
        : FALLBACK_BUDGET_ZERO;
      var hardValidation = validator.validateReply(
        hardFallback,
        {
          stage: advancedState.stage,
          question_budget: advancedState.question_budget,
          turn_index: advancedState.turn_index,
          known_facts: advancedState.known_facts,
          student_message: studentMessage,
        }
      );

      finalReply = hardFallback;
      finalValidation = hardValidation;
    }
  }

  // ---- Step 13: finalize ----

  var nextState =
    adapter.finalizeConversationStateAfterReply(
      advancedState,
      finalValidation
    );

  return {
    finalReply: finalReply,
    nextState: nextState,
    analysis: analysis,
    validation: finalValidation,
    repairAttempted: repairAttempted,
    repairSucceeded: repairSucceeded,
    usedFallback: usedFallback,
  };
}

// ============================================================
//  导出
// ============================================================

module.exports = {
  runV2Turn,
};
