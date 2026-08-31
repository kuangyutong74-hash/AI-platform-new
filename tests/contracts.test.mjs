import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const readJson = path => readFile(join(root, path), "utf8").then(JSON.parse);

const registry = await readJson("config/construct-registry.v1.json");
const policy = await readJson("config/evidence-policy.v1.json");
const manifestNames = (await readdir(join(root, "config/modules"))).filter(name => name.endsWith(".json"));
const manifests = await Promise.all(manifestNames.map(name => readJson(`config/modules/${name}`)));
const eventSchemaNames = (await readdir(join(root, "packages/contracts/schemas/evidence"))).filter(name => name.endsWith(".schema.json"));

assert.equal(manifests.length, 4, "必须登记四个当前体验模块");
assert.deepEqual(new Set(manifests.map(item => item.id)), new Set(["chat", "story", "deep_sea", "career"]));
const constructKeys = new Set(registry.constructs.map(item => item.key));
for (const manifest of manifests) {
  assert.match(manifest.version, /^\d+\.\d+\.\d+$/);
  assert.equal(manifest.constructRegistryVersion, registry.version);
  assert.ok(manifest.constructs.every(key => constructKeys.has(key)), `${manifest.id} 引用了未知构念`);
  assert.ok(manifest.supportedEventTypes.length > 0);
  for (const eventType of manifest.supportedEventTypes)
    assert.ok(eventSchemaNames.includes(`${eventType}.schema.json`), `${eventType} 缺少 payload schema`);
}
for (const rule of policy.rules) {
  assert.ok(rule.constructs.every(key => constructKeys.has(key)), `${rule.eventType} 引用了未知构念`);
  assert.ok(manifests.some(module => module.supportedEventTypes.includes(rule.eventType)), `${rule.eventType} 未被模块声明`);
}
console.log("contracts: PASS");
