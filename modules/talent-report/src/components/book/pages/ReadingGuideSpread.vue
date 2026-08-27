<script setup lang="ts">
defineProps<{side:"left"|"right"}>();
const workflow=[
  {image:"report-story-v1.webp",title:"记录",detail:"捕捉真实活动"},
  {image:"report-deep-sea-v1.webp",title:"归类",detail:"标注行为线索"},
  {image:"report-career-v1.webp",title:"综合",detail:"比较跨模块表现"},
  {image:"report-listening-v1.webp",title:"回溯",detail:"保留原始日志"},
];
const sources=[
  {image:"report-listening-v1.webp",title:"倾听之洲",detail:"聊天观察"},
  {image:"report-story-v1.webp",title:"想象之洲",detail:"故事共创"},
  {image:"report-deep-sea-v1.webp",title:"创造之洲",detail:"深海基地重建"},
  {image:"report-career-v1.webp",title:"未来之洲",detail:"职业模拟器"},
];
</script>
<template><div v-if="side==='left'"><p class="page-kicker">READING GUIDE · 01</p><h2>先读懂这本报告</h2><p class="lead-note">这不是一张给孩子打分的成绩单，而是从真实活动中整理出的观察记录。</p><ol class="reading-notes"><li><b>只描述看到的行为</b><span>不凭一次表现给孩子下结论。</span></li><li><b>图标代表证据数量</b><span>不代表能力高低或固定水平。</span></li><li><b>每条证据都可回溯</b><span>点击编号可查看原始行为记录。</span></li><li><b>结合日常综合看待</b><span>把报告当作继续观察的起点。</span></li></ol></div><div v-else><p class="page-kicker">HOW IT WORKS</p><h2>报告是怎么形成的</h2><div class="workflow"><div v-for="step in workflow" :key="step.title"><img :src="`/assets/report-watercolor/${step.image}`" alt=""/><b>{{step.title}}</b><span>{{step.detail}}</span></div></div><h3 class="subheading">线索来自四块探索大陆</h3><div class="source-badges"><span v-for="source in sources" :key="source.title"><img :src="`/assets/report-watercolor/${source.image}`" alt=""/><b>{{source.title}}</b><small>{{source.detail}}</small></span></div><p class="semantic-warning">证据数量 ≠ 能力高低，采集较少也不等于能力不足。</p></div></template>
