/* AI 伯乐 V1 模块 SDK：token 仅驻留内存；没有 LaunchContext 时为 standalone。 */
(function attachAIBoleModuleSDK(global) {
  const defaultCoreUrl = "http://localhost:8020";
  const requiredContext = ["sessionId", "moduleId", "moduleVersion", "launchCode", "launchCodeExpiresAt", "returnUrl", "contractVersion"];
  const queueLimit = 100;
  const uuid = () => global.crypto && global.crypto.randomUUID ? global.crypto.randomUUID() : `${Date.now()}-${Math.random()}`;

  function readContext() {
    if (!global.name) return null;
    try { const value = JSON.parse(global.name); return value.namespace === "ai-bole.launch-context.v1" ? value.context : null; }
    catch (_) { return null; }
    finally { global.name = ""; }
  }
  function createModuleSDK(options) {
    const coreUrl = (options && options.coreUrl) || defaultCoreUrl;
    const expectedModuleId = options && options.moduleId;
    let context = null, token = null, terminal = false, interruptionBound = false, queue = [];
    const standalone = {notConnected:true, standalone:true};
    const validate = value => {
      if (!value || requiredContext.some(key => !value[key]) || value.contractVersion !== "1.0") throw new Error("启动上下文无效");
      if (expectedModuleId && value.moduleId !== expectedModuleId) throw new Error("启动上下文与当前模块不匹配");
      return value;
    };
    const request = async (path, init) => {
      if (!token) return standalone;
      const response = await fetch(coreUrl + path, Object.assign({}, init, {headers:Object.assign({"Content-Type":"application/json","Authorization":"Bearer " + token}, init && init.headers)}));
      if (!response.ok) { const error = new Error("平台接口请求失败：" + response.status); error.status = response.status; throw error; }
      return response.json();
    };
    const flush = async () => {
      if (!token || !queue.length) return {flushed:0,pending:queue.length};
      const pending = []; let flushed = 0;
      for (const task of queue) { try { await request(task.path, task.init); flushed += 1; } catch (_) { pending.push(task); } }
      queue = pending; return {flushed,pending:queue.length};
    };
    const queueOrRequest = async (path, init) => {
      if (!context || !token) return standalone;
      try { return await request(path, init); }
      catch (error) { if (error.status && error.status < 500) throw error; queue = queue.concat([{path,init}]).slice(-queueLimit); return {queued:true,pending:queue.length}; }
    };
    return {
      async connectOptional() {
        if (context && token) return {connected:true,context};
        const value = context || readContext();
        if (!value) return standalone;
        context = validate(value);
        const response = await fetch(coreUrl + "/api/v1/module-authorizations:exchange", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({launchCode:context.launchCode})});
        if (!response.ok) throw new Error("启动授权已失效");
        token = (await response.json()).token;
        this.interruptOnPageHide();
        return {connected:true,context};
      },
      connected() { return Boolean(context && token); },
      makeEvent(eventType, payload, idempotencyKey) { return {schemaVersion:"1.0",eventId:uuid(),idempotencyKey:idempotencyKey || uuid(),eventType,occurredAt:new Date().toISOString(),payload}; },
      emitEvidence(event) { return queueOrRequest("/api/v1/evidence-events:batch", {method:"POST",body:JSON.stringify({events:[event]})}); },
      publishArtifact(artifact) { return queueOrRequest("/api/v1/artifacts", {method:"POST",body:JSON.stringify(artifact)}); },
      async captureSnapshot(selector) {
        if (!context || !token) return standalone;
        if (!global.html2canvas) await new Promise((resolve,reject)=>{const s=document.createElement("script");s.src=coreUrl+"/sdk/html2canvas.min.js";s.onload=resolve;s.onerror=reject;document.head.appendChild(s);});
        const canvas = await global.html2canvas(document.querySelector(selector || "main") || document.body, {scale:.9,useCORS:true,backgroundColor:null,logging:false});
        return request("/api/v1/assets/snapshots", {method:"POST",body:JSON.stringify({dataUrl:canvas.toDataURL("image/jpeg",.76)})});
      },
      async completeSession(summary) { if (!context || !token) return standalone; const flushed = await flush(); if (flushed.pending) return {queued:true,pending:flushed.pending}; terminal=true; return request("/api/v1/assessment-sessions/"+context.sessionId,{method:"PATCH",body:JSON.stringify({status:"completed",summary:summary||{}})}); },
      async interruptSession(reason) { if (!context || !token || terminal) return standalone; terminal=true; return request("/api/v1/assessment-sessions/"+context.sessionId,{method:"PATCH",body:JSON.stringify({status:"interrupted",reason:reason||"module-interrupted"})}); },
      interruptOnPageHide() { if (interruptionBound) return; interruptionBound=true; global.addEventListener("pagehide",()=>{if (!context || !token || terminal) return; fetch(coreUrl+"/api/v1/assessment-sessions/"+context.sessionId,{method:"PATCH",keepalive:true,headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},body:JSON.stringify({status:"interrupted",reason:"pagehide"})}).catch(()=>undefined);}); global.addEventListener("online",()=>flush()); },
      returnToPortal() { global.location.href = context ? context.returnUrl : "http://localhost:4173"; }
    };
  }
  global.AIBoleModuleSDK = {create:createModuleSDK};
})(window);
