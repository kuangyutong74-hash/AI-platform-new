<script setup lang="ts">
import PageTurnCorner from "./PageTurnCorner.vue";
defineProps<{ number:number; canPrev?:boolean; canNext?:boolean }>();
defineEmits<{ prev:[]; next:[] }>();
</script>
<template>
  <section class="book-spread" :aria-label="`魔法书第 ${number} 跨页`">
    <article class="book-sheet book-sheet--left"><div class="sheet-scroll"><slot name="left"/></div><span class="sheet-number">{{number*2-1}}</span><PageTurnCorner side="left" :disabled="!canPrev" @turn="$emit('prev')"/></article>
    <div class="book-spine" aria-hidden="true"/>
    <article class="book-sheet book-sheet--right"><div class="sheet-scroll"><slot name="right"/></div><span class="sheet-number">{{number*2}}</span><PageTurnCorner side="right" :disabled="!canNext" @turn="$emit('next')"/></article>
  </section>
</template>
