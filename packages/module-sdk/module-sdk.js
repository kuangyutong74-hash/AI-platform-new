/* 浏览器端最小 SDK：与旧 window.AIBole 并存，逐模块采用。
 * 当前仅提供在线 V1 API；离线队列仍由兼容桥接承担，模块完成迁移后再统一收敛。 */
(function attachAIBoleModuleSDK(global) {
  const defaultCoreUrl = "http://localhost:8020";
  const requiredContext = ["sessionId", "moduleId", "moduleVersion", "launchCode", "launchCodeExpiresAt", "returnUrl", "contractVersion"];

  function createModuleSDK(options) {
    const coreUrl = (options && options.coreUrl) || defaultCoreUrl;
    let context = null;
    let token = null;
    const validateContext = value => {
      if (!value || requiredContext.some(key => !value[key])) throw new Error("启动上下文不完整");
      if (value.contractVersion !== "1.0") throw new Error("不支持的模块契约版本");
      return value;
    };
    const request = async (path, init) => {
      if (!token) throw new Error("模块尚未完成授权");
      const response = await fetch(coreUrl + path, Object.assign({}, init, { headers: Object.assign({"Content-Type": "application/json", "Authorization": "Bearer " + token}, init && init.headers) }));
      if (!response.ok) throw new Error("平台接口请求失败：" + response.status);
      return response.json();
    };
    return {
      initialize(value) { context = validateContext(value || global.__AI_BOLE_LAUNCH_CONTEXT__); return Promise.resolve(context); },
      async exchangeLaunchCode() {
        if (!context) throw new Error("请先初始化启动上下文");
        const result = await fetch(coreUrl + "/api/v1/module-authorizations:exchange", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({launchCode: context.launchCode})});
        if (!result.ok) throw new Error("启动授权已失效");
        token = (await result.json()).token;
      },
      emitEvidence(event) { return request("/api/v1/evidence-events:batch", {method: "POST", body: JSON.stringify({events: [event]})}); },
      publishArtifact(artifact) { return request("/api/v1/artifacts", {method: "POST", body: JSON.stringify(artifact)}); },
      completeSession(summary) { return request("/api/v1/assessment-sessions/" + context.sessionId, {method: "PATCH", body: JSON.stringify({status: "completed", summary: summary || {}})}); },
      interruptSession(reason) { return request("/api/v1/assessment-sessions/" + context.sessionId, {method: "PATCH", body: JSON.stringify({status: "interrupted", reason: reason || "module-interrupted"})}); },
      returnToPortal() { global.location.href = context ? context.returnUrl : "http://localhost:4173"; }
    };
  }
  global.AIBoleModuleSDK = { create: createModuleSDK };
})(window);
