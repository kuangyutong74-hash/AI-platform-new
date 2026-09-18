<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import BookCover from "./book/BookCover.vue";import BookSpread from "./book/BookSpread.vue";import BookPagination from "./book/BookPagination.vue";import BookPageContent from "./book/BookPageContent.vue";import TurningLeaf from "./book/TurningLeaf.vue";import SeriousReport from "./SeriousReport.vue";
import { familyAdvice, insights, reportMeta, teacherAdvice, type Evidence, type Talent } from "../data/mockReport";
import { generateReport, getEvidenceRecords, type CoreEvidenceRecord, type GeneratedReport, type ParentAnswerReference } from "../api/core";
import { momentsForTalent } from "../data/liveMoments";
import { buildTalentEvidence, childWords, clipPhrase, dimensionSummary, evidenceEventIds, hasUsableDimensionEvidence, mentionedPeople, quoteChild } from "../lib/evidenceCopy";
import { useBookFlip } from "../composables/useBookFlip";import "../styles/book.css";import "../styles/reflect.css";import "../styles/report-polish.css";import "../styles/serious-report.css";
const props=defineProps<{talents:Talent[]}>();defineEmits<{back:[];childView:[]}>();
const opened=ref(false),opening=ref(false),rawEvidence=ref<Evidence>(),rawVisible=ref(false),highlightedId=ref<string>();
const savedFormat=localStorage.getItem("ai-bole-adult-report-format"),reportFormat=ref<"book"|"formal">(savedFormat==="formal"?"formal":"book"),liveReport=ref<GeneratedReport>(),liveEvents=ref<CoreEvidenceRecord[]>([]);
const {currentSpread,fromSpread,targetSpread,direction,flipping,goTo,next,prev}=useBookFlip(10);
const sourceNames:Record<string,string>={story:"故事共创",deep_sea:"深海基地重建",chat:"聊天观察",career:"职业模拟器"};
function excerpt(value:string,length:number){return clipPhrase(value,length)}
// 以下聊天相关辅助来自 kyt 的提交：同一话题、同一批发言会被平台存成多条事件，
// 这里按「话题 + 全部发言」指纹在事件层先去一次重，卡片层再按时间归并。
function chatTurns(event:CoreEvidenceRecord){
  const value=event.sessionSummary?.childTurns||event.payload.childTurns;
  return Array.isArray(value)?value.map(item=>typeof item==="object"&&item?String((item as {text?:unknown}).text||"").trim():"").filter(Boolean):[]
}
function chatTopic(event:CoreEvidenceRecord){return String(event.payload.topicKey||"自由交流").trim()||"自由交流"}
function chatFingerprint(event:CoreEvidenceRecord){return `${chatTopic(event)}|${chatTurns(event).join("|")||childWords(event)}`}
function deduplicateEvents(events:CoreEvidenceRecord[]){
  const seen=new Set<string>();
  return events.filter(event=>{if(event.moduleId!=="chat")return true;const key=chatFingerprint(event);if(!key||seen.has(key))return false;seen.add(key);return true})
}
function dimensionDetails(key:string,event:CoreEvidenceRecord,details:string[]){
  if(event.moduleId==="chat"){
    const words=childWords(event);
    // 卡片的入口已经过滤掉没有可引用原话的记录，这里写不出原话时直接交回
    // 原始过程说明，不再用“未保存原文”这类否定句占位。
    if(!words)return details;
    // 同一条记录里孩子往往说了好几句，按顺序列出来比只引用一句更有依据。
    // 引号一律交给 quoteChild，孩子原话自带引号时外层会自动换成「」，
    // 不会出现“他说“……””这种嵌套。
    const turns=chatTurns(event).filter(Boolean),pool=turns.length?turns:[words];
    const listed=pool.slice(-3).map((turn,index,array)=>array.length>1?`表达 ${turns.length-array.length+1+index}：${quoteChild(clipPhrase(turn,120))}`:`自我表达：${quoteChild(clipPhrase(turn,120))}`);
    const people=mentionedPeople(pool.join("；"));
    if(key==="interpersonal")return [people.length?`关系对象：孩子提到了${people.join("、")}。`:`交流话题：${chatTopic(event)}。`,...listed,"人际视角：关注孩子如何理解、回应或期待他人。"];
    if(key==="intrapersonal")return [...listed,"内省视角：关注孩子如何命名自己的感受、偏好、想法或期待。"];
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
const displayTalents=computed(()=>props.talents.map(talent=>{
  const dimension=liveReport.value?.dimensions.find(item=>item.key===talent.key);
  if(!liveEvents.value.length)return {...talent,evidence:[],moments:[]};
  const events=deduplicateEvents(liveEvents.value.filter(event=>event.reportDimensions.includes(talent.key)&&hasUsableDimensionEvidence(talent.key,event)));
  const explanations=liveReport.value?.evidence_explanations||[];
  const evidence=buildTalentEvidence(talent.key,liveEvents.value,explanations,sourceNames,talent.continent,dimensionDetails);
  // 头部标签同样不能用示例文案：它必须来自这份报告真实的证据状态，
  // 否则每个孩子看到的是同一句结论式的评价。
  return {...talent,label:dimension?.status||"记录积累中",usedEvidenceIds:events.map(event=>event.id),evidence,moments:momentsForTalent(events,talent.key).map(moment=>{
    const event=liveEvents.value.find(item=>item.id===moment.evidenceId);
    const explanation=explanations.find(item=>item.evidence_ref===moment.evidenceId);
    const caption=(event?dimensionSummary(talent.key,event,explanation?.summary||""):"")||explanation?.summary||moment.caption;
    return {...moment,title:explanation?.title||moment.title,caption}
  })}
}));
// 报告接口返回前不能拿示例综合观察顶上：那会让家长在同一页里同时看到
// 真实证据卡片和写得像结论一样的示例文案。
const reportReady=computed(()=>Boolean(liveReport.value));
const reportInsights=computed(()=>{
  if(liveReport.value)return liveReport.value.cross_insights.map(item=>item.text);
  if(liveEvents.value.length)return ["报告智能体正在根据本次探索记录整理综合观察，完成后会自动更新本页。"];
  return insights.map(item=>item.replace(/\[E\d+\]/g,""));
});
const advice=(value:string|string[])=>Array.isArray(value)?value:[value];
// 同样不能在报告就绪前用示例建议顶上，否则家长会把示例当成对自己孩子的结论。
const pendingAdvice=["报告智能体正在根据真实记录整理支持建议，完成后会自动更新本页。"];
const reportFamily=computed(()=>liveReport.value?advice(liveReport.value.recommendations.family):liveEvents.value.length?pendingAdvice:familyAdvice),reportTeacher=computed(()=>liveReport.value?advice(liveReport.value.recommendations.teacher):liveEvents.value.length?pendingAdvice:teacherAdvice);
const emptyAttributions=(items:string[]):ParentAnswerReference[][]=>items.map(()=>[]);
const familyAttributions=computed(()=>liveReport.value?.recommendation_attributions?.family||emptyAttributions(reportFamily.value));
const teacherAttributions=computed(()=>liveReport.value?.recommendation_attributions?.teacher||emptyAttributions(reportTeacher.value));
const richNames=computed(()=>displayTalents.value.filter(t=>t.evidence.filter(e=>e.level==="strong").length>=2).map(t=>t.adultName)),fewNames=computed(()=>displayTalents.value.filter(t=>t.evidence.length<2).map(t=>t.adultName));
// 顺序阅读版开头要先交代“这份报告的依据是什么”。数字全部来自真实记录，
// “较完整”按页面上真正标注出来的卡片统计，这样概览、维度分析里的数字和
// 卡片标签永远指向同一批记录。
const evidenceMetrics=computed(()=>{
  const usable=liveEvents.value.filter(event=>event.reportDimensions.some(key=>hasUsableDimensionEvidence(key,event)));
  const modules=[...new Set(usable.map(event=>sourceNames[event.moduleId]||"探索活动"))];
  const times=usable.map(event=>event.occurredAt||"").filter(Boolean).sort();
  const range=times.length?(times.length>1?`${times[0].slice(0,10)} 至 ${times[times.length-1].slice(0,10)}`:times[0].slice(0,10)):"";
  const strongIds=new Set(displayTalents.value.flatMap(talent=>talent.evidence.filter(item=>item.level==="strong").flatMap(evidenceEventIds)));
  const usableIds=new Set(usable.map(event=>event.id));
  return {moduleNames:modules.join("、"),moduleCount:modules.length,recordCount:usable.length,strongCount:[...strongIds].filter(id=>usableIds.has(id)).length,range};
});
const coverMetrics=computed(()=>{
  const first=liveEvents.value.map(event=>event.occurredAt||"").filter(Boolean).sort()[0]||"";
  const last=liveEvents.value.map(event=>event.occurredAt||"").filter(Boolean).sort().slice(-1)[0]||"";
  return {range:first&&last?`${first.slice(0,10)} 至 ${last.slice(0,10)}`:"",sources:[...new Set(liveEvents.value.map(event=>sourceNames[event.moduleId]||"探索活动"))]};
});
const formalProps=computed(()=>({talents:displayTalents.value,insights:reportInsights.value,family:reportFamily.value,teacher:reportTeacher.value,liveReport:liveReport.value,ready:reportReady.value,metrics:evidenceMetrics.value,cover:coverMetrics.value}));
const bookPageProps=computed(()=>({talents:displayTalents.value,insights:reportInsights.value,richNames:richNames.value,fewNames:fewNames.value,family:reportFamily.value,teacher:reportTeacher.value,familyAttributions:familyAttributions.value,teacherAttributions:teacherAttributions.value,liveReport:liveReport.value,highlightedId:highlightedId.value}));
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
    const pageW=pdf.internal.pageSize.getWidth(),pageH=pdf.internal.pageSize.getHeight(),margin=10,contentW=pageW-margin*2,contentH=pageH-margin*2;
    const docWidth=doc.scrollWidth,docHeight=doc.scrollHeight;
    // 长报告如果始终按 2 倍分辨率生成，浏览器可能会超过画布尺寸或内存上限。
    // 在保证清晰度的前提下自适应缩放，随后再按 A4 页面裁切同一张连续画布。
    const maxCanvasSide=28000,maxCanvasPixels=64_000_000;
    const renderScale=Math.min(2,maxCanvasSide/Math.max(docWidth,docHeight),Math.sqrt(maxCanvasPixels/(docWidth*docHeight)));
    const canvas=await html2canvas(doc,{backgroundColor:"#ffffff",scale:renderScale,useCORS:true,scrollX:0,scrollY:0,width:docWidth,height:docHeight,windowWidth:docWidth,windowHeight:docHeight});
    const pxPerMm=canvas.width/contentW,pageCapacity=Math.floor(contentH*pxPerMm),docRect=doc.getBoundingClientRect(),domToCanvas=canvas.width/docWidth;
    // 优先在章节、分析块和单条证据卡之前换页。这样既不会切断卡片，也不会
    // 像原先那样把整个维度推到下一页，留下半页甚至整页空白。
    const safeBreaks=Array.from(doc.querySelectorAll<HTMLElement>([
      ":scope > .formal-toc",
      "#formal-summary > h2",
      "#formal-summary > .formal-section-intro",
      "#formal-summary > .formal-insight-list > li",
      "#formal-dimensions > h2",
      "#formal-dimensions > .formal-dimension > header",
      "#formal-dimensions > .formal-dimension > .formal-analysis",
      "#formal-dimensions > .formal-dimension > .formal-evidence > *",
      "#formal-advice",
      ":scope > .formal-disclaimer"
    ].join(","))).map(element=>Math.round((element.getBoundingClientRect().top-docRect.top)*domToCanvas)).filter(value=>value>0&&value<canvas.height).sort((a,b)=>a-b);
    let sourceY=0,pageIndex=0;
    while(sourceY<canvas.height){
      const idealEnd=Math.min(sourceY+pageCapacity,canvas.height);
      const candidates=safeBreaks.filter(value=>value>sourceY+8&&value<=idealEnd);
      const safeEnd=candidates[candidates.length-1];
      // 只有安全断点至少填满 58% 页面时才采用；否则按页高裁切，避免再次产生大留白。
      const sourceEnd=safeEnd&&safeEnd-sourceY>=pageCapacity*.58?safeEnd:idealEnd;
      const sliceHeight=Math.max(1,sourceEnd-sourceY),pageCanvas=document.createElement("canvas");
      pageCanvas.width=canvas.width;pageCanvas.height=sliceHeight;
      pageCanvas.getContext("2d")?.drawImage(canvas,0,sourceY,canvas.width,sliceHeight,0,0,canvas.width,sliceHeight);
      if(pageIndex>0)pdf.addPage();
      pdf.addImage(pageCanvas.toDataURL("image/jpeg",.93),"JPEG",margin,margin,contentW,sliceHeight/pxPerMm);
      sourceY=sourceEnd;pageIndex++;
    }
    pdf.save(`AI伯乐天赋观察报告-${new Date().toISOString().slice(0,10)}.pdf`);
    ElMessage.success("报告已导出");
  }catch(err){console.error(err);ElMessage.error("导出失败，请稍后重试")}
  finally{exportingFormal.value=false}
}
onMounted(async()=>{window.addEventListener("keydown",onKeydown);const evidence=await getEvidenceRecords();if(evidence?.records.length){liveEvents.value=evidence.records;const report=await generateReport();if(report)liveReport.value=report}});onBeforeUnmount(()=>{window.removeEventListener("keydown",onKeydown);window.clearTimeout(openingTimer);window.clearTimeout(highlightTimer)});
</script>

