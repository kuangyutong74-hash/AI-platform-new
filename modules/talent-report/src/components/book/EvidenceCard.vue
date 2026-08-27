<script setup lang="ts">
import type { Evidence } from "../../data/mockReport";
defineProps<{evidence:Evidence;highlighted?:boolean}>();
defineEmits<{open:[evidence:Evidence]}>();
</script>
<template><article :id="`evidence-${evidence.id}`" class="evidence-card" :class="{highlighted}"><button class="evidence-badge" aria-label="查看这条行为记录的过程回顾" @click.stop="$emit('open',evidence)"><span>行为记录</span><small>查看回顾</small></button><div class="evidence-content"><p>{{evidence.behavior}}</p><div class="evidence-meta"><span>{{evidence.continent}}</span><time>{{evidence.time}}</time><em :class="evidence.level"><img :src="evidence.level==='strong'?'/assets/dossier/tag-strong.png':'/assets/dossier/tag-reference.png'" alt=""/>{{evidence.level==='strong'?'较完整记录':'参考线索'}}</em></div></div></article></template>
