import { readFile, writeFile } from "node:fs/promises";
import process from "node:process";

const publicOrigin = (process.env.ECS_PUBLIC_ORIGIN || "").replace(/\/$/, "");
if (!/^https?:\/\/[^/]+$/.test(publicOrigin)) {
  throw new Error("ECS_PUBLIC_ORIGIN 必须是完整来源，例如 http://47.93.156.176");
}

const root = new URL("../", import.meta.url);
const publicFiles = [
  "packages/module-sdk/module-sdk.js",
  "config/modules/chat-1.0.0.json",
  "config/modules/story-1.0.0.json",
  "config/modules/deep_sea-1.0.0.json",
  "config/modules/career-1.0.0.json",
  "app/config/modules.ts",
  "app/page.tsx",
  "app/journey-demo/page.tsx",
  "modules/chat/public/chat-end.html",
  "modules/chat/public/chat.html",
  "modules/chat/public/home.html",
  "modules/chat/public/mic-diagnose.html",
  "modules/story/frontend/index.html",
  "modules/story/frontend/src/api/platformWorks.ts",
  "modules/story/frontend/src/components/Shared/PlatformReturn.tsx",
  "modules/story/frontend/src/components/Story/ChatBubble.tsx",
  "modules/story/frontend/src/pages/CharacterPage.tsx",
  "modules/deep-sea/index.html",
  "modules/deep-sea/src/components/LevelThree.vue",
  "modules/deep-sea/src/components/PlatformReturn.vue",
  "modules/deep-sea/src/components/ReportScreen.vue",
  "modules/deep-sea/src/utils/tts.js",
  "modules/talent-report/src/App.vue",
  "modules/talent-report/src/api/core.ts",
  "modules/talent-report/src/data/mockReport.ts",
  "modules/career/backend/templates/base.html",
  "modules/career/backend/templates/career_select.html",
  "modules/platform-core/main.py",
  "modules/report-agent/main.py",
  "modules/story/backend/app/main.py",
];

const portUrl = (port) => (port === "4173" ? publicOrigin : `${publicOrigin}:${port}`);
const localUrlPattern = /http:\/\/(?:localhost|127\.0\.0\.1):(3000|3001|4173|5174|5175|8000|8005|8010|8020)/g;

for (const relativePath of publicFiles) {
  const fileUrl = new URL(relativePath.replaceAll("\\", "/"), root);
  const original = await readFile(fileUrl, "utf8");
  const updated = original.replace(localUrlPattern, (_match, port) => portUrl(port));
  if (updated !== original) await writeFile(fileUrl, updated, "utf8");
}

console.log(`已将浏览器访问地址配置为 ${publicOrigin}`);
