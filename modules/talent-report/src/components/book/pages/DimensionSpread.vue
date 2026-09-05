<script setup lang="ts">
import { computed } from "vue";
import type { Evidence, Talent } from "../../../data/mockReport";

const props = defineProps<{ side: "left" | "right"; talent: Talent; analysis?: string; adultObservation?: string; highlightedId?: string }>();
defineEmits<{ open: [evidence: Evidence] }>();

const observationItems = computed(() => props.adultObservation?.split(/[；\n]+/).map(item => item.trim()).filter(Boolean) || []);

const moduleMeta: Record<string, { color: string; stamp: string; wash: string }> = {
  "聊天观察": { color: "#d98f6a", stamp: "聊", wash: "/assets/storybook/magic-wash-blue.png" },
  "故事共创": { color: "#7aa8c9", stamp: "事", wash: "/assets/storybook/magic-wash-terracotta.png" },
  "深海基地重建": { color: "#8fbf9f", stamp: "深", wash: "/assets/storybook/magic-wash-sage.png" },
  "深海基地重建 · 第一关生物配对": { color: "#8fbf9f", stamp: "深", wash: "/assets/storybook/magic-wash-sage.png" },
  "职业模拟器": { color: "#c9a3c9", stamp: "职", wash: "/assets/storybook/magic-wash-gold.png" }
};

const metaFor = (source: string) => moduleMeta[source] || { color: "#b89a5f", stamp: source.slice(0, 1), wash: "/assets/storybook/magic-wash-gold.png" };

const dimSticker = computed(() => `/assets/storybook/magic-dim-${props.talent.key}.png`);

const evidenceCount = computed(() => props.talent.evidence.length);
const visibleEvidence = computed(() => props.talent.evidence.slice(0, 4));
const moduleSegments = computed(() => {
  const counts: Record<string, number> = {};
  props.talent.evidence.forEach(ev => { counts[ev.source] = (counts[ev.source] || 0) + 1; });
  const segments = Object.entries(counts).map(([source, count]) => ({ source, count, ...metaFor(source), percent: (count / (evidenceCount.value || 1)) * 100 }));
  return segments;
});
const sourceCountText = computed(() => {
  const list = moduleSegments.value.map(seg => `${seg.source} ${seg.count}`);
  return list.join(" · ") || "暂无证据";
});

const crossSceneText = computed(() => {
  const n = evidenceCount.value;
  if (!n) return "报告智能体正在根据真实活动记录整理跨场景一致性…";
  const parts = moduleSegments.value.map(seg => `${seg.source} ${seg.count} 条`);
  const diversity = moduleSegments.value.length;
  let suffix = "";
  if (diversity >= 3) suffix = "同一倾向在多个场景中稳定出现，说明表现不是偶然的。";
  else if (diversity === 2) suffix = "同一倾向在两类活动中出现，具备一定稳定性。";
  else suffix = "当前记录集中在一种活动中，建议在其他情境继续观察。";
  return `行为证据共 ${n} 条，其中 ${parts.join("、")}；${suffix}`;
});
</script>

