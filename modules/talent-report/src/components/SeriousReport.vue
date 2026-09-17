<script setup lang="ts">
import type { GeneratedReport } from "../api/core";
import type { Evidence, Talent } from "../data/mockReport";
import { evidenceEventIds } from "../lib/evidenceCopy";

type ReportMetrics = { moduleNames:string; moduleCount:number; recordCount:number; strongCount:number; range:string };
type ReportCover = { range:string; sources:string[] };
defineProps<{talents:Talent[];insights:string[];family:string[];teacher:string[];liveReport?:GeneratedReport;ready?:boolean;metrics?:ReportMetrics;cover?:ReportCover}>();
const emit=defineEmits<{open:[evidence:Evidence]}>();
const dimensionAnalysis=(talent:Talent,liveReport?:GeneratedReport)=>liveReport?.dimensions.find(item=>item.key===talent.key);
const observationItems=(talent:Talent,liveReport?:GeneratedReport)=>(dimensionAnalysis(talent,liveReport)?.adult_observation||"").split(/[；\n]+/).map(item=>item.trim()).filter(Boolean);
const parentRefs=(report:GeneratedReport|undefined,kind:"family"|"teacher",index:number)=>report?.recommendation_attributions?.[kind]?.[index]||[];
const visibleEvidence=(talent:Talent)=>talent.evidence.slice(0,4);
const hiddenEvidenceCount=(talent:Talent)=>Math.max(0,talent.evidence.length-visibleEvidence(talent).length);
const evidenceRecordCount=(talent:Talent)=>talent.evidence.reduce((total,item)=>total+(item.rounds?.length||1),0);
// 分析文本引用的是“参与了本报告的证据”。深海完整通关记录会被合并成关卡卡片，
// 但它确实是被引用的证据，所以要一起算进来，否则会误判成“引用了被过滤的内容”。
function evidenceIds(talent:Talent){return new Set([...(talent.usedEvidenceIds||[]),...talent.evidence.flatMap(evidenceEventIds)])}
// 后端分析里如果出现被过滤掉的引用、否定式泛化句或自我复读，就退回本页
// 用真实证据现写的简短说明，避免家长读到“没有保存……没有保存……”这样的段落。
function hasRepeatedCopy(analysis:string){
  const sentences=analysis.split(/[。；]/).map(item=>item.trim()).filter(item=>item.length>12);
  return sentences.some((sentence,index)=>sentences.indexOf(sentence)!==index);
}
function conciseAnalysis(talent:Talent){
  if(!talent.evidence.length)return "当前记录只说明孩子参加过相关活动，缺少可回溯到具体表达、选择或操作的细节；本报告因此不把它们作为本维度证据。";
  const sources=[...new Set(talent.evidence.map(item=>item.source))];
  const examples=[...new Set(talent.evidence.map(item=>item.behavior))].slice(0,3).map(item=>item.length>82?`${item.slice(0,82)}…`:item);
  return `本阶段从${sources.join("、")}保留了 ${evidenceRecordCount(talent)} 条可回溯行为证据。较有代表性的记录包括：${examples.join("；")}这些内容只描述当时发生的行为，不等同于固定能力结论。`;
}
function analysisText(talent:Talent,liveReport?:GeneratedReport){
  const dimension=dimensionAnalysis(talent,liveReport),analysis=dimension?.analysis?.trim()||"";
  if(!analysis)return conciseAnalysis(talent);
  const invalidCopy=/没有保存|没有可确认|没有可引用|未保存|不作进一步推断|只确认参与|暂无可观测数据/.test(analysis);
  // 只有“这段分析主要建立在看不到的记录上”才需要重写。少量被合并或过滤的
  // 记录（例如深海完整通关记录）不影响分析的可核对性。
  const refs=dimension?.evidence_refs||[],ids=evidenceIds(talent);
  const filtered=refs.filter(id=>!ids.has(id)).length;
  const staleRefs=refs.length>0&&filtered>=2&&filtered/refs.length>=0.6;
  // 长度本身就是“这段分析是不是堆砌出来的”最直接信号，不再用引用条数间接判断。
  return invalidCopy||staleRefs||analysis.length>520||hasRepeatedCopy(analysis)?conciseAnalysis(talent):analysis;
}
</script>

