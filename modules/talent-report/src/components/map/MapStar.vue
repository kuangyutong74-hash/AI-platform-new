<script setup lang="ts">
import { computed } from "vue";
import type { Talent } from "../../data/mockReport";
import { mapCopy, starAria, stickerByKey, type MapPosition } from "../../data/treasureMap";
const props=defineProps<{talent:Talent;position:MapPosition;lit:boolean;eligible:boolean;burst?:boolean}>();
defineEmits<{select:[talent:Talent]}>();
const label=computed(()=>props.lit?starAria.lit(props.talent.childName):props.eligible?starAria.eligible(props.talent.childName):starAria.sealed(props.talent.childName,props.talent.continent));
</script>
<template><button class="map-star" :class="{lit,eligible,burst}" :style="{left:`${position.x}%`,top:`${position.y}%`,'--star-color':talent.color}" :aria-label="label" @click="$emit('select',talent)"><span class="sealed-shape"><svg viewBox="0 0 64 64" aria-hidden="true"><path d="M32 3 40 22l20 2-15 13 5 20-18-11-18 11 5-20L4 24l20-2Z"/><path class="seal-ring" d="M25 30a7 7 0 1 1 14 0v5H25Zm3 5v10h8V35"/></svg></span><span class="lit-shape"><img :src="stickerByKey[talent.key]" alt=""/><i v-if="burst" v-for="n in 4" :key="n" :style="{'--spark':n}"/></span><b v-if="lit">{{talent.childName}}</b><em v-else>{{eligible?mapCopy.collected:mapCopy.sealHover}}</em></button></template>
