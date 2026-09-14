<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import BookCover from "./book/BookCover.vue";import BookSpread from "./book/BookSpread.vue";import BookPagination from "./book/BookPagination.vue";import BookPageContent from "./book/BookPageContent.vue";import TurningLeaf from "./book/TurningLeaf.vue";import SeriousReport from "./SeriousReport.vue";
import { familyAdvice, insights, reportMeta, teacherAdvice, type Evidence, type Talent } from "../data/mockReport";
import { generateReport, getEvidenceRecords, type CoreEvidenceRecord, type GeneratedReport } from "../api/core";
import { momentsForTalent } from "../data/liveMoments";
import { useBookFlip } from "../composables/useBookFlip";import "../styles/book.css";import "../styles/reflect.css";import "../styles/report-polish.css";import "../styles/serious-report.css";
const props=defineProps<{talents:Talent[]}>();defineEmits<{back:[];childView:[]}>();
const opened=ref(false),opening=ref(false),rawEvidence=ref<Evidence>(),rawVisible=ref(false),highlightedId=ref<string>();
const savedFormat=localStorage.getItem("ai-bole-adult-report-format"),reportFormat=ref<"book"|"formal">(savedFormat==="formal"?"formal":"book"),liveReport=ref<GeneratedReport>(),liveEvents=ref<CoreEvidenceRecord[]>([]);
const {currentSpread,fromSpread,targetSpread,direction,flipping,goTo,next,prev}=useBookFlip(10);
const sourceNames:Record<string,string>={story:"故事共创",deep_sea:"深海基地重建",chat:"聊天观察",career:"职业模拟器"};
function isLevelThree(event:CoreEvidenceRecord){return event.moduleId==="deep_sea"&&event.eventType==="deep-sea.spatial-task-completed.v1"&&Number(event.payload.level)===3}
function childWords(event:CoreEvidenceRecord){return String(event.sessionSummary?.childWords||"").trim()}
function mentionedPeople(words:string){return ["同学","朋友","老师","爸爸","妈妈","家人","伙伴"].filter(name=>words.includes(name))}
function dimensionSummary(key:string,event:CoreEvidenceRecord,fallback:string){
  if(event.moduleId==="chat"){
    const words=childWords(event),people=mentionedPeople(words);
    if(key==="interpersonal")return people.length?`孩子谈到与${people.join("、")}的相处，并表达了对这段关系的关注。`:"孩子参与了交流，但现有记录没有保存可确认的他人观点或互动细节。";
    if(key==="intrapersonal")return words?"孩子在聊天中说出了自己的感受、想法或期待。":"孩子完成了聊天，但现有记录没有保存可引用的自我表达。";
  }
  if(event.moduleId==="career"&&key==="intrapersonal")return "孩子在导师追问中解释了自己的想法、理由或感受。";
  if(event.moduleId==="deep_sea"&&event.eventType==="deep-sea.spatial-task-completed.v1"){
    const level=Number(event.payload.level);
    if(level===1&&key==="naturalistic")return "孩子依据海洋生物的栖息地与共生关系完成生态配对。";
    if(level===1&&key==="logical")return "孩子比较配对条件并检验判断结果，完成第一关任务。";
    if(level===2&&key==="spatial")return "孩子通过摆放和旋转管件规划洋流线路。";
    if(level===2&&key==="logical")return "孩子检查线路是否连通，并根据结果调整连接方案。";
    if(level===3&&key==="linguistic")return "孩子在海洋议事厅中组织了自己的调解表达。";
    if(level===3&&key==="interpersonal")return "孩子在海洋议事厅中选择了回应双方需要的协调方案。";
  }
  return fallback
}
function dimensionDetails(key:string,event:CoreEvidenceRecord,details:string[]){
  if(event.moduleId==="chat"){
    const words=childWords(event),people=mentionedPeople(words),quote=words?`“${words.slice(0,120)}”`:"这条历史记录未保存聊天原文。";
    if(key==="interpersonal")return [people.length?`关系对象：孩子提到了${people.join("、")}。`:"关系对象：没有保存可确认的具体人物。",`人际视角：关注表达中如何理解、回应或期待他人；原话为${quote}`];
    if(key==="intrapersonal")return [`自我表达：${quote}`,"内省视角：关注孩子如何命名自己的感受、偏好、想法或期待。"];
  }
  if(event.moduleId==="career"&&key==="intrapersonal")return details.filter(detail=>detail.startsWith("导师对话：")).concat("内省视角：关注孩子如何解释自己的选择、感受和理由。");
  if(event.moduleId==="deep_sea"&&event.eventType==="deep-sea.spatial-task-completed.v1"){
    const level=Number(event.payload.level);
    if(level===1&&key==="naturalistic")return details.filter(detail=>detail.startsWith("观察与判断：")||detail.startsWith("任务结果："));
    if(level===1&&key==="logical")return ["推理过程：比较生物与住处的匹配条件，再通过检查结果验证判断。",...details.filter(detail=>detail.startsWith("任务结果："))];
    if(level===2&&key==="spatial")return details.filter(detail=>detail.startsWith("建造过程：")||detail.startsWith("调整记录："));
    if(level===2&&key==="logical")return ["推理过程：沿线路检查断点和方向，再根据连通结果调整管件。",...details.filter(detail=>detail.startsWith("调整记录："))];
    if(level===3&&key==="linguistic")return details.filter(detail=>detail.startsWith("调解表达："));
    if(level===3&&key==="interpersonal")return details.filter(detail=>detail.startsWith("方案选择："));
  }
  return details
}
function groupDeepSeaRounds(items:Evidence[],events:CoreEvidenceRecord[]){
  const eventById=new Map(events.map(event=>[event.id,event]));
  const groups=new Map<number,Evidence[]>(),result:Evidence[]=[];
  items.forEach(item=>{const event=eventById.get(item.id);const level=event?.moduleId==="deep_sea"&&event.eventType==="deep-sea.spatial-task-completed.v1"?Number(event.payload.level):0;if(!level){result.push(item);return}const rounds=groups.get(level)||[];rounds.push(item);groups.set(level,rounds)});
  const levelNames:Record<number,string>={1:"珊瑚公寓",2:"洋流电网",3:"海洋议事厅"};
  groups.forEach((rounds,level)=>{const ordered=[...rounds].sort((a,b)=>a.time.localeCompare(b.time));const latest=ordered[ordered.length-1];result.push({...latest,id:`deep-sea-level-${level}-${latest.id}`,behavior:`第 ${level} 关“${levelNames[level]}”共留下 ${ordered.length} 轮观察记录`,time:ordered.length>1?`${ordered[0].time.slice(5)} — ${latest.time.slice(5)}`:latest.time,logTitle:`深海基地第 ${level} 关：${levelNames[level]}`,logSummary:`同一关卡的 ${ordered.length} 轮体验按时间整理如下。`,logDetails:ordered.map(round=>`${round.time}｜${round.behavior}`),rounds:ordered})});
  return result.sort((a,b)=>b.time.localeCompare(a.time));
}
const displayTalents=computed(()=>props.talents.map(talent=>{
  if(!liveEvents.value.length)return {...talent,evidence:[],moments:[]};
  const events=liveEvents.value.filter(event=>event.reportDimensions.includes(talent.key));
  const explanations=liveReport.value?.evidence_explanations||[];
  const evidence=events.map(event=>{
    const explanation=explanations.find(item=>item.evidence_ref===event.id);
    const summary=dimensionSummary(talent.key,event,explanation?.summary||event.behaviorSummary);
    const details=dimensionDetails(talent.key,event,explanation?.details||["生成完成后会显示这次活动中具体发生的过程。"]);
    return {id:event.id,behavior:summary,source:sourceNames[event.moduleId]||"探索活动",continent:`${talent.continent} · ${sourceNames[event.moduleId]||"探索活动"}`,time:event.occurredAt.replace("T"," ").slice(0,16),level:event.evidenceLevel,raw:"",logTitle:explanation?.title||"报告智能体正在整理",logSummary:summary,logDetails:details} as Evidence
  });
  return {...talent,evidence:groupDeepSeaRounds(evidence,events),moments:momentsForTalent(liveEvents.value,talent.key).map(moment=>{
    const event=liveEvents.value.find(item=>item.id===moment.evidenceId);
    const explanation=explanations.find(item=>item.evidence_ref===moment.evidenceId);
    const caption=event?dimensionSummary(talent.key,event,explanation?.summary||"报告智能体正在整理这个精彩瞬间…"):explanation?.summary||"报告智能体正在整理这个精彩瞬间…";
    return {...moment,title:explanation?.title||moment.title,caption}
  })}
}));
const reportInsights=computed(()=>liveReport.value?liveReport.value.cross_insights.map(item=>item.text):insights.map(item=>item.replace(/\[E\d+\]/g,"")));
const advice=(value:string|string[])=>Array.isArray(value)?value:[value];
const reportFamily=computed(()=>liveReport.value?advice(liveReport.value.recommendations.family):familyAdvice),reportTeacher=computed(()=>liveReport.value?advice(liveReport.value.recommendations.teacher):teacherAdvice);
const richNames=computed(()=>displayTalents.value.filter(t=>t.evidence.filter(e=>e.level==="strong").length>=2).map(t=>t.adultName)),fewNames=computed(()=>displayTalents.value.filter(t=>t.evidence.length<2).map(t=>t.adultName));
const bookPageProps=computed(()=>({talents:displayTalents.value,insights:reportInsights.value,richNames:richNames.value,fewNames:fewNames.value,family:reportFamily.value,teacher:reportTeacher.value,liveReport:liveReport.value,highlightedId:highlightedId.value}));
let openingTimer:number|undefined,highlightTimer:number|undefined;
function openBook(){if(opening.value)return;opening.value=true;openingTimer=window.setTimeout(()=>{opened.value=true;opening.value=false},1280)}function closeBook(){opened.value=false;currentSpread.value=0}function previous(){if(currentSpread.value===0){closeBook();return}prev()}function forward(){if(currentSpread.value===9){ElMessage.info("已经是最后一页啦 ✦");return}next()}
function openRaw(evidence:Evidence){rawEvidence.value=evidence;rawVisible.value=true}function jumpEvidence(id:string){const index=displayTalents.value.findIndex(t=>t.evidence.some(e=>e.id===id));if(index<0)return;goTo(index+2);window.clearTimeout(highlightTimer);window.setTimeout(async()=>{highlightedId.value=id;await nextTick();document.getElementById(`evidence-${id}`)?.scrollIntoView({block:"center"});highlightTimer=window.setTimeout(()=>highlightedId.value=undefined,1200)},520)}
function finishReflection(report?:GeneratedReport){if(report)liveReport.value=report;next()}
function setReportFormat(value:"book"|"formal"){reportFormat.value=value;localStorage.setItem("ai-bole-adult-report-format",value)}function onKeydown(event:KeyboardEvent){if(reportFormat.value!=="book")return;if(event.key==="ArrowLeft"){event.preventDefault();opened.value?previous():undefined}else if(event.key==="ArrowRight"){event.preventDefault();opened.value?forward():openBook()}}
const exportingFormal=ref(false);
async function exportFormalPdf(){
  const doc=document.querySelector<HTMLElement>(".formal-document");
  if(!doc){ElMessage.error("报告内容尚未就绪");return}
  exportingFormal.value=true;
  try{
    await document.fonts?.ready;
    const pdf=new jsPDF("p","mm","a4");
    const pageW=pdf.internal.pageSize.getWidth(),pageH=pdf.internal.pageSize.getHeight(),margin=10,contentW=pageW-margin*2;
    const blocks:HTMLElement[]=[];
    doc.querySelectorAll<HTMLElement>(":scope > .formal-title,:scope > .formal-toc,:scope > .formal-disclaimer").forEach(b=>blocks.push(b));
    const summary=doc.querySelector<HTMLElement>("#formal-summary");if(summary)blocks.push(summary);
    doc.querySelectorAll<HTMLElement>("#formal-dimensions > .formal-dimension").forEach(b=>blocks.push(b));
    const advice=doc.querySelector<HTMLElement>("#formal-advice");if(advice)blocks.push(advice);
    if(!blocks.length)blocks.push(doc);
    let y=margin;
    for(const block of blocks){
      const canvas=await html2canvas(block,{backgroundColor:"#ffffff",scale:2,useCORS:true,scrollX:0,scrollY:0,width:block.scrollWidth,height:block.scrollHeight,windowWidth:block.scrollWidth,windowHeight:block.scrollHeight});
      const imgH=canvas.height*contentW/canvas.width;
      if(y+imgH>pageH-margin){pdf.addPage();y=margin}
      pdf.addImage(canvas.toDataURL("image/jpeg",.92),"JPEG",margin,y,contentW,imgH);
      y+=imgH+3;
    }
    pdf.save(`AI伯乐天赋观察报告-${new Date().toISOString().slice(0,10)}.pdf`);
    ElMessage.success("报告已导出");
  }catch(err){console.error(err);ElMessage.error("导出失败，请稍后重试")}
  finally{exportingFormal.value=false}
}
onMounted(async()=>{window.addEventListener("keydown",onKeydown);const evidence=await getEvidenceRecords();if(evidence?.records.length){liveEvents.value=evidence.records;const report=await generateReport();if(report)liveReport.value=report}});onBeforeUnmount(()=>{window.removeEventListener("keydown",onKeydown);window.clearTimeout(openingTimer);window.clearTimeout(highlightTimer)});
</script>