<template>
  <div class="dimension-spread-v2" :style="{ '--talent': talent.color }">
    <template v-if="side === 'left'">
      <section class="ds-left">
        <img class="ds-wash ds-wash-tl" src="/assets/storybook/magic-wash-terracotta.png" alt="" />
        <img class="ds-wash ds-wash-bl" src="/assets/storybook/magic-wash-gold.png" alt="" />

        <p class="ds-kicker">{{ talent.key.toUpperCase() }} · {{ talent.childName }}</p>
        <h2 class="ds-title">
          {{ talent.adultName }}
          <img class="ds-dim-sticker" :src="dimSticker" :alt="talent.adultName" />
        </h2>

        <div class="ds-overview-card">
          <div class="ds-overview-head">行为证据 {{ evidenceCount }} 条 · 走过 {{ moduleSegments.length }} 个世界</div>
          <div class="ds-module-bar">
            <div v-for="seg in moduleSegments" :key="seg.source" class="ds-bar-segment" :style="{ width: seg.percent + '%', background: seg.color }" />
          </div>
          <div class="ds-overview-foot">{{ sourceCountText }}</div>
        </div>

        <div v-if="visibleEvidence.length" class="ds-evidence-grid">
          <article v-for="item in visibleEvidence" :key="item.id" :id="`evidence-${item.id}`" class="ds-evidence-card" :class="{ highlighted: highlightedId === item.id }">
            <div class="ds-evidence-stamp" :style="{ color: metaFor(item.source).color, borderColor: metaFor(item.source).color, background: metaFor(item.source).color + '18' }">
              {{ metaFor(item.source).stamp }}
            </div>
            <div class="ds-evidence-body">
              <div class="ds-evidence-meta">
                <time>{{ item.time }}</time>
                <span class="ds-level" :class="item.level">{{ item.level === "strong" ? "较完整记录" : "参考线索" }}</span>
              </div>
              <p class="ds-evidence-text">{{ item.behavior }}</p>
              <button class="ds-evidence-open" type="button" @click.stop="$emit('open', item)">查看回顾</button>
            </div>
            <img class="ds-evidence-wash" :src="metaFor(item.source).wash" alt="" />
          </article>
        </div>
        <div v-else class="ds-evidence-empty">还没有收集到与这一维度相关的行为记录</div>

        <p class="ds-page-tip">证据未完 · 翻到下一页继续 ✦</p>
      </section>
    </template>

    <template v-else>
      <section class="ds-right">
        <img class="ds-wash ds-wash-tr" src="/assets/storybook/magic-wash-blue.png" alt="" />
        <img class="ds-wash ds-wash-br" src="/assets/storybook/magic-wash-gold.png" alt="" />

        <p class="ds-kicker">INSIGHT NOTES · {{ talent.adultName }}</p>
        <div class="ds-right-header">
          <h2 class="ds-title">天赋解读</h2>
          <div class="ds-star-wrap">
            <img class="ds-star-seal" src="/assets/storybook/magic-star-seal.png" alt="" />
            <small>智能体 · 观察星章</small>
          </div>
        </div>

        <div class="ds-insight-cards">
          <article class="ds-insight-card">
            <h3><i>✦</i>表现画像</h3>
            <p>{{ analysis || "报告智能体正在根据本次真实活动记录整理具体表现…" }}</p>
          </article>

          <article class="ds-insight-card">
            <h3><i>✦</i>跨场景足迹</h3>
            <p>{{ crossSceneText }}</p>
          </article>

          <article class="ds-insight-card ds-insight-card--gold">
            <h3><i>✦</i>给大人的延伸观察</h3>
            <ul v-if="observationItems.length">
              <li v-for="item in observationItems" :key="item">{{ item }}</li>
            </ul>
            <p v-else>报告智能体正在结合本次表现生成延伸观察清单…</p>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.dimension-spread-v2 {
  --ink: #4a3f2e;
  --ink-soft: #6b5b4f;
  --ink-muted: #9c8b7a;
  --paper: #fffdf6;
  --paper-shade: #fdf8ec;
  --gold: #c9a961;
  --divider: #e0cfa8;
  position: relative;
  height: 100%;
  color: var(--ink);
  font-size: 13px;
  line-height: 1.6;
}

