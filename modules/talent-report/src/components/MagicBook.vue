<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import BookCover from "./book/BookCover.vue";
import BookSpread from "./book/BookSpread.vue";
import BookPagination from "./book/BookPagination.vue";
import ReadingGuideSpread from "./book/pages/ReadingGuideSpread.vue";
import OverviewSpread from "./book/pages/OverviewSpread.vue";
import DimensionSpread from "./book/pages/DimensionSpread.vue";
import AdviceSpread from "./book/pages/AdviceSpread.vue";
import { familyAdvice, insights, reportMeta, teacherAdvice, type Evidence, type Talent } from "../data/mockReport";
import { useBookFlip } from "../composables/useBookFlip";
import "../styles/book.css";

const props=defineProps<{talents:Talent[]}>();
defineEmits<{back:[];childView:[]}>();
const opened=ref(false), opening=ref(false), rawEvidence=ref<Evidence>(), rawVisible=ref(false), highlightedId=ref<string>();
const {currentSpread,direction,flipping,goTo,next,prev}=useBookFlip(9);
const richNames=computed(()=>props.talents.filter(t=>t.evidence.filter(e=>e.level==="strong").length>=2).map(t=>t.adultName));
const fewNames=computed(()=>props.talents.filter(t=>t.evidence.length<2).map(t=>t.adultName));
const activeTalent=computed(()=>currentSpread.value>=2&&currentSpread.value<=7?props.talents[currentSpread.value-2]:undefined);
let openingTimer:number|undefined, highlightTimer:number|undefined;
function openBook(){if(opening.value)return;opening.value=true;openingTimer=window.setTimeout(()=>{opened.value=true;opening.value=false},1280)}
function closeBook(){opened.value=false;currentSpread.value=0}
function previous(){if(currentSpread.value===0){closeBook();return}prev()}
function forward(){if(currentSpread.value===8){ElMessage.info("已经是最后一页啦 ✦");return}next()}
function openRaw(evidence:Evidence){rawEvidence.value=evidence;rawVisible.value=true}
function jumpEvidence(id:string){const index=props.talents.findIndex(t=>t.evidence.some(e=>e.id===id));if(index<0)return;goTo(index+2);window.clearTimeout(highlightTimer);window.setTimeout(async()=>{highlightedId.value=id;await nextTick();document.getElementById(`evidence-${id}`)?.scrollIntoView({block:"center"});highlightTimer=window.setTimeout(()=>highlightedId.value=undefined,1200)},520)}
function exportPdf(){document.querySelector<HTMLButtonElement>(".report-footer .primary")?.click()}
function onKeydown(event:KeyboardEvent){if(event.key==="ArrowLeft"){event.preventDefault();opened.value?previous():undefined}else if(event.key==="ArrowRight"){event.preventDefault();opened.value?forward():openBook()}}
onMounted(()=>window.addEventListener("keydown",onKeydown));
onBeforeUnmount(()=>{window.removeEventListener("keydown",onKeydown);window.clearTimeout(openingTimer);window.clearTimeout(highlightTimer)});
</script>
<template>
  <div class="magic-book-app">
    <header class="storybook-toolbar"><div class="storybook-toolbar-actions"><button class="ribbon-button" @click="$emit('back')">✦ 返回探索星球</button><button class="child-view-button" @click="$emit('childView')">切换孩子视角 →</button></div><div><small>AI BOLE · TALENT REPORT</small><b>天赋魔法书</b></div><button class="paper-button" :disabled="!opened" @click="closeBook">回到封面</button></header>
    <main class="magic-book-main">
      <BookCover v-if="!opened" :range="reportMeta.range" :opening="opening" @open="openBook"/>
      <div v-else class="open-book-shell" :class="[`flip-${direction}`,{flipping}]">
        <BookSpread :number="currentSpread+1" :can-prev="true" :can-next="currentSpread<8" @prev="previous" @next="forward">
          <template #left><ReadingGuideSpread v-if="currentSpread===0" side="left"/><OverviewSpread v-else-if="currentSpread===1" side="left" :talents="talents" :insights="insights" :rich-names="richNames" :few-names="fewNames" @evidence="jumpEvidence"/><DimensionSpread v-else-if="activeTalent" side="left" :talent="activeTalent" :highlighted-id="highlightedId" @open="openRaw"/><AdviceSpread v-else side="left" :family="familyAdvice" :teacher="teacherAdvice"/></template>
          <template #right><ReadingGuideSpread v-if="currentSpread===0" side="right"/><OverviewSpread v-else-if="currentSpread===1" side="right" :talents="talents" :insights="insights" :rich-names="richNames" :few-names="fewNames" @evidence="jumpEvidence"/><DimensionSpread v-else-if="activeTalent" side="right" :talent="activeTalent" :highlighted-id="highlightedId" @open="openRaw"/><AdviceSpread v-else side="right" :family="familyAdvice" :teacher="teacherAdvice" @finish="closeBook"/></template>
        </BookSpread>
        <div class="turning-leaf" aria-hidden="true"/>
      </div>
    </main>
    <footer class="storybook-footer"><span>{{opened?`第 ${currentSpread+1} / 9 跨页`:'封面 · 等待开启'}}</span><BookPagination v-if="opened" :current="currentSpread" @select="goTo"/><button class="envelope-button" @click="exportPdf">💌 导出 PDF</button></footer>
    <el-dialog v-model="rawVisible" width="min(600px,92vw)" class="book-raw-dialog" title="原始行为日志" align-center><template v-if="rawEvidence"><div class="book-raw-meta"><b>#{{rawEvidence.id}}</b><span>{{rawEvidence.continent}}</span><time>{{rawEvidence.time}}</time></div><p>{{rawEvidence.behavior}}</p><pre>{{rawEvidence.raw}}</pre><small>原始日志用于证据回溯，不代表能力分数或排名。</small></template></el-dialog>
  </div>
</template>
