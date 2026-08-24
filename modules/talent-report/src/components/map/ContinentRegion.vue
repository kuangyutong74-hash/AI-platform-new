<script setup lang="ts">
defineProps<{region:{name:string;icon:string;tone:string;x:number;y:number;w:number;h:number}}>();
defineEmits<{hint:[name:string]}>();
</script>
<template><button class="continent-region" :class="`continent-${region.tone}`" :style="{left:`${region.x}%`,top:`${region.y}%`,width:`${region.w}%`,height:`${region.h}%`}" tabindex="-1" aria-hidden="true" @click="$emit('hint',region.name)"><b>{{region.name}}</b><span aria-hidden="true"/></button></template>
