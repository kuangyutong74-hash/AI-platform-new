<script setup lang="ts">
import type { Moment } from "../../data/mockReport";
defineProps<{ moment:Moment; source:string }>();
</script>
<template><article class="moment-card"><div class="moment-scene" :class="`scene-${moment.kind}`"><template v-if="moment.kind==='story'"><span class="scene-book">📖</span><i>角色</i><i>因为…所以…</i></template><template v-else-if="moment.kind==='base'"><span v-for="n in 6" :key="n" :style="{'--n':n}"/><b>≈</b></template><template v-else-if="moment.kind==='chat'"><i>💬</i><blockquote>{{moment.quote||'我发现了一个不一样的地方……'}}</blockquote></template><template v-else><small>今日任务</small><b>方案 A　方案 B</b><i>✓ 重新选择</i></template></div><div class="moment-copy"><small>{{moment.id}} · 精彩瞬间</small><h3>{{moment.title}}</h3><p>{{moment.caption}}</p><blockquote v-if="moment.quote && moment.kind!=='chat'">“{{moment.quote}}”</blockquote><span>来源：{{source}}</span></div></article></template>
