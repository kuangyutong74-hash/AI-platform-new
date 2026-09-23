<script setup lang="ts">
import { computed } from "vue";
import RadarChart from "../../RadarChart.vue";import type { Talent } from "../../../data/mockReport";
import type { GeneratedReport } from "../../../api/core";
const props=defineProps<{side:"left"|"right";talents:Talent[];insights:string[];richNames:string[];fewNames:string[];family:string[];liveReport?:GeneratedReport}>();defineEmits<{evidence:[id:string]}>();
function parts(text:string){return text.split(/(\[[^\]]+\])/g).filter(Boolean)}
function clean(text:string){return text.replace(/\[[^\]]+\]/g,"").replace(/\s+/g," ").trim()}
const overviewSummary=computed(()=>{
  const evidenceCount=props.talents.reduce((sum,talent)=>sum+talent.evidence.length,0);
  if(!evidenceCount)return "目前还没有足够的探索记录形成孩子的阶段性结论。建议先完成更多聊天、故事、建构或职业体验，报告会随着真实行为记录逐步补充。";
  if(props.insights.some(item=>item.includes("正在根据本次探索记录整理")))return "本页图形只展示各类行为记录的数量，记录较多不等于孩子在该方面表现突出。具体结论与培养建议正在根据真实记录整理，完成后会自动更新。";
  const reportInsights=props.liveReport?.cross_insights||[];
  const evidenceById=new Map(props.talents.flatMap(talent=>talent.evidence.map(evidence=>[evidence.id,evidence] as const)));
  const isMechanicOrNeutral=(text:string)=>/洋流电网|旋转管件|参与面|完成了\s*\d+\s*次/.test(text);
  const stable=reportInsights.find(item=>{
    const refs=[...new Set(item.evidence_refs)].map(id=>evidenceById.get(id)).filter(Boolean);
    const independent=new Set(refs.map(evidence=>`${evidence?.source}|${evidence?.time}`)).size;
    return !isMechanicOrNeutral(item.text)&&refs.filter(evidence=>evidence?.level==="strong").length>=2&&independent>=2;
  });
  const concrete=reportInsights.find(item=>!isMechanicOrNeutral(item.text)&&!/较为费力|不作为.+优势/.test(item.text));
  const advice=clean(props.family[0]||"");
  if(stable)return `多条独立记录共同支持一项阶段性优势线索：${clean(stable.text)}这不是由点击次数得出的结论，而是相似的高质量行为在不同记录中重复出现。${advice?`接下来建议：${advice}`:"建议换到新的生活或学习情境中继续观察，确认这种表现能否稳定迁移。"}`;
  if(concrete)return `目前还不足以判断哪一部分“最突出”，但有一项具体表现值得肯定：${clean(concrete.text)}这次表现先作为继续观察的线索，不直接上升为天赋结论。${advice?`接下来建议：${advice}`:"建议在另一个独立情境中再次观察同类行为。"}`;
  return "目前的记录主要说明孩子完成了哪些探索活动，还没有出现经过多次独立情境验证的优势线索。游戏中的点击、拖动和合理调整次数不作为突出表现的依据，建议继续观察孩子是否会稳定地说明理由、提前规划并有针对性地修正。";
});
</script>
<template><div v-if="side==='left'"><p class="page-kicker">WATERCOLOR MAP · 02</p><h2>六类智能 · 阶段性观察总览</h2><RadarChart :talents="talents"/><div class="watercolor-legend"><span v-for="talent in talents" :key="talent.key"><i :style="{background:talent.color}"/>{{talent.adultName}}</span></div><section class="overview-conclusion" aria-labelledby="overview-conclusion-title"><h3 id="overview-conclusion-title">给家长的阶段小结</h3><p>{{overviewSummary}}</p></section><p class="semantic-warning">图表只表示采集到的行为记录数量；记录多不等于能力突出，记录少也不等于能力不足。</p></div><div v-else><p class="page-kicker">WHOLE PICTURE</p><h2>整体观测结论</h2><div class="insight-notes"><p v-for="(insight,index) in insights" :key="index"><span v-for="part in parts(insight)" :key="part"><button v-if="/^\[[^\]]+\]$/.test(part)" @click.stop="$emit('evidence',part.slice(1,-1))">{{part}}</button><template v-else>{{part}}</template></span></p></div><div class="coverage-note"><h3>行为记录覆盖情况</h3><p><b>记录相对较多：</b>{{richNames.length?richNames.join('、'):'正在持续积累'}}</p><p><b>记录相对较少：</b>{{fewNames.length?fewNames.join('、'):'本阶段各维度均有记录'}}</p><small>这里只说明记录数量，不表示能力高低或天赋是否突出。</small></div><blockquote class="closing-quote">天赋不是标签，而是一段持续被看见、被支持的成长过程。</blockquote></div></template>
