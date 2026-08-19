<script setup lang="ts">
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import TalentGalaxy from "./components/TalentGalaxy.vue";
import RadarChart from "./components/RadarChart.vue";
import { familyAdvice, reportMeta, talents, teacherAdvice, type Evidence, type Talent } from "./data/mockReport";

type ViewMode="child"|"adult";
const saved=localStorage.getItem("ai-bole-report-view");
const view=ref<ViewMode>(saved==="adult"?"adult":"child");
const selected=ref<Talent>(); const dialogVisible=ref(false); const exporting=ref(false); const activeTalentKey=ref<string>();
const rawEvidence=ref<Evidence>(); const rawDialogVisible=ref(false);
const agentGenerating=ref(false); const agentDraft=ref<string>();
const topTalents=computed(()=>[...talents].sort((a,b)=>b.relativeStrength-a.relativeStrength).slice(0,3));
const evidenceSources=[
  {id:"chat",icon:"◌",continent:"倾听之洲",module:"聊天观察",color:"#9ce5d0"},
  {id:"story",icon:"✦",continent:"想象之洲",module:"故事共创",color:"#cbb5ff"},
  {id:"deep-sea",icon:"◇",continent:"创造之洲",module:"深海基地重建",color:"#8fd8ff"},
  {id:"career",icon:"△",continent:"未来之洲",module:"职业模拟器",color:"#f2d49a"},
];
function setView(value:ViewMode){view.value=value;localStorage.setItem("ai-bole-report-view",value);}
let highlightTimer:number|undefined;
function openTalent(t:Talent){selected.value=t;activeTalentKey.value=t.key;dialogVisible.value=true;window.clearTimeout(highlightTimer);highlightTimer=window.setTimeout(()=>{if(!dialogVisible.value)activeTalentKey.value=undefined;},1100);}
function hoverTalent(key?:string){window.clearTimeout(highlightTimer);activeTalentKey.value=key;}
function leaveTalent(){if(!dialogVisible.value)activeTalentKey.value=undefined;}
function cardEvidence(t:Talent){return ({spatial:"你调整了基地布局，让通道不再打架。",linguistic:"你为角色补上原因，让故事更完整。",interpersonal:"你听懂双方需要，想出了公平办法。"} as Record<string,string>)[t.key]||t.evidence[0]?.behavior;}
function goPlanet(){location.href="http://localhost:4173/?from=talent-report";}
function goModule(url?:string){if(url)location.href=url;}
function openRaw(item:Evidence){rawEvidence.value=item;rawDialogVisible.value=true;}
async function generateAgentDraft(){agentGenerating.value=true;try{const response=await fetch("http://localhost:8030/api/report/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({child_name:"小朋友",events:talents.flatMap(t=>t.evidence.map(item=>({id:item.id,module:t.module,event_type:item.source,occurred_at:item.time,evidence_level:item.level,intelligence_candidates:[t.key],behavior_summary:item.behavior,raw_evidence:{raw:item.raw},context:{continent:item.continent}})))} )});if(!response.ok)throw new Error("agent offline");const result=await response.json();agentDraft.value=result.cross_insights?.[0]?.text||"智能体已完成本阶段证据整理。";}catch{agentDraft.value="本地演示模式：智能体会基于已采集行为，生成可回溯的观察表述与家庭、课堂建议。当前报告页面已准备好证据编号，可直接继续人工复核。";}finally{agentGenerating.value=false;}}
function scrollToEvidence(id:string){document.getElementById(`evidence-${id}`)?.scrollIntoView({behavior:"smooth",block:"center"});}
function statusFor(t:Talent){const strong=t.evidence.filter(item=>item.level==="strong").length;if(t.evidence.length<2)return {label:"采集行为较少",tone:"few"};if(strong>=2)return {label:"证据丰富",tone:"rich"};return {label:"证据均衡",tone:"balanced"};}
const evidenceRichNames=computed(()=>talents.filter(t=>statusFor(t).tone==="rich").map(t=>t.adultName));
const evidenceFewNames=computed(()=>talents.filter(t=>statusFor(t).tone==="few").map(t=>t.adultName));
const insightRows=[
  {text:"空间布局与情境决策都出现了‘先观察—再修正’的策略。",refs:["E05","E04"]},
  {text:"语言表达与人际理解经常共同出现：能补充因果，也能复述他人需要。",refs:["E01","E09"]},
  {text:"对自然细节的自发观察较稳定，并会在任务中持续修正方法。",refs:["E13","E14"]},
];
const workflowSteps=[{icon:"⌁",title:"记录",desc:"捕捉真实活动中的关键操作"},{icon:"◈",title:"归类",desc:"按情境标注候选智能维度"},{icon:"✦",title:"综合",desc:"比较行为类型与跨模块一致性"},{icon:"↺",title:"回溯",desc:"保留编号，随时查看原始日志"}];
const analysisMap:Record<string,string>={linguistic:"表达行为同时出现在故事创作与聊天观察中，说明孩子会用语言组织经验并补充因果。",logical:"孩子会先定位问题，再根据新信息调整策略；这是一种可迁移的问题解决路径。",spatial:"空间关系描述与基地布局修改相互印证，显示出较稳定的结构化观察方式。",interpersonal:"孩子会先复述不同角色的需要，再提出兼顾双方的方案，表现出关系视角的切换。",intrapersonal:"孩子能够描述投入、犹豫与表达意图，并愿意据此修改作品或选择。",naturalistic:"孩子会关注自然对象的细节差异，并尝试按环境、形态或功能进行归类。"};
const familyTipMap:Record<string,string>={linguistic:"共读后请孩子为角色补一句‘为什么’，再把这句话写进故事。",logical:"让孩子先说出排查顺序，再一起复盘哪一步带来了变化。",spatial:"提供纸笔或积木，邀请孩子先画布局再动手调整。",interpersonal:"遇到分歧时请孩子先说出双方各自想要什么。",intrapersonal:"活动结束留一分钟，让孩子说说最投入和最犹豫的环节。",naturalistic:"用照片或语音记录一次自然发现，并请孩子说出分类依据。"};
const teacherTipMap:Record<string,string>={linguistic:"允许用故事、口述或图文混合方式呈现同一学习成果。",logical:"把‘定位—尝试—修正’过程留在作品记录中，而不只看最终答案。",spatial:"给同一任务提供平面图、模型和数字工具等多种表达媒介。",interpersonal:"设置需要协商的角色任务，观察孩子如何复述和整合他人观点。",intrapersonal:"在任务后加入简短反思卡，记录选择依据与下一步计划。",naturalistic:"在观察活动中保留孩子自定的分类标签，再追问分类依据。"};
async function exportPdf(){
  const target=document.querySelector<HTMLElement>(".report-main"); if(!target)return; exporting.value=true;
  try{const canvas=await html2canvas(target,{backgroundColor:"#090b24",scale:1.6,useCORS:true});const pdf=new jsPDF("p","mm","a4");const width=190,height=canvas.height*width/canvas.width,page=277;let left=height,offset=10;const image=canvas.toDataURL("image/jpeg",.94);pdf.addImage(image,"JPEG",10,offset,width,height);left-=page;while(left>0){offset=10-(height-left);pdf.addPage();pdf.addImage(image,"JPEG",10,offset,width,height);left-=page;}pdf.save(`AI伯乐天赋报告-${new Date().toISOString().slice(0,10)}.pdf`);ElMessage.success("报告已导出");}catch{ElMessage.error("导出失败，请稍后重试");}finally{exporting.value=false;}
}
</script>

<template>
  <div :class="['cosmos-shell',{'child-theme':view==='child'}]">
    <div class="nebula nebula-a"/><div class="nebula nebula-b"/><div class="star-layer"/>
    <header class="report-header glass">
      <button class="brand-button" @click="goPlanet"><span>✦</span><b>AI 伯乐</b><small>天赋探索报告</small></button>
      <div class="title-block"><p>MY TALENT UNIVERSE</p><h1>我的天赋星图</h1></div>
      <div class="view-switch single" role="group" aria-label="报告视角切换"><button class="active" @click="setView(view==='child'?'adult':'child')">{{view==='child'?'切换家长 / 老师视角':'切换孩子视角'}} →</button></div>
    </header>

    <main class="report-main">
      <section v-if="view==='child'" class="child-view">
        <div class="galaxy-stage"><div class="hero-copy"><p class="eyebrow">你的探索正在点亮宇宙</p><h2>每一颗星，都藏着不一样的你</h2><p>点一点环绕星球的天赋卫星，看看最近有哪些发现。</p></div><TalentGalaxy :talents="talents" :active-talent-key="activeTalentKey" @select="openTalent"/></div>
        <section class="top-section"><div class="section-heading"><div><small>FOUR CONTINENTS · ONE TALENT UNIVERSE</small><h2>四块大陆共同点亮的天赋星</h2></div><p>每块大陆都带回不同的发现，它们一起拼成你的探索星图。</p></div><div class="source-ribbon glass" aria-label="天赋报告四个数据来源"><div v-for="source in evidenceSources" :key="source.id" class="source-node" :style="{'--source':source.color}"><i>{{source.icon}}</i><span><b>{{source.continent}}</b><small>{{source.module}}</small></span><em>已带回线索</em></div></div><p class="talent-cards-guide">从四块大陆带回的线索中，最近这些天赋星留下了清晰的成长故事。把鼠标放到卡片上，星星会回应你。</p><div class="top-grid"><article v-for="talent in topTalents" :key="talent.key" :data-talent-id="talent.key" :class="['talent-card','glass',{linked:activeTalentKey===talent.key}]" :style="{'--talent':talent.color}" @mouseenter="hoverTalent(talent.key)" @mouseleave="leaveTalent" @click="openTalent(talent)"><span :class="['talent-crystal',`crystal-${talent.key}`]" aria-hidden="true"/><div><small>{{talent.continent}}</small><h3>{{talent.childName}}</h3><p>{{cardEvidence(talent)}}</p></div><button @click.stop="openTalent(talent)">查看星光证据 →</button></article></div></section>
      </section>

      <section v-else class="adult-view">
        <!-- 家长/教师视角：先说明证据边界，再进入可回溯的证据工作台。 -->
        <div class="adult-intro"><div><p class="eyebrow">阶段性行为证据报告 · 家长 / 教师视角</p><h2>从真实活动中，看见孩子的思考方式</h2><p class="adult-disclaimer">本报告不输出能力分数。图表仅代表本阶段采集到的行为证据数量；“采集行为较少”不等于孩子缺少这项能力。</p></div><aside class="meta-card glass"><span>生成时间<b>{{reportMeta.generatedAt}}</b></span><span>观察区间<b>{{reportMeta.range}}</b></span><span>数据来源<b>{{reportMeta.sources.join('、')}}</b></span></aside></div>
        <section class="overview-grid adult-overview"><article class="glass radar-card"><div class="card-heading"><small>GARDNER · 6 INTELLIGENCES</small><h3>六类智能证据分布</h3><div class="radar-warning">⚠️ 图表仅代表采集证据数量多少，不等于能力强弱；导出 PDF 时该提示也会保留。</div></div><RadarChart :talents="talents"/><div class="radar-summary"><p><b>证据丰富的维度</b>{{evidenceRichNames.length?evidenceRichNames.join('、'):'本阶段暂无明显集中'}}</p><p><b>采集行为较少</b>{{evidenceFewNames.length?evidenceFewNames.join('、'):'本阶段六个维度均有可回溯线索'}}</p></div></article><article class="glass method-card workflow-card"><small>FROM ACTIVITY TO INSIGHT</small><h3>本次报告如何形成</h3><div class="workflow-steps"><div v-for="step in workflowSteps" :key="step.title" class="workflow-step"><span class="workflow-icon">{{step.icon}}</span><span><b>{{step.title}}</b><small>{{step.desc}}</small></span></div></div><div class="key-insights"><h4>本阶段关键洞察</h4><p v-for="row in insightRows" :key="row.text">{{row.text}} <button v-for="ref in row.refs" :key="ref" class="ref-chip" @click="scrollToEvidence(ref)">#{{ref}}</button></p></div></article></section>
        <section class="evidence-section"><div class="section-heading"><div><small>TRACEABLE EVIDENCE · SIX DIMENSIONS</small><h2>六类智能证据工作台</h2></div><p>强正向证据代表行为较明确且情境完整；参考证据只作为线索，不单独形成结论。每张卡片默认展开，方便快速回溯。</p></div><div class="adult-evidence-grid"><article v-for="talent in talents" :id="`talent-${talent.key}`" :key="talent.key" class="glass adult-talent-card"><header class="adult-card-head"><span class="adult-talent-icon" :style="{color:talent.color}">{{talent.icon}}</span><div><small>{{talent.continent}} · {{talent.module}}</small><h3>{{talent.adultName}}</h3></div><em :class="['status-badge',statusFor(talent).tone]">{{statusFor(talent).label}}</em></header><div class="evidence-list"><article v-for="item in talent.evidence" :id="`evidence-${item.id}`" :key="item.id" class="evidence-row"><button class="evidence-id-button" @click="scrollToEvidence(item.id)">#{{item.id}}</button><div class="evidence-body"><div><span :class="['evidence-level',item.level]">{{item.level==='strong'?'强正向证据':'参考证据'}}</span><time>{{item.time}}</time></div><h4>{{item.behavior}}</h4><p>来源：{{item.continent}}</p><button class="raw-link" @click="openRaw(item)">查看原始日志 ↗</button></div></article></div><p class="analysis-copy"><b>智能分析</b>{{analysisMap[talent.key]}} <span class="inline-ref">（证据{{talent.evidence.map(item=>`#${item.id}`).join('、')}}）</span></p><div class="tips-grid"><p><b>家庭养育小提示</b>{{familyTipMap[talent.key]}}</p><p><b>课堂教学小提示</b>{{teacherTipMap[talent.key]}}</p></div><p class="card-disclaimer">采集行为较少不等于该项能力不足，可以在对应大洲探索更多相关活动。</p></article></div></section>
        <section class="insight-grid adult-bottom-grid"><article class="glass"><small>INTEGRATED INSIGHTS</small><h2>综合跨维度洞察</h2><p v-for="(row,index) in insightRows" :key="row.text"><b>0{{index+1}}</b>{{row.text}} <button v-for="ref in row.refs" :key="ref" class="ref-chip" @click="scrollToEvidence(ref)">#{{ref}}</button></p></article><article class="glass"><small>ACTIONABLE SUPPORT</small><h2>落地行动建议</h2><div class="advice-columns"><div><h3>家庭养育建议</h3><ul><li v-for="item in familyAdvice" :key="item">{{item}}</li></ul></div><div><h3>课堂教学建议</h3><ul><li v-for="item in teacherAdvice" :key="item">{{item}}</li></ul></div></div></article></section>
        <section class="agent-launcher glass"><div><small>AI REPORT AGENT</small><h3>让智能体把证据写成温柔、可回溯的观察语言</h3><p>智能体只使用已采集行为，不补写事实；生成后仍可逐条回看证据编号。</p></div><button class="primary" :disabled="agentGenerating" @click="generateAgentDraft">{{agentGenerating?'正在整理证据…':'生成本阶段表述'}}</button><p v-if="agentDraft" class="agent-draft">{{agentDraft}}</p></section>
      </section>
    </main>

    <footer class="report-footer glass"><p>天赋不是标签，而是一段持续被看见、被支持的成长过程。</p><div><button class="ghost" @click="goPlanet">← 回到探索星球</button><button class="primary" :disabled="exporting" @click="exportPdf">{{exporting?'正在生成…':'导出 PDF'}}</button></div></footer>

    <el-dialog v-model="dialogVisible" width="min(540px,92vw)" class="talent-dialog" :show-close="false" align-center @closed="activeTalentKey=undefined">
      <template v-if="selected"><div class="dialog-star" :style="{color:selected.color}">{{selected.icon}}</div><p>{{selected.continent}} · {{selected.module}}</p><h2>{{selected.childName}}</h2><div class="dialog-evidence"><small>我们看见你</small><p>{{selected.evidence[0]?.behavior}}</p></div><blockquote>{{selected.encouragement}}</blockquote><div class="dialog-actions"><button @click="dialogVisible=false">继续看星星</button><button @click="goModule(selected.moduleUrl)">去{{selected.continent}}探险 →</button></div></template>
    </el-dialog>
    <el-dialog v-model="rawDialogVisible" width="min(620px,92vw)" class="raw-dialog" title="原始行为日志" align-center><template v-if="rawEvidence"><div class="raw-meta"><b>#{{rawEvidence.id}}</b><span>{{rawEvidence.continent}}</span><time>{{rawEvidence.time}}</time></div><p class="raw-behavior">{{rawEvidence.behavior}}</p><pre>{{rawEvidence.raw}}</pre><p class="raw-note">原始日志已做展示级精简，仅用于回溯证据来源，不用于单独判断能力。</p></template></el-dialog>
  </div>
</template>
