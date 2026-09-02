<script setup lang="ts">
import type { Talent } from "../../data/mockReport";
import { mapCopy, stickerByKey } from "../../data/treasureMap";
defineProps<{talent:Talent;story?:string;loading:boolean;failed:boolean;order:number;canCollect:boolean}>();
defineEmits<{close:[];collect:[];visit:[url:string]}>();
</script>
<template><div class="story-card-backdrop" @click.self="$emit('close')"><article class="star-story-card" role="dialog" aria-modal="true" :aria-labelledby="`story-${talent.key}`"><header><div><p>{{mapCopy.source(talent.continent)}}</p><small v-if="order>0">{{mapCopy.order(order)}}</small></div><img :src="stickerByKey[talent.key]" alt=""/></header><h2 :id="`story-${talent.key}`">{{talent.childName}}</h2><p class="story-card-label">智能体整理的探索小发现</p><blockquote :class="{'is-empty':!story}">{{story||(loading?'智能体正在阅读这次游戏记录，马上就能写好这颗星的专属发现……':failed?'智能体这次没有连接成功，请稍后重新打开藏宝图。':'这次体验已经完成，但保存的记录还不足以描述这颗星。')}}</blockquote><footer><button class="story-visit" @click="$emit('visit',talent.moduleUrl)">{{mapCopy.visit(talent.continent)}}</button><button v-if="canCollect" class="story-collect" @click="$emit('collect')">{{mapCopy.collected}}</button><button v-else class="story-collect" @click="$emit('close')">{{mapCopy.closeStory}}</button></footer></article></div></template>
