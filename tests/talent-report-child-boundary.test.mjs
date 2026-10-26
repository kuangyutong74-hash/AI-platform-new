import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

const source = relative => readFile(new URL(`../${relative}`, import.meta.url), "utf8");

test("student treasure map does not expose the adult report", async () => {
  const [app,map,overlay,copy] = await Promise.all([
    source("modules/talent-report/src/App.vue"),
    source("modules/talent-report/src/components/TreasureMap.vue"),
    source("modules/talent-report/src/components/map/CelebrationOverlay.vue"),
    source("modules/talent-report/src/data/treasureMap.ts"),
  ]);

  assert.doesNotMatch(map, /openReport|open-report|map-report/);
  assert.doesNotMatch(overlay, /openReport|open-report|celebratePrimary/);
  assert.doesNotMatch(copy, /和爸爸妈妈一起看完整报告|celebratePrimary/);
  assert.doesNotMatch(app, /@open-report/);
  assert.match(app, /v-if="view==='adult'" class="view-switch single"/);
  assert.match(app, /@click="setView\('child'\)"/);
});
