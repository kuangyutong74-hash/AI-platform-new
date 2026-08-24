<script setup lang="ts">
defineProps<{ range:string; opening?:boolean }>();
defineEmits<{ open:[] }>();
const stickers=["talent-storybook.png","talent-puzzle.png","talent-blocks.png","talent-friends.png","talent-mirror.png","talent-leaf.png"];
</script>
<template>
  <section class="magic-cover-stage" :class="{opening}" aria-label="孩子的天赋星图魔法书封面">
    <div class="book-decor" aria-hidden="true"><i v-for="n in 6" :key="`star-${n}`" class="decor-star" :style="{ '--n':n }">✦</i><i v-for="n in 2" :key="`glint-${n}`" class="decor-glint" :style="{ '--n':n }"/><img class="book-ornament ornament-moon" src="/assets/storybook/cover-decor-2.png" alt=""/><img class="book-ornament ornament-botanical" src="/assets/storybook/cover-decor-6.png" alt=""/><img class="book-ornament ornament-comet" src="/assets/storybook/cover-decor-7.png" alt=""/><img class="book-ornament ornament-stardust" src="/assets/storybook/cover-decor-1.png" alt=""/><div class="raffia raffia-left"><i v-for="n in 5" :key="n"/></div><div class="raffia raffia-right"><i v-for="n in 5" :key="n"/></div></div>
    <div class="book-opening-pages" aria-hidden="true"><span/><i/><span/></div>
    <button class="closed-magic-book" aria-label="打开孩子的天赋星图魔法书" @click="$emit('open')">
      <img src="/assets/storybook/magic-report-book-cutout-v2.png" alt="暖酒红色水彩魔法书"/>
      <div class="cover-lettering"><small>AI BOLE · 阶段观察</small><h1>孩子的天赋星图</h1></div>
      <div class="cover-stickers" aria-hidden="true"><img v-for="(sticker,index) in stickers" :key="sticker" :src="`/assets/storybook/${sticker}`" :style="{'--i':index}" alt=""/></div>
    </button>
    <div class="cover-caption"><p>阶段性行为证据报告 · 家长 / 教师阅读版</p><time>{{range}}</time></div>
    <button class="wax-seal" @click="$emit('open')"><b>✦</b><span>打开<br>魔法书</span></button>
  </section>
</template>
