<script setup lang="ts">
import { computed } from "vue";
import type { Evidence, Talent } from "../../../data/mockReport";
import EvidenceCard from "../EvidenceCard.vue";
import MomentCard from "../MomentCard.vue";
const props=defineProps<{side:"left"|"right";talent:Talent;analysis?:string;adultObservation?:string;highlightedId?:string}>();
defineEmits<{open:[evidence:Evidence]}>();
const observationItems=computed(()=>props.adultObservation?.split(/[；\n]+/).map(item=>item.trim()).filter(Boolean)||[]);
const sticker:Record<string,string>={linguistic:"talent-storybook.png",logical:"talent-puzzle.png",spatial:"talent-blocks.png",interpersonal:"talent-friends.png",intrapersonal:"talent-mirror.png",naturalistic:"talent-leaf.png"};
</script>
<template><div class="dimension-page" :style="{'--talent':talent.color}">
  <template v-if="side==='left'">
    <header class="dimension-header"><img :src="`/assets/storybook/${sticker[talent.key]}`" alt=""/><div><p class="page-kicker">BEHAVIOR EVIDENCE</p><h2>{{talent.adultName}} <small>{{talent.childName}}</small></h2><span>{{talent.label}}</span></div></header>
    <p class="dimension-analysis" :class="{'is-empty':!talent.evidence.length}">{{analysis||'报告智能体正在根据本次真实游戏记录整理具体表现…'}}</p>
    <div v-if="talent.evidence.length" class="evidence-list"><EvidenceCard v-for="item in talent.evidence" :key="item.id" :evidence="item" :highlighted="highlightedId===item.id" @open="$emit('open',$event)"/></div>
    <div v-else class="evidence-empty">还没有收集到与这一维度相关的行为记录</div>
    <p class="page-tip">行为记录按时间与跨模块一致性整理，可点击“查看回顾”了解完整过程。</p>
  </template>
  <template v-else>
    <p class="page-kicker">MAGICAL MOMENTS</p><h2>孩子的精彩瞬间</h2>
    <div v-if="talent.moments?.length" class="moment-stack"><MomentCard v-for="moment in talent.moments" :key="moment.id" :moment="moment" :source="talent.continent+' · '+talent.module"/></div>
    <div v-else class="moment-empty"><b>这一页正等着孩子来点亮</b><span>完成一次相关探索后，真实的精彩瞬间会自动收藏到这里。</span></div>
    <section class="adult-observe-note"><b>给成人的延伸观察</b><ul v-if="observationItems.length"><li v-for="item in observationItems" :key="item">{{item}}</li></ul><span v-else>报告智能体正在结合本次表现生成延伸观察清单…</span></section>
  </template>
</div></template>
