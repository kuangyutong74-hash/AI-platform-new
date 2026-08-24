<script setup lang="ts">
import RadarChart from "../../RadarChart.vue";
import type { Talent } from "../../../data/mockReport";
defineProps<{ side:"left"|"right"; talents:Talent[]; insights:string[]; richNames:string[]; fewNames:string[] }>();
defineEmits<{ evidence:[id:string] }>();
function parts(text:string){return text.split(/(\[E\d+\])/g).filter(Boolean)}
</script>
<template><div v-if="side==='left'"><p class="page-kicker">WATERCOLOR MAP · 02</p><h2>六类智能 · 阶段性观察总览</h2><RadarChart :talents="talents"/><div class="watercolor-legend"><span v-for="talent in talents" :key="talent.key"><i :style="{background:talent.color}"/>{{talent.adultName}}</span></div><p class="semantic-warning">图表只表示采集到的行为证据数量，不代表能力高低。</p></div><div v-else><p class="page-kicker">WHOLE PICTURE</p><h2>整体观测结论</h2><div class="insight-notes"><p v-for="(insight,index) in insights" :key="index"><span v-for="part in parts(insight)" :key="part"><button v-if="/^\[E\d+\]$/.test(part)" @click.stop="$emit('evidence',part.slice(1,-1))">{{part}}</button><template v-else>{{part}}</template></span></p></div><div class="coverage-note"><h3>证据覆盖情况</h3><p><b>线索较丰富：</b>{{richNames.length?richNames.join('、'):'正在持续积累'}}</p><p><b>采集行为较少：</b>{{fewNames.length?fewNames.join('、'):'本阶段各维度均有记录'}}</p><small>覆盖情况只说明采集量，不作能力判断。</small></div><blockquote class="closing-quote">天赋不是标签，而是一段持续被看见、被支持的成长过程。</blockquote></div></template>
