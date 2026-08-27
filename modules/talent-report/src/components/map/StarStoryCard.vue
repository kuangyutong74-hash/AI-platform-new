<script setup lang="ts">
import type { Talent } from "../../data/mockReport";
import { mapCopy, starConfessions, stickerByKey } from "../../data/treasureMap";
defineProps<{talent:Talent;order:number;canCollect:boolean}>();
defineEmits<{close:[];collect:[];visit:[url:string]}>();
</script>
<template><div class="story-card-backdrop" @click.self="$emit('close')"><article class="star-story-card" role="dialog" aria-modal="true" :aria-labelledby="`story-${talent.key}`"><p>{{mapCopy.source(talent.continent)}}</p><small v-if="order>0">{{mapCopy.order(order)}}</small><img :src="stickerByKey[talent.key]" alt=""/><h2 :id="`story-${talent.key}`">{{talent.childName}}</h2><blockquote>{{starConfessions[talent.key]}}</blockquote><div><button class="story-visit" @click="$emit('visit',talent.moduleUrl)">{{mapCopy.visit(talent.continent)}}</button><button v-if="canCollect" class="story-collect" @click="$emit('collect')">{{mapCopy.collected}}</button><button v-else class="story-collect" @click="$emit('close')">{{mapCopy.closeStory}}</button></div></article></div></template>
