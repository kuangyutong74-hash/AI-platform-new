<script setup lang="ts">
import * as echarts from "echarts";
import { onBeforeUnmount, onMounted, ref } from "vue";
import type { Talent } from "../data/mockReport";
const props=defineProps<{talents:Talent[]}>(); const host=ref<HTMLDivElement>(); let chart:echarts.ECharts|undefined,observer:ResizeObserver|undefined;
onMounted(()=>{if(!host.value)return;chart=echarts.init(host.value);const evidenceAmount=(t:Talent)=>Math.min(5,1+t.evidence.length*1.1+t.evidence.filter(item=>item.level==="strong").length*.35);chart.setOption({radar:{radius:"64%",splitNumber:4,indicator:props.talents.map(t=>({name:t.adultName,max:5})),axisName:{color:"#dcdafa",fontSize:12},splitArea:{areaStyle:{color:["rgba(102,82,180,.03)","rgba(102,82,180,.08)"]}},splitLine:{lineStyle:{color:"rgba(169,151,236,.2)"}},axisLine:{lineStyle:{color:"rgba(169,151,236,.2)"}}},series:[{type:"radar",symbol:"circle",symbolSize:6,lineStyle:{color:"#9b8cff",width:2},itemStyle:{color:"#c6baff"},areaStyle:{color:"rgba(127,112,238,.27)"},data:[{value:props.talents.map(evidenceAmount)}]}]});observer=new ResizeObserver(()=>chart?.resize());observer.observe(host.value)});onBeforeUnmount(()=>{observer?.disconnect();chart?.dispose()});
</script>
<template><div ref="host" class="radar-chart" role="img" aria-label="六类智能阶段性采集证据数量分布图，不代表能力强弱"></div></template>
