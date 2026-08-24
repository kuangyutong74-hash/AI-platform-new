<script setup lang="ts">
import type { Talent } from "../../data/mockReport";
import { mapCopy, starConfessions, stickerByKey } from "../../data/treasureMap";
defineProps<{talent:Talent;order:number}>();
defineEmits<{close:[];visit:[url:string]}>();
</script>
<template><div class="story-card-backdrop" @click.self="$emit('close')"><article class="star-story-card" role="dialog" aria-modal="true" :aria-labelledby="`story-${talent.key}`"><p>{{mapCopy.source(talent.continent)}}</p><small>{{mapCopy.order(order)}}</small><img :src="stickerByKey[talent.key]" alt=""/><h2 :id="`story-${talent.key}`">{{talent.childName}}</h2><blockquote>{{starConfessions[talent.key]}}</blockquote><div><button class="story-visit" @click="$emit('visit',talent.moduleUrl)">{{mapCopy.visit(talent.continent)}}</button><button class="story-collect" @click="$emit('close')">{{mapCopy.collected}}</button></div></article></div></template>
