<script setup lang="ts">
import type { Evidence, Talent } from "../../../data/mockReport";
import EvidenceCard from "../EvidenceCard.vue";
import MomentCard from "../MomentCard.vue";
defineProps<{ side:"left"|"right"; talent:Talent; highlightedId?:string }>();
defineEmits<{ open:[evidence:Evidence] }>();
const sticker:Record<string,string>={linguistic:"talent-storybook.png",logical:"talent-puzzle.png",spatial:"talent-blocks.png",interpersonal:"talent-friends.png",intrapersonal:"talent-mirror.png",naturalistic:"talent-leaf.png"};
</script>
<template><div class="dimension-page" :style="{'--talent':talent.color}"><template v-if="side==='left'"><header class="dimension-header"><img :src="`/assets/storybook/${sticker[talent.key]}`" alt=""/><div><p class="page-kicker">BEHAVIOR EVIDENCE</p><h2>{{talent.adultName}} <small>{{talent.childName}}</small></h2><span>{{talent.label}}</span></div></header><div class="evidence-list"><EvidenceCard v-for="item in talent.evidence" :key="item.id" :evidence="item" :highlighted="highlightedId===item.id" @open="$emit('open',$event)"/></div><p class="page-tip">证据按时间与跨模块一致性整理，可点击编号回溯原始日志。</p></template><template v-else><p class="page-kicker">MAGICAL MOMENTS</p><h2>孩子的精彩瞬间</h2><div v-if="talent.moments?.length" class="moment-stack"><MomentCard v-for="moment in talent.moments" :key="moment.id" :moment="moment" :source="talent.continent+' · '+talent.module"/></div><div v-else class="moment-empty">✦<b>本阶段暂无快照</b><span>请结合左侧证据继续观察。</span></div><p class="adult-observe-note">给成人的观察提示：结合证据 {{talent.evidence.map(item=>'#'+item.id).join('、')}}，继续留意孩子如何表达、尝试、修改和重新开始。</p></template></div></template>