<template><div class="magic-book-app" :class="{'is-formal':reportFormat==='formal'}"><header class="storybook-toolbar"><div class="storybook-toolbar-actions"><button class="ribbon-button" @click="$emit('back')"><img src="/assets/report-watercolor/report-planet-v1.webp" alt=""/>返回探索星球</button><button class="child-view-button" @click="$emit('childView')">切换孩子视角 →</button></div><div><small>AI BOLE · TALENT REPORT</small><b>{{reportFormat==='book'?'天赋魔法书':'天赋观察报告'}}</b></div><div class="toolbar-end"><div class="report-format-switch" role="group" aria-label="报告样式切换"><button :class="{active:reportFormat==='book'}" :aria-pressed="reportFormat==='book'" @click="setReportFormat('book')">魔法书版</button><button :class="{active:reportFormat==='formal'}" :aria-pressed="reportFormat==='formal'" @click="setReportFormat('formal')">顺序阅读版</button></div><button v-if="reportFormat==='book'" class="paper-button" :disabled="!opened" @click="closeBook">回到封面</button><button v-if="reportFormat==='formal'" class="export-button" :disabled="exportingFormal" @click="exportFormalPdf">{{exportingFormal?'正在生成…':'导出 PDF'}}</button></div></header><template v-if="reportFormat==='book'"><main class="magic-book-main"><BookCover v-if="!opened" :range="reportMeta.range" :opening="opening" @open="openBook"/><div v-else class="open-book-shell" :class="[`flip-${direction}`,{flipping}]"><BookSpread :number="currentSpread+1" :can-prev="true" :can-next="currentSpread<9" @prev="previous" @next="forward"><template #left><BookPageContent v-bind="bookPageProps" :spread-index="currentSpread" side="left" @open="openRaw" @evidence="jumpEvidence" @finish="closeBook" @reflection-complete="finishReflection" @reflection-skip="finishReflection()"/></template><template #right><BookPageContent v-bind="bookPageProps" :spread-index="currentSpread" side="right" @open="openRaw" @evidence="jumpEvidence" @finish="closeBook" @reflection-complete="finishReflection" @reflection-skip="finishReflection()"/></template></BookSpread><TurningLeaf v-if="flipping" :direction="direction"><template #front><BookPageContent v-bind="bookPageProps" :spread-index="fromSpread" :side="direction==='next'?'right':'left'"/></template><template #back><BookPageContent v-bind="bookPageProps" :spread-index="targetSpread" :side="direction==='next'?'left':'right'"/></template></TurningLeaf></div></main></template><SeriousReport v-else :talents="displayTalents" :insights="reportInsights" :family="reportFamily" :teacher="reportTeacher" :live-report="liveReport" @open="openRaw"/><footer class="storybook-footer"><span>{{reportFormat==='formal'?'顺序阅读版 · 全文':opened?`第 ${currentSpread+1} / 10 跨页`:'封面 · 等待开启'}}</span><BookPagination v-if="reportFormat==='book'&&opened" :current="currentSpread" @select="goTo"/></footer><el-dialog v-model="rawVisible" width="min(620px,92vw)" class="book-raw-dialog" title="这次探索发生了什么" align-center><template v-if="rawEvidence"><div class="book-raw-meta"><span>{{rawEvidence.source}}</span><time>{{rawEvidence.time}}</time><em>{{rawEvidence.level==='strong'?'较完整记录':'参考线索'}}</em></div><section class="human-log"><h3>{{rawEvidence.logTitle||'探索过程回顾'}}</h3><p>{{rawEvidence.logSummary||rawEvidence.behavior}}</p><ul><li v-for="detail in rawEvidence.logDetails" :key="detail">{{detail}}</li></ul></section><small>这段回顾由报告智能体根据活动过程整理，只描述当时发生的行为，不代表能力分数或排名。</small></template></el-dialog></div></template>
