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

export const PLATFORM_URL = "http://localhost:4173";
export const CORE_API_URL = "http://localhost:8020";

export const PLATFORM_MODULES: PlatformModule[] = [
  { id: "chat", name: "倾听之洲", module: "聊天观察", icon: "◌", iconAsset: "/assets/module-icons/module-listening-v2.png?v=1", angle: 8, latitude: 24, url: "http://localhost:3000/chat.html?from=ai-bole", healthUrl: "http://localhost:3000/chat.html", color: "mint", desc: "说说兴趣、问题和生活里的新发现" },
  { id: "story", name: "想象之洲", module: "故事共创", icon: "✦", iconAsset: "/assets/module-icons/module-imagination-v2.png?v=1", angle: 98, latitude: -18, url: "http://localhost:5174/story-create?from=ai-bole", healthUrl: "http://localhost:8010/api/health", color: "rose", desc: "创造人物、情节和自己的想象世界" },
  { id: "build", name: "创造之洲", module: "深海基地重建", icon: "◇", iconAsset: "/assets/module-icons/module-creation-v2.png?v=1", angle: 188, latitude: 10, url: "http://localhost:3001/?from=ai-bole", healthUrl: "http://localhost:8005/api/health", color: "blue", desc: "规划空间、调配资源并解决建造挑战" },
  { id: "career", name: "未来之洲", module: "职业模拟器", icon: "△", iconAsset: "/assets/module-icons/module-future-v2.png?v=2", angle: 278, latitude: -30, url: "http://localhost:8000/?from=ai-bole", healthUrl: "http://localhost:8000", color: "amber", desc: "体验不同职业的一天和真实任务" },
];
