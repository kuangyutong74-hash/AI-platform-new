<script setup lang="ts">
import type { GeneratedReport } from "../api/core";
import type { Evidence, Talent } from "../data/mockReport";

defineProps<{talents:Talent[];insights:string[];family:string[];teacher:string[];liveReport?:GeneratedReport}>();
const emit=defineEmits<{open:[evidence:Evidence]}>();
const dimensionAnalysis=(talent:Talent,liveReport?:GeneratedReport)=>liveReport?.dimensions.find(item=>item.key===talent.key);
</script>

<template>
  <main class="formal-report" aria-label="天赋观察报告连续阅读版">
    <article class="formal-document">
      <header class="formal-title">
        <div><span>AI 伯乐</span><strong>儿童天赋观察报告</strong></div>
        <dl><div><dt>观察周期</dt><dd>近期探索活动</dd></div><div><dt>报告范围</dt><dd>{{ talents.length }} 个观察维度</dd></div></dl>
        <h1>孩子的天赋观察与支持建议</h1>
        <p>本报告依据孩子在不同探索活动中的行为记录整理，用于帮助家长与老师持续观察，不用于能力排名或定性判断。</p>
      </header>
      <nav class="formal-toc" aria-label="报告目录"><a href="#formal-summary">综合观察</a><a href="#formal-dimensions">分维度记录</a><a href="#formal-advice">支持建议</a></nav>
      <section id="formal-summary" class="formal-section">
        <h2>综合观察</h2><p class="formal-section-intro">以下结论来自不同活动中的重复行为线索。随着记录增加，观察结论也会持续更新。</p>
        <ol class="formal-insight-list"><li v-for="insight in insights" :key="insight">{{ insight }}</li></ol>
      </section>
      <section id="formal-dimensions" class="formal-section">
        <h2>分维度观察记录</h2>
        <section v-for="(talent,index) in talents" :key="talent.key" class="formal-dimension">
          <header><span>{{ String(index+1).padStart(2,'0') }}</span><div><h3>{{ talent.adultName }}</h3><p>{{ talent.label }} · {{ talent.continent }} · {{ talent.module }}</p></div></header>
          <div class="formal-analysis"><h4>阶段性分析</h4><p>{{ dimensionAnalysis(talent,liveReport)?.analysis || talent.encouragement }}</p><p v-if="dimensionAnalysis(talent,liveReport)?.adult_observation" class="formal-observation"><strong>建议继续观察：</strong>{{ dimensionAnalysis(talent,liveReport)?.adult_observation }}</p></div>
          <div class="formal-evidence"><h4>行为证据</h4><p v-if="!talent.evidence.length" class="formal-empty">当前还没有足够的可回溯记录，建议继续在不同情境中观察。</p><button v-for="evidence in talent.evidence" :key="evidence.id" type="button" @click="emit('open',evidence)"><span class="formal-evidence-meta"><b>{{ evidence.source }}</b><time>{{ evidence.time }}</time><em>{{ evidence.level==='strong'?'较完整记录':'参考线索' }}</em></span><span>{{ evidence.behavior }}</span><small>查看完整过程记录</small></button></div>
        </section>
      </section>
      <section id="formal-advice" class="formal-section formal-advice"><h2>下一阶段支持建议</h2><div><section><h3>家庭支持</h3><ol><li v-for="item in family" :key="item">{{ item }}</li></ol></section><section><h3>学校支持</h3><ol><li v-for="item in teacher" :key="item">{{ item }}</li></ol></section></div></section>
      <footer class="formal-disclaimer"><strong>报告说明</strong><p>天赋不是固定标签。本报告只描述当前记录中出现的行为特点，建议结合孩子在家庭、学校和长期活动中的真实表现持续观察。</p></footer>
    </article>
  </main>
</template>
