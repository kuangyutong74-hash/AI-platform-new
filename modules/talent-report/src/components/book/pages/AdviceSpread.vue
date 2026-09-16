<script setup lang="ts">
import { computed } from "vue";
import type { ParentAnswerReference } from "../../../api/core";
const props=defineProps<{side:"left"|"right";family:string[];teacher:string[];familyAttributions:ParentAnswerReference[][];teacherAttributions:ParentAnswerReference[][]}>();
defineEmits<{finish:[]}>();
const items=computed(()=>props.side==='left'?props.family:props.teacher);
const attributions=computed(()=>props.side==='left'?props.familyAttributions:props.teacherAttributions);
</script>
<template><div class="advice-page"><p class="page-kicker">GROWING TOGETHER · 10</p><h2>{{side==='left'?'把发现带回家':'把发现带回课堂'}}</h2><div class="advice-intro"><img :src="`/assets/report-watercolor/${side==='left'?'report-family-v1.webp':'report-classroom-v1.webp'}`" alt=""/><p>{{side==='left'?'在日常里留一点空间，让孩子自然地展示自己的方法。':'在课堂里提供多种路径，让每种思考方式都有机会被看见。'}}</p></div><div class="letter-notes"><article v-for="(item,index) in items" :key="item"><i>{{index+1}}</i><span>{{index+1}}</span><p>{{item}}</p><details v-if="attributions[index]?.length" class="parent-answer-note"><summary>参考了您的回答</summary><p v-for="source in attributions[index]" :key="`${source.question}-${source.answer}`"><b>{{source.question}}</b><span>{{source.answer}}</span></p></details></article></div><blockquote>继续给孩子机会去表达、尝试、修改和重新开始。</blockquote><button v-if="side==='right'" class="finished-badge" @click.stop="$emit('finish')"><img src="/assets/report-watercolor/report-classroom-v1.webp" alt=""/><span>读完啦</span></button></div></template>