<template>
  <main class="formal-report" aria-label="天赋观察报告连续阅读版">
    <article class="formal-document">
      <header class="formal-title">
        <div><span>AI 伯乐</span><strong>儿童天赋观察报告</strong></div>
        <dl>
          <div><dt>观察周期</dt><dd>{{ cover?.range || '近期探索活动' }}</dd></div>
          <div><dt>报告范围</dt><dd>{{ talents.length }} 个观察维度</dd></div>
        </dl>
        <h1>孩子的天赋观察与支持建议</h1>
        <p>本报告依据孩子在不同探索活动中的行为记录整理，用于帮助家长与老师持续观察，不用于能力排名或定性判断。</p>
        <dl v-if="metrics && metrics.recordCount" class="formal-metrics">
          <div><dt>记录来源</dt><dd>{{ metrics.moduleCount }} 项活动 · {{ metrics.moduleNames }}</dd></div>
          <div><dt>纳入报告的可回溯记录</dt><dd>{{ metrics.recordCount }} 条</dd></div>
          <div><dt>其中过程较完整的记录</dt><dd>{{ metrics.strongCount }} 条</dd></div>
          <div><dt>证据说明</dt><dd>只登记活动中真实发生的表达、选择与调整；缺少细节的记录不作推断。</dd></div>
        </dl>
      </header>
      <nav class="formal-toc" aria-label="报告目录"><a href="#formal-summary">综合观察</a><a href="#formal-dimensions">分维度记录</a><a href="#formal-advice">支持建议</a></nav>
      <section id="formal-summary" class="formal-section">
        <h2>综合观察</h2><p class="formal-section-intro">{{ ready ? '以下结论来自不同活动中的重复行为线索，每条都可以回到下面的过程记录核对。随着记录增加，观察结论也会持续更新。' : '报告智能体正在根据本次探索记录整理综合观察，完成后本页会自动更新。' }}</p>
        <ol class="formal-insight-list"><li v-for="insight in insights" :key="insight">{{ insight }}</li></ol>
      </section>
      <section id="formal-dimensions" class="formal-section">
        <h2>分维度观察记录</h2>
        <section v-for="(talent,index) in talents" :key="talent.key" class="formal-dimension">
          <header><span>{{ String(index+1).padStart(2,'0') }}</span><div><h3>{{ talent.adultName }}</h3><p>{{ talent.label }} · {{ talent.continent }} · {{ talent.module }}</p></div></header>
          <div v-if="talent.evidence.length" class="formal-analysis"><h4>基于有效证据的观察</h4><p>{{ analysisText(talent,liveReport) }}</p><div v-if="observationItems(talent,liveReport).length" class="formal-observation"><strong>给成人的延伸观察：</strong><ol><li v-for="item in observationItems(talent,liveReport)" :key="item">{{item}}</li></ol></div></div>
          <div class="formal-evidence"><h4>行为证据</h4><p v-if="!talent.evidence.length" class="formal-empty">本维度暂不展示证据：已有记录缺少可回溯的原话或操作细节，系统不会仅凭“参加过活动”作出判断。</p><button v-for="evidence in visibleEvidence(talent)" :key="evidence.id" type="button" @click="emit('open',evidence)"><span class="formal-evidence-meta"><b>{{ evidence.source }}</b><time>{{ evidence.time }}</time><em>{{ evidence.level==='strong'?'较完整记录':'参考线索' }}</em></span><span>{{ evidence.behavior }}</span><small>查看完整过程记录</small></button><p v-if="hiddenEvidenceCount(talent)" class="formal-evidence-folded">为避免重复，顺序阅读版每个维度展示最近 4 条有效记录，另有 {{ hiddenEvidenceCount(talent) }} 条有效记录已折叠。点开任意一条可见该次探索的完整过程。</p></div>
        </section>
      </section>
      <section id="formal-advice" class="formal-section formal-advice"><h2>下一阶段支持建议</h2><div><section><h3>家庭支持</h3><ol><li v-for="(item,index) in family" :key="item">{{ item }}<div v-if="parentRefs(liveReport,'family',index).length" class="formal-parent-source"><strong>参考了您的回答</strong><p v-for="source in parentRefs(liveReport,'family',index)" :key="`${source.question}-${source.answer}`">{{source.question}}：{{source.answer}}</p></div></li></ol></section><section><h3>学校支持</h3><ol><li v-for="(item,index) in teacher" :key="item">{{ item }}<div v-if="parentRefs(liveReport,'teacher',index).length" class="formal-parent-source"><strong>参考了您的回答</strong><p v-for="source in parentRefs(liveReport,'teacher',index)" :key="`${source.question}-${source.answer}`">{{source.question}}：{{source.answer}}</p></div></li></ol></section></div></section>
      <footer class="formal-disclaimer"><strong>报告说明</strong><p>天赋不是固定标签。本报告只描述当前记录中出现的行为特点，建议结合孩子在家庭、学校和长期活动中的真实表现持续观察。</p></footer>
    </article>
  </main>
</template>
