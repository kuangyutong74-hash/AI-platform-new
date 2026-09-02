<script setup lang="ts">
import type { Moment } from "../../data/mockReport";
import ParameterizedMomentScene from "./ParameterizedMomentScene.vue";
defineProps<{ moment:Moment; source?:string }>();
</script>
<template>
  <article class="moment-card" :class="{'is-example':moment.isExample}"><span class="moment-tape" aria-hidden="true"/>
    <div class="moment-scene" :class="[`scene-${moment.kind}`,{'has-photo':moment.imageUrl}]">
      <img v-if="moment.imageUrl" class="moment-photo" :src="moment.imageUrl" :alt="`${moment.source||source}体验过程画面`"/>
      <ParameterizedMomentScene v-else-if="moment.sceneData" :scene="moment.sceneData"/>
      <template v-else-if="moment.kind==='story'"><span class="scene-book" aria-hidden="true"><i/><i/><i/></span><i>角色</i><i>因为…所以…</i></template>
      <template v-else-if="moment.kind==='base'"><span v-for="n in 6" :key="n" :style="{'--n':n}"/><b>≈</b></template>
      <template v-else-if="moment.kind==='chat'"><span class="scene-bubble" aria-hidden="true"/><blockquote>{{moment.quote||'认真说出自己的发现与想法。'}}</blockquote></template>
      <template v-else><small>今日任务</small><b>方案 A　方案 B</b><i>✓ 重新选择</i></template>
    </div>
    <div class="moment-copy"><div class="moment-meta"><small>{{moment.isExample?'示例瞬间':'精彩瞬间'}}</small><time v-if="moment.time">{{moment.time}}</time></div><h3>{{moment.title}}</h3><p>{{moment.caption}}</p><blockquote v-if="moment.quote && moment.kind!=='chat'">“{{moment.quote}}”</blockquote><span>来源：{{moment.source||source}} · {{moment.imageUrl?'真实体验画面':moment.sceneData?'根据游戏过程参数还原':'历史记录未包含场景参数'}}</span></div>
  </article>
</template>