.ds-left,
.ds-right {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.ds-wash {
  position: absolute;
  pointer-events: none;
  opacity: 0.18;
  mix-blend-mode: multiply;
  transform: rotate(-8deg);
  width: 130px;
}
.ds-wash-tl { top: -30px; left: -28px; }
.ds-wash-bl { bottom: 18px; right: -20px; width: 150px; transform: rotate(12deg); opacity: 0.13; }
.ds-wash-tr { top: -18px; right: -24px; opacity: 0.14; }
.ds-wash-br { bottom: 30px; left: -22px; width: 150px; transform: rotate(10deg); opacity: 0.12; }

.ds-kicker {
  margin: 0 0 6px;
  color: #b89a5f;
  font-size: 10px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.ds-title {
  position: relative;
  display: inline-flex;
  align-items: baseline;
  gap: 12px;
  margin: 0 0 14px;
  padding-bottom: 8px;
  color: var(--ink);
  font-family: "LXGW WenKai", "Yuanti SC", "幼圆", "KaiTi", cursive;
  font-size: clamp(22px, 2.2cqw, 32px);
  font-weight: 600;
  line-height: 1.2;
}
.ds-title::after {
  content: "";
  position: absolute;
  left: 0;
  bottom: 0;
  width: 72px;
  height: 2px;
  background: linear-gradient(90deg, var(--gold), transparent);
}

.ds-dim-sticker {
  width: 96px;
  height: 96px;
  object-fit: contain;
  opacity: 0.95;
  transform: translateY(2px) rotate(3deg);
}
/* 总览卡 */
.ds-overview-card {
  position: relative;
  padding: 14px 16px;
  margin-bottom: 14px;
  border-radius: 14px;
  background: var(--paper-shade);
  box-shadow: inset 0 0 0 1px rgba(184, 154, 95, 0.22), 0 6px 16px rgba(104, 71, 45, 0.06);
  overflow: hidden;
}
.ds-overview-card::before {
  content: "";
  position: absolute;
  left: -40px;
  top: -30px;
  width: 120px;
  height: 80px;
  background: url('/assets/storybook/magic-wash-terracotta.png') center/contain no-repeat;
  opacity: 0.16;
  mix-blend-mode: multiply;
  transform: rotate(-14deg);
}
.ds-overview-head {
  position: relative;
  margin-bottom: 10px;
  color: #8a7a5c;
  font-size: 11.5px;
  font-weight: 500;
}
.ds-module-bar {
  position: relative;
  display: flex;
  height: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: #f0e6cf;
}
.ds-bar-segment {
  height: 100%;
  transition: width 0.6s ease;
}
.ds-bar-segment:first-child { border-radius: 999px 0 0 999px; }
.ds-bar-segment:last-child { border-radius: 0 999px 999px 0; }
.ds-overview-foot {
  position: relative;
  margin-top: 10px;
  color: #a09070;
  font-size: 10.5px;
}

/* 证据卡网格 */
.ds-evidence-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}
.ds-evidence-card {
  position: relative;
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 10px;
  padding: 12px;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(104, 71, 45, 0.06);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  overflow: hidden;
}
.ds-evidence-card.highlighted {
  transform: scale(1.02);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--talent) 45%, transparent), 0 6px 16px rgba(104, 71, 45, 0.1);
}
.ds-evidence-wash {
  position: absolute;
  right: -30px;
  top: -30px;
  width: 90px;
  opacity: 0.18;
  mix-blend-mode: multiply;
  pointer-events: none;
}
.ds-evidence-stamp {
  align-self: start;
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 1.5px dashed currentColor;
  font-size: 12px;
  font-weight: 700;
}
.ds-evidence-body {
  position: relative;
  z-index: 1;
  min-width: 0;
}
.ds-evidence-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 10px;
  margin-bottom: 6px;
  color: #a09070;
  font-size: 10px;
}
.ds-evidence-text {
  margin: 0 0 8px;
  color: var(--ink-soft);
  font-size: 11.5px;
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ds-evidence-open {
  border: 0;
  padding: 0;
  background: transparent;
  color: #b87b52;
  font-size: 10.5px;
  text-decoration: underline;
  text-underline-offset: 2px;
  cursor: pointer;
}
.ds-evidence-open:hover { color: #8f5c36; }

.ds-level {
  padding: 2px 7px;
  border-radius: 999px;
  background: #fff7e5;
  color: #8a6f3d;
  font-size: 9.5px;
}
.ds-level.reference { background: #f4f0ff; }

.ds-evidence-empty {
  margin: 20px 0;
  padding: 22px;
  border-radius: 14px;
  background: var(--paper-shade);
  color: var(--ink-muted);
  text-align: center;
  font-size: 12px;
}

.ds-page-tip {
  margin: auto 0 0;
  padding-top: 10px;
  border-top: 1.5px dashed var(--divider);
  color: #b8a87f;
  font-size: 10.5px;
  text-align: center;
}

/* 右页 */
.ds-right-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.ds-star-wrap {
  display: grid;
  place-items: center;
  gap: 4px;
  color: #a09070;
  font-size: 9px;
  text-align: center;
}
.ds-star-seal {
  width: 48px;
  height: 48px;
  object-fit: contain;
}

.ds-insight-cards {
  display: grid;
  gap: 12px;
}
.ds-insight-card {
  position: relative;
  padding: 14px 16px;
  border-radius: 14px;
  background: var(--paper-shade);
  box-shadow: inset 0 0 0 1px rgba(184, 154, 95, 0.2), 0 5px 12px rgba(104, 71, 45, 0.05);
  overflow: hidden;
}
.ds-insight-card::after {
  content: "";
  position: absolute;
  right: -36px;
  top: -24px;
  width: 90px;
  height: 90px;
  background: url('/assets/storybook/magic-wash-blue.png') center/contain no-repeat;
  opacity: 0.14;
  mix-blend-mode: multiply;
  transform: rotate(18deg);
}
.ds-insight-card:nth-child(2)::after {
  background: url('/assets/storybook/magic-wash-sage.png') center/contain no-repeat;
  right: auto;
  left: -30px;
  top: auto;
  bottom: -20px;
  transform: rotate(-12deg);
}
.ds-insight-card--gold::after {
  background: url('/assets/storybook/magic-wash-gold.png') center/contain no-repeat;
  right: -28px;
  top: -18px;
}
.ds-insight-card h3 {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 10px;
  color: #8a6f3d;
  font-family: "LXGW WenKai", "Yuanti SC", "幼圆", "KaiTi", cursive;
  font-size: 14px;
  font-weight: 700;
}
.ds-insight-card h3 i {
  font-style: normal;
  color: var(--gold);
}
.ds-insight-card p,
.ds-insight-card ul {
  position: relative;
  z-index: 1;
  margin: 0;
  color: #5a5240;
  font-size: 12px;
  line-height: 1.65;
}
.ds-insight-card ul {
  padding-left: 1.25em;
  display: grid;
  gap: 6px;
}
.ds-insight-card li { padding-left: 3px; }

@media (max-width: 900px) {
  .ds-evidence-grid { grid-template-columns: 1fr; }
  .ds-dim-sticker { width: 64px; height: 64px; }
}
@media (max-height: 780px) {
  .ds-title { font-size: 22px; margin-bottom: 10px; }
  .ds-evidence-grid { gap: 9px; }
  .ds-evidence-card { padding: 10px; }
  .ds-insight-cards { gap: 9px; }
}
</style>
