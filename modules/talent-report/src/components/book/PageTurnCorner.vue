<script setup lang="ts">
defineProps<{ side:"left"|"right"; disabled?:boolean }>();
defineEmits<{ turn:[] }>();
</script>
<template><button class="turn-corner" :class="`turn-corner--${side}`" :disabled="disabled" :aria-label="side==='left'?'翻到上一跨页':'翻到下一跨页'" @click.stop="$emit('turn')"><span>{{side==='left'?'‹':'›'}}</span></button></template>
