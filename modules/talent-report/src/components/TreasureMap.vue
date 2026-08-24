<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import type { Talent } from "../data/mockReport";
import { continentHints, loadStarState, mapCopy, saveStarState } from "../data/treasureMap";
import MapCanvas from "./map/MapCanvas.vue";
import StarStoryCard from "./map/StarStoryCard.vue";
import ProgressTrack from "./map/ProgressTrack.vue";
import CelebrationOverlay from "./map/CelebrationOverlay.vue";
import EmptyMap from "./map/EmptyMap.vue";

const props=defineProps<{talents:Talent[]}>();
const emit=defineEmits<{openReport:[];back:[]}>();
const discovered=ref<string[]>([]);
const order=ref<string[]>([]);
const selected=ref<Talent>();
const burstKey=ref<string>();
const announcement=ref("");
const mapHint=ref("");
const celebrating=ref(false);
const pendingCelebration=ref(false);
const revisit=ref(false);
let burstTimer:number|undefined;
let hintTimer:number|undefined;

const availableTalents=computed(()=>props.talents);
const isEmpty=computed(()=>props.talents.length===0||props.talents.every(talent=>talent.evidence.length===0));
const isComplete=computed(()=>availableTalents.value.length>0&&discovered.value.length===availableTalents.value.length);

onMounted(()=>{
  const state=loadStarState(availableTalents.value.map(talent=>talent.key));
  discovered.value=state.discovered;
  order.value=state.order;
  revisit.value=availableTalents.value.length>0&&state.discovered.length===availableTalents.value.length;
});
onBeforeUnmount(()=>{window.clearTimeout(burstTimer);window.clearTimeout(hintTimer)});

function selectStar(talent:Talent){
  if(discovered.value.includes(talent.key)){selected.value=talent;return}
  discovered.value=[...discovered.value,talent.key];
  order.value=[...order.value,talent.key];
  saveStarState({discovered:discovered.value,order:order.value});
  burstKey.value=talent.key;
  announcement.value=mapCopy.foundBurst(talent.childName);
  window.clearTimeout(burstTimer);
  burstTimer=window.setTimeout(()=>{burstKey.value=undefined},900);
  selected.value=talent;
  pendingCelebration.value=discovered.value.length===availableTalents.value.length;
}
function closeStory(){
  selected.value=undefined;
  if(pendingCelebration.value){pendingCelebration.value=false;celebrating.value=true}
}
function showHint(name:string){
  mapHint.value=continentHints[name]||"";
  window.clearTimeout(hintTimer);
  hintTimer=window.setTimeout(()=>{mapHint.value=""},2500);
}
function visit(url:string){if(url)location.href=url}
</script>

<template>
  <section class="treasure-map-app">
    <EmptyMap v-if="isEmpty" @back="emit('back')"/>
    <template v-else>
      <p v-if="revisit" class="revisit-note">{{mapCopy.revisit}}</p>
      <MapCanvas :talents="availableTalents" :discovered="discovered" :order="order" :burst-key="burstKey" @select="selectStar" @hint="showHint"/>
      <div class="map-message" aria-live="polite">{{announcement||mapHint}}</div>
      <ProgressTrack :count="discovered.length" :total="availableTalents.length"/>
      <footer class="treasure-actions">
        <button class="map-back" @click="emit('back')">{{mapCopy.back}}</button>
        <button v-if="isComplete&&!celebrating" class="map-report" @click="emit('openReport')">{{mapCopy.celebratePrimary}}</button>
      </footer>
      <StarStoryCard v-if="selected" :talent="selected" :order="order.indexOf(selected.key)+1" @close="closeStory" @visit="visit"/>
      <CelebrationOverlay v-if="celebrating" :talents="availableTalents" @open-report="emit('openReport')" @close="celebrating=false;revisit=true"/>
    </template>
  </section>
</template>
