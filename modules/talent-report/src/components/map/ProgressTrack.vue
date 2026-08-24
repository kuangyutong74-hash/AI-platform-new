<script setup lang="ts">
import { mapCopy } from "../../data/treasureMap";
defineProps<{count:number;total?:number}>();
</script>
<template><section class="progress-track" aria-live="polite" :aria-label="mapCopy.progressAria(count)"><div class="progress-stars" aria-hidden="true"><i v-for="n in (total||6)" :key="n" :class="{filled:n<=count}">★</i></div><div><b>{{mapCopy.progress(count)}}</b><span>{{mapCopy.progressHint}}</span></div></section></template>
