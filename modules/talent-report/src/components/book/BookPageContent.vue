<script setup lang="ts">
import { computed } from "vue";
import type { GeneratedReport } from "../../api/core";
import type { Evidence, Talent } from "../../data/mockReport";
import AdviceSpread from "./pages/AdviceSpread.vue";
import DimensionSpread from "./pages/DimensionSpread.vue";
import OverviewSpread from "./pages/OverviewSpread.vue";
import ReadingGuideSpread from "./pages/ReadingGuideSpread.vue";

const props=defineProps<{spreadIndex:number;side:"left"|"right";talents:Talent[];insights:string[];richNames:string[];fewNames:string[];family:string[];teacher:string[];liveReport?:GeneratedReport;highlightedId?:string}>();
const emit=defineEmits<{open:[evidence:Evidence];evidence:[id:string];finish:[]}>();
const talent=computed(()=>props.spreadIndex>=2&&props.spreadIndex<=7?props.talents[props.spreadIndex-2]:undefined);
const analysis=computed(()=>talent.value?props.liveReport?.dimensions.find(item=>item.key===talent.value?.key)?.analysis:undefined);
const adultObservation=computed(()=>talent.value?props.liveReport?.dimensions.find(item=>item.key===talent.value?.key)?.adult_observation:undefined);
</script>

<template>
  <ReadingGuideSpread v-if="spreadIndex===0" :side="side"/>
  <OverviewSpread v-else-if="spreadIndex===1" :side="side" :talents="talents" :insights="insights" :rich-names="richNames" :few-names="fewNames" @evidence="emit('evidence',$event)"/>
  <DimensionSpread v-else-if="talent" :side="side" :talent="talent" :analysis="analysis" :adult-observation="adultObservation" :highlighted-id="highlightedId" @open="emit('open',$event)"/>
  <AdviceSpread v-else :side="side" :family="family" :teacher="teacher" @finish="emit('finish')"/>
</template>
