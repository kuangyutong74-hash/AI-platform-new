<script setup lang="ts">
import type { MomentSceneData } from "../../data/mockReport";
import DeepSeaPipelineScene from "./DeepSeaPipelineScene.vue";
defineProps<{scene:MomentSceneData}>();
</script>
<template>
  <DeepSeaPipelineScene v-if="scene.type==='deep_sea_pipeline'" :scene="scene"/>
  <div v-else-if="scene.type==='deep_sea_ecology'" class="parameter-scene ecology-replay"><div class="ecology-pairs"><div v-for="(pair,index) in scene.pairs" :key="pair.label||index" :class="{done:pair.done}"><i/><span>{{pair.label||`生态组合 ${index+1}`}}</span><b>{{pair.done?'匹配完成':'继续观察'}}</b></div></div><footer>完成 {{scene.pairs.filter(item=>item.done).length}} 组 · 调整 {{scene.adjustments}} 次<span v-if="scene.checks"> · 检查 {{scene.checks}} 次</span></footer></div>
  <div v-else-if="scene.type==='deep_sea_mediation'" class="parameter-scene mediation-replay"><div class="mediation-people"><span><i/>壳壳</span><div><b>{{scene.harmony}}%</b><small>和解度</small></div><span><i/>彩彩</span></div><p>{{scene.solution||'孩子尝试倾听双方需要，并提出兼顾彼此的办法。'}}</p><footer>完成 {{scene.rounds}} 轮协商</footer></div>
  <div v-else-if="scene.type==='story'" class="parameter-scene story-replay"><div class="story-paper"><h4>{{scene.title||'我的共创故事'}}</h4><p>{{scene.words||'孩子和故事导演一起完成了这段故事。'}}</p><span>{{scene.mode==='child'?'孩子独立写下结尾':'与故事导演共同完成'}} · {{scene.turns}} 轮</span></div></div>
  <div v-else-if="scene.type==='chat'" class="parameter-scene chat-replay"><header>入口主题：“{{scene.topic}}”</header><small>会话中的另一段表达</small><blockquote>{{scene.words||'孩子认真表达了自己的想法。'}}</blockquote><footer>整场会话共 {{scene.turns}} 轮 · 两项记录未标为同一轮</footer></div>
  <div v-else class="parameter-scene career-replay"><h4>{{scene.career||'职业体验'}}的一天</h4><div class="career-stages"><i v-for="n in scene.stages" :key="n" :class="{done:n<=scene.completed}"/></div><p>完成 {{scene.completed}} / {{scene.stages}} 个阶段</p><footer>调整 {{scene.adjustments}} 次 · 重试 {{scene.retries}} 次 · 查看提示 {{scene.hints}} 次</footer></div>
</template>