<template><div class="magic-book-app" :class="{'is-formal':reportFormat==='formal'}"><header class="storybook-toolbar"><div class="storybook-toolbar-actions"><button class="ribbon-button" @click="$emit('back')"><img src="/assets/report-watercolor/report-planet-v1.webp" alt=""/>返回探索星球</button><button class="child-view-button" @click="$emit('childView')">切换孩子视角 →</button></div><div><small>AI BOLE · TALENT REPORT</small><b>{{reportFormat==='book'?'天赋魔法书':'天赋观察报告'}}</b></div><div class="toolbar-end"><div class="report-format-switch" role="group" aria-label="报告样式切换"><button :class="{active:reportFormat==='book'}" :aria-pressed="reportFormat==='book'" @click="setReportFormat('book')">魔法书版</button><button :class="{active:reportFormat==='formal'}" :aria-pressed="reportFormat==='formal'" @click="setReportFormat('formal')">顺序阅读版</button></div><button v-if="reportFormat==='book'" class="paper-button" :disabled="!opened" @click="closeBook">回到封面</button><button v-if="reportFormat==='formal'" class="export-button" :disabled="exportingFormal" @click="exportFormalPdf">{{exportingFormal?'正在生成…':'导出 PDF'}}</button></div></header><template v-if="reportFormat==='book'"><main class="magic-book-main"><BookCover v-if="!opened" :range="reportMeta.range" :opening="opening" @open="openBook"/><div v-else class="open-book-shell" :class="[`flip-${direction}`,{flipping}]"><BookSpread :number="currentSpread+1" :can-prev="true" :can-next="currentSpread<9" @prev="previous" @next="forward"><template #left><BookPageContent v-bind="bookPageProps" :spread-index="currentSpread" side="left" @open="openRaw" @evidence="jumpEvidence" @finish="closeBook" @reflection-complete="finishReflection" @reflection-skip="finishReflection()"/></template><template #right><BookPageContent v-bind="bookPageProps" :spread-index="currentSpread" side="right" @open="openRaw" @evidence="jumpEvidence" @finish="closeBook" @reflection-complete="finishReflection" @reflection-skip="finishReflection()"/></template></BookSpread><TurningLeaf v-if="flipping" :direction="direction"><template #front><BookPageContent v-bind="bookPageProps" :spread-index="fromSpread" :side="direction==='next'?'right':'left'"/></template><template #back><BookPageContent v-bind="bookPageProps" :spread-index="targetSpread" :side="direction==='next'?'left':'right'"/></template></TurningLeaf></div></main></template><SeriousReport v-else v-bind="formalProps" @open="openRaw"/><footer class="storybook-footer"><span>{{reportFormat==='formal'?'顺序阅读版 · 全文':opened?`第 ${currentSpread+1} / 10 跨页`:'封面 · 等待开启'}}</span><BookPagination v-if="reportFormat==='book'&&opened" :current="currentSpread" @select="goTo"/></footer><el-dialog v-model="rawVisible" width="min(620px,92vw)" class="book-raw-dialog" title="这次探索发生了什么" align-center><template v-if="rawEvidence"><div class="book-raw-meta"><span>{{rawEvidence.source}}</span><time>{{rawEvidence.time}}</time><em>{{rawEvidence.level==='strong'?'较完整记录':'参考线索'}}</em></div><section class="human-log"><h3>{{rawEvidence.logTitle||'探索过程回顾'}}</h3><p>{{rawEvidence.logSummary||rawEvidence.behavior}}</p><ul><li v-for="detail in rawEvidence.logDetails" :key="detail">{{detail}}</li></ul></section><small>这段回顾由报告智能体根据活动过程整理，只描述当时发生的行为，不代表能力分数或排名。</small></template></el-dialog></div></template>
