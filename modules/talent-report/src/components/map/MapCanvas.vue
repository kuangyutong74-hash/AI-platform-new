<script setup lang="ts">
import { computed } from "vue";
import type { Talent } from "../../data/mockReport";
import { continentRegions, starPositions } from "../../data/treasureMap";
import ContinentRegion from "./ContinentRegion.vue";
import MapStar from "./MapStar.vue";
const props=defineProps<{talents:Talent[];discovered:string[];eligible:string[];order:string[];burstKey?:string}>();
defineEmits<{select:[talent:Talent];hint:[name:string]}>();
const routePoints=computed(()=>props.order.map(key=>starPositions[key]).filter(Boolean).map(point=>`${point.x},${point.y}`).join(" "));
</script>
<template>
  <section class="map-canvas" aria-label="水彩藏宝图">
    <img class="map-painting" src="/assets/storybook/treasure-map-watercolor-v2.png" alt="" aria-hidden="true"/>
    <svg class="treasure-route" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <polyline v-if="order.length>1" :points="routePoints" fill="none" stroke="#D49A43" stroke-width=".72" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1.7 1.5" vector-effect="non-scaling-stroke"/>
    </svg>
    <ContinentRegion v-for="region in continentRegions" :key="region.name" :region="region" @hint="$emit('hint',$event)"/>
    <MapStar v-for="talent in talents" :key="talent.key" :talent="talent" :position="starPositions[talent.key]" :lit="discovered.includes(talent.key)" :eligible="eligible.includes(talent.key)" :burst="burstKey===talent.key" @select="$emit('select',$event)"/>
  </section>
</template>
