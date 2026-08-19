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
  assert.match(page, /欢迎来到探索星球/);
  assert.match(page, /一个账号连接四块大陆/);
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
  for (const label of ["我的作品", "成长足迹", "天赋报告"]) {
    assert.match(planet, new RegExp(label));
  }
  assert.match(planet, /deep-space-nebula-bg-v1|nebula-background/);
  assert.match(planet, /stardust-fragment/);
  assert.match(planet, /onPointerMove=\{handleOrbitPointerMove\}/);
  assert.match(planet, /onWheel=\{handleWheel\}/);
  assert.match(planet, /沿星轨缓慢环行 · 拖动选择/);
  assert.match(planet, /requestAnimationFrame\(revolve\)/);
  assert.match(planet, /window\.location\.href=item\.url/);
  assert.match(page, /http:\/\/localhost:5175/);
  assert.match(page, /天赋报告/);
});
