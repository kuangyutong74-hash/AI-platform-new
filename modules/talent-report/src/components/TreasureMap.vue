<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import type { Talent } from "../data/mockReport";
import { generateTalentStories, getEvidenceRecords, getTalentEligibility } from "../api/core";
import { continentHints, loadStarState, mapCopy, resetStarState, saveStarState } from "../data/treasureMap";
import MapCanvas from "./map/MapCanvas.vue";
import StarStoryCard from "./map/StarStoryCard.vue";
import ProgressTrack from "./map/ProgressTrack.vue";
import CelebrationOverlay from "./map/CelebrationOverlay.vue";
import EmptyMap from "./map/EmptyMap.vue";
const props=defineProps<{talents:Talent[]}>();
const emit=defineEmits<{openReport:[];back:[]}>();
const discovered=ref<string[]>([]),order=ref<string[]>([]),eligible=ref<string[]>([]);
const selected=ref<Talent>(),burstKey=ref<string>(),announcement=ref(""),mapHint=ref("");
const childStories=ref<Record<string,string>>({});
const storiesLoading=ref(false),storiesFailed=ref(false);
const celebrating=ref(false),revisit=ref(false);
let burstTimer:number|undefined,hintTimer:number|undefined;
const availableTalents=computed(()=>props.talents);
const isEmpty=computed(()=>props.talents.length===0);
const isComplete=computed(()=>availableTalents.value.length>0&&discovered.value.length===availableTalents.value.length);
const moduleByTalent:Record<string,string>={linguistic:"story",logical:"deep_sea",spatial:"deep_sea",interpersonal:"chat",naturalistic:"deep_sea",intrapersonal:"career"};
onMounted(async()=>{const keys=availableTalents.value.map(t=>t.key);const state=loadStarState(keys);discovered.value=state.discovered;order.value=state.order;const [response,evidenceResponse]=await Promise.all([getTalentEligibility(),getEvidenceRecords()]);eligible.value=response?response.talents.filter(item=>item.eligible&&keys.includes(item.key)).map(item=>item.key):[];const levelOne=(evidenceResponse?.records||[]).find(item=>item.moduleId==="deep_sea"&&item.eventType==="deep-sea.spatial-task-completed.v1"&&Number(item.payload.level)===1);if(levelOne){const successful=Number(levelOne.payload.successfulPairs??4),total=Number(levelOne.payload.totalPairs??4),accuracy=Math.round(Number(levelOne.payload.accuracyPercent??successful/Math.max(total,1)*100)),checks=levelOne.payload.checkAttempts,adjustments=Number(levelOne.payload.adjustmentCount??0);childStories.value.naturalistic=`第一关生物配对中，你成功配对了 ${successful}/${total} 组，最终准确度 ${accuracy}%（${successful===total?'全部配对成功':'尚未全部配对成功'}）${checks===undefined?'':`，检查了 ${checks} 次`}，修正了 ${adjustments} 次。`}if(response){const validDiscovered=discovered.value.filter(key=>eligible.value.includes(key));if(validDiscovered.length!==discovered.value.length){discovered.value=validDiscovered;order.value=order.value.filter(key=>validDiscovered.includes(key));saveStarState({discovered:discovered.value,order:order.value})}}revisit.value=keys.length>0&&discovered.value.length===keys.length;if(response?.talents.some(item=>item.completedModules?.length)){storiesLoading.value=true;storiesFailed.value=false;const result=await generateTalentStories();storiesLoading.value=false;storiesFailed.value=!result;const stories=Object.fromEntries((result?.stories||[]).map(item=>[item.key,item.story]));if(levelOne)stories.naturalistic=childStories.value.naturalistic;childStories.value={...childStories.value,...Object.fromEntries(response.talents.filter(item=>keys.includes(item.key)).map(item=>{const moduleId=moduleByTalent[item.key];return [item.key,item.completedModules.includes(moduleId)?stories[item.key]||"":""]}).filter(([,text])=>Boolean(text)))}}});
onBeforeUnmount(()=>{window.clearTimeout(burstTimer);window.clearTimeout(hintTimer)});
function selectStar(talent:Talent){if(discovered.value.includes(talent.key)||eligible.value.includes(talent.key)){selected.value=talent;return}announcement.value=mapCopy.locked(talent.continent)}
function collectStar(talent:Talent){if(!eligible.value.includes(talent.key)||discovered.value.includes(talent.key))return;discovered.value=[...discovered.value,talent.key];order.value=[...order.value,talent.key];saveStarState({discovered:discovered.value,order:order.value});burstKey.value=talent.key;announcement.value=mapCopy.foundBurst(talent.childName);window.clearTimeout(burstTimer);burstTimer=window.setTimeout(()=>{burstKey.value=undefined},900);selected.value=undefined;if(discovered.value.length===availableTalents.value.length)celebrating.value=true}
function resetMap(){resetStarState();discovered.value=[];order.value=[];selected.value=undefined;celebrating.value=false;revisit.value=false;announcement.value="星星回到藏宝图上啦"}
function showHint(name:string){mapHint.value=continentHints[name]||"";window.clearTimeout(hintTimer);hintTimer=window.setTimeout(()=>{mapHint.value=""},2500)}
function visit(url:string){if(url)location.href=url}
</script>
<template><section class="treasure-map-app"><EmptyMap v-if="isEmpty" @back="emit('back')"/><template v-else><p v-if="revisit" class="revisit-note">{{mapCopy.revisit}}</p><MapCanvas :talents="availableTalents" :discovered="discovered" :eligible="eligible" :order="order" :burst-key="burstKey" @select="selectStar" @hint="showHint"/><div class="map-message" aria-live="polite">{{announcement||mapHint}}</div><ProgressTrack :count="discovered.length" :total="availableTalents.length"/><footer class="treasure-actions"><button class="map-back" @click="emit('back')">{{mapCopy.back}}</button><button class="map-reset" @click="resetMap">{{mapCopy.reset}}</button><button v-if="isComplete&&!celebrating" class="map-report" @click="emit('openReport')">{{mapCopy.celebratePrimary}}</button></footer><StarStoryCard v-if="selected" :talent="selected" :story="childStories[selected.key]" :loading="storiesLoading" :failed="storiesFailed" :order="order.indexOf(selected.key)+1" :can-collect="eligible.includes(selected.key)&&!discovered.includes(selected.key)" @close="selected=undefined" @collect="collectStar(selected)" @visit="visit"/><CelebrationOverlay v-if="celebrating" :talents="availableTalents" @open-report="emit('openReport')" @close="celebrating=false;revisit=true"/></template></section></template>
