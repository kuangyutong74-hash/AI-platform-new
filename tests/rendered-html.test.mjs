import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server renders AI伯乐探索星球", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>AI伯乐 · 探索星球<\/title>/i);
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  assert.match(page, /欢迎回到探索星球/);
  assert.match(page, /创建探索账号/);
  assert.match(page, /\/api\/account\/register/);
  assert.match(page, /\/api\/account\/password\/reset/);
  assert.match(page, /我是学生/);
  assert.match(page, /我是老师 \/ 家长/);
  assert.match(page, /两次输入的密码不一致/);
  assert.match(page, /http:\/\/localhost:8020/);
  assert.doesNotMatch(html, /codex-preview|SkeletonPreview|react-loading-skeleton/);
});

test("keeps four modules equal and preserves personal exploration nodes", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  const moduleConfig = await readFile(new URL("../app/config/modules.ts", import.meta.url), "utf8");
  const planet = await readFile(new URL("../app/components/PlanetHome.tsx", import.meta.url), "utf8");
  for (const name of ["聊天观察", "故事共创", "深海基地重建", "职业模拟器"]) {
    assert.match(moduleConfig, new RegExp(name));
  }
  assert.equal((moduleConfig.match(/\{ id: "/g) ?? []).length, 4);
  for (const label of ["我的作品", "天赋藏宝图"]) {
    assert.match(planet, new RegExp(label));
  }
  for (const label of ["天赋报告", "作品展柜", "成长足迹"]) {
    assert.match(page, new RegExp(label));
  }
  assert.match(planet, /deep-space-nebula-bg-v1|nebula-background/);
  assert.match(planet, /space-dust/);
  assert.match(planet, /window\.addEventListener\("pointermove",onPointerMove\)/);
  assert.match(planet, /onWheel=\{handleWheel\}/);
  assert.match(planet, /沿星轨缓慢环行 · 拖动选择/);
  assert.match(planet, /requestAnimationFrame\(revolve\)/);
  assert.match(planet, /window\.location\.href=item\.url/);
  assert.match(page, /http:\/\/localhost:5175/);
  assert.match(page, /天赋报告/);
});

test("keeps the glowing growth star on the illustrated SVG trail", async () => {
  const growth = await readFile(
    new URL("../app/components/GrowthTrailPage.tsx", import.meta.url),
    "utf8",
  );
  const styles = await readFile(
    new URL("../app/styles/growth.css", import.meta.url),
    "utf8",
  );

  assert.match(growth, /getPointAtLength/);
  assert.match(growth, /--trail-angle/);
  assert.match(growth, /className="traveler-star"/);
  assert.match(styles, /\.trail-paper-edge/);
  assert.match(styles, /\.trail-stitches/);
  assert.match(styles, /\.trail-progress-glow/);
});

test("keeps works as transparent highlight stickers and timeline as usage history", async () => {
  const works = await readFile(
    new URL("../app/components/WorksPage.tsx", import.meta.url),
    "utf8",
  );
  const growth = await readFile(
    new URL("../app/components/GrowthTrailPage.tsx", import.meta.url),
    "utf8",
  );
  const data = await readFile(
    new URL("../app/lib/explorer-data.mjs", import.meta.url),
    "utf8",
  );
  const styles = await readFile(
    new URL("../app/styles/works.css", import.meta.url),
    "utf8",
  );

  for (const moduleName of ["story", "ocean", "career", "listening"]) {
    assert.match(data, new RegExp(`highlight-${moduleName}-sticker-v1\\.webp`));
  }
  assert.match(works, /全部作品/);
  assert.match(works, /温暖点评/);
  assert.match(works, /metricValue/);
  assert.match(styles, /\.sticker-picture[\s\S]*background:\s*transparent/);
  assert.match(styles, /\.collection-art[\s\S]*background:\s*transparent/);
  assert.match(growth, /注册起点/);
  assert.match(growth, /timelineNotice/);
  assert.match(growth, /item\.metricValue/);
  assert.match(growth, /item\.firstUsedAt/);
  assert.match(growth, /最近一次完成/);
});
