<script setup lang="ts">
import type { Talent } from "../../data/mockReport";
import { mapCopy, stickerByKey } from "../../data/treasureMap";
defineProps<{talent:Talent;story?:string;order:number;canCollect:boolean}>();
defineEmits<{close:[];collect:[];visit:[url:string]}>();
</script>
<template><div class="story-card-backdrop" @click.self="$emit('close')"><article class="star-story-card" role="dialog" aria-modal="true" :aria-labelledby="`story-${talent.key}`"><header><div><p>{{mapCopy.source(talent.continent)}}</p><small v-if="order>0">{{mapCopy.order(order)}}</small></div><img :src="stickerByKey[talent.key]" alt=""/></header><h2 :id="`story-${talent.key}`">{{talent.childName}}</h2><p class="story-card-label">我的探索小发现</p><blockquote :class="{'is-empty':!story}">{{story||'还没有可回看的探索记录。去这块大陆完成一次游戏后，我会把你的真实表现写在这里。'}}</blockquote><footer><button class="story-visit" @click="$emit('visit',talent.moduleUrl)">{{mapCopy.visit(talent.continent)}}</button><button v-if="canCollect" class="story-collect" @click="$emit('collect')">{{mapCopy.collected}}</button><button v-else class="story-collect" @click="$emit('close')">{{mapCopy.closeStory}}</button></footer></article></div></template>
