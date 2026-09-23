export type ModuleColor = "mint" | "rose" | "blue" | "amber";

export type PlatformModule = {
  id: string;
  name: string;
  module: string;
  icon: string;
  iconAsset: string;
  angle: number;
  latitude: number;
  url: string;
  healthUrl: string;
  color: ModuleColor;
  desc: string;
};

function configuredUrl(value: string | undefined, fallback: string) {
  return (value || fallback).replace(/\/$/, "");
}

export const PLATFORM_URL = configuredUrl(process.env.NEXT_PUBLIC_PLATFORM_URL, "http://localhost:4173");
export const CORE_API_URL = configuredUrl(process.env.NEXT_PUBLIC_CORE_API_URL, "http://localhost:8020");
export const NATURAL_TTS_URL = configuredUrl(process.env.NEXT_PUBLIC_NATURAL_TTS_URL, "http://localhost:8005/api/tts");

export const PLATFORM_MODULES: PlatformModule[] = [
  { id: "chat", name: "倾听之洲", module: "聊天观察", icon: "◌", iconAsset: "/assets/module-icons/module-listening-v2.png?v=1", angle: 8, latitude: 24, url: "http://localhost:3000/home.html?from=ai-bole", healthUrl: "http://localhost:3000/chat.html", color: "mint", desc: "说说兴趣、问题和生活里的新发现" },
  { id: "story", name: "想象之洲", module: "故事共创", icon: "✦", iconAsset: "/assets/module-icons/module-imagination-v2.png?v=1", angle: 98, latitude: -18, url: "http://localhost:5174/story-create?from=ai-bole", healthUrl: "http://localhost:8010/api/health", color: "rose", desc: "创造人物、情节和自己的想象世界" },
  { id: "build", name: "创造之洲", module: "深海基地重建", icon: "◇", iconAsset: "/assets/module-icons/module-creation-v2.png?v=1", angle: 188, latitude: 10, url: "http://localhost:3001/?from=ai-bole", healthUrl: "http://localhost:8005/api/health", color: "blue", desc: "规划空间、调配资源并解决建造挑战" },
  { id: "career", name: "未来之洲", module: "职业模拟器", icon: "△", iconAsset: "/assets/module-icons/module-future-v2.png?v=2", angle: 278, latitude: -30, url: "http://localhost:8000/?from=ai-bole&ui=career-cinematic-v10", healthUrl: "http://localhost:8000", color: "amber", desc: "体验不同职业的一天和真实任务" },
];

type ModuleManifest = {id:string;name:string;description?:string;entryUrl:string;healthUrl?:string};
export type ExplorationRelay = {fromModule:string;sourceTitle:string;prompt:string};

export function canonicalModuleId(id: string) {
  return id === "build" ? "deep_sea" : id;
}

export async function loadPlatformModules(signal?: AbortSignal): Promise<PlatformModule[]> {
  const response = await fetch(`${CORE_API_URL}/api/v1/modules`, {credentials:"include", signal});
  if (!response.ok) throw new Error("模块目录暂时不可用");
  const payload = await response.json() as {modules?:ModuleManifest[]};
  if (!Array.isArray(payload.modules)) throw new Error("模块目录格式不正确");
  return payload.modules.map((manifest,index) => {
    const existing = PLATFORM_MODULES.find(item => canonicalModuleId(item.id) === manifest.id);
    return existing
      ? {...existing,name:manifest.name,desc:manifest.description||existing.desc,url:existing.id==="career"?existing.url:manifest.entryUrl,healthUrl:manifest.healthUrl||existing.healthUrl}
      : {id:manifest.id,name:manifest.name,module:manifest.name,icon:"✦",iconAsset:"",angle:(index*73)%360,latitude:index%2?-22:22,url:manifest.entryUrl,healthUrl:manifest.healthUrl||"",color:"mint",desc:manifest.description||"新的探索体验"};
  });
}

export async function launchPlatformModule(item: PlatformModule, relay?: ExplorationRelay) {
  const response = await fetch(`${CORE_API_URL}/api/v1/assessment-sessions`, {method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({module_id:canonicalModuleId(item.id)})});
  if (!response.ok) throw new Error("探索记录暂时无法创建");
  const context = await response.json();
  const destination = new URL(item.url);
  // The session cookie belongs to the account API host (ports do not matter),
  // which can differ from the hostname used to open the platform shell.
  if (["localhost", "127.0.0.1"].includes(destination.hostname)) {
    destination.hostname = new URL(CORE_API_URL).hostname;
  }
  const nextContext = relay ? {...context,relay} : context;
  window.name = JSON.stringify({
    namespace:"ai-bole.launch-context.v1",
    context:{...nextContext,platformOrigin:window.location.origin,coreApiUrl:CORE_API_URL},
  });
  if(relay){
    if(canonicalModuleId(item.id)==="story")destination.pathname="/story-create/characters";
    if(canonicalModuleId(item.id)==="career")destination.pathname="/careers";
    destination.searchParams.set("relayFrom",relay.fromModule);
    destination.searchParams.set("relayTitle",relay.sourceTitle);
    destination.searchParams.set("relayPrompt",relay.prompt);
  }
  window.location.assign(destination.toString());
}
