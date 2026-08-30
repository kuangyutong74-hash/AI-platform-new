<script setup lang="ts">
import type { DeepSeaPipelineScene } from "../../data/mockReport";
const props=defineProps<{scene:DeepSeaPipelineScene}>();
const key=(row:number,col:number)=>`${row}-${col}`;
const pipes=new Map(props.scene.pipes.map(item=>[key(item.row,item.col),item]));
const obstacles=new Map(props.scene.obstacles.map(item=>[key(item.row,item.col),item]));
const cells=Array.from({length:props.scene.rows*props.scene.cols},(_,index)=>({row:Math.floor(index/props.scene.cols),col:index%props.scene.cols}));
</script>

<template><div class="pipeline-replay" :style="{'--pipeline-cols':scene.cols}" :aria-label="`洋流电网完成布局，共使用${scene.pipes.length}根管道`"><div class="pipeline-grid"><div v-for="cell in cells" :key="key(cell.row,cell.col)" class="pipeline-cell" :class="{'is-start':cell.row===scene.start.row&&cell.col===scene.start.col,'is-end':cell.row===scene.end.row&&cell.col===scene.end.col,'has-obstacle':obstacles.has(key(cell.row,cell.col))}"><span v-if="pipes.has(key(cell.row,cell.col))" class="pipeline-pipe" :class="{'is-energized':pipes.get(key(cell.row,cell.col))?.energized}" :style="{transform:`rotate(${(pipes.get(key(cell.row,cell.col))?.rot||0)*90}deg)`}">{{pipes.get(key(cell.row,cell.col))?.def}}</span><i v-else-if="obstacles.has(key(cell.row,cell.col))" :class="`obstacle-${obstacles.get(key(cell.row,cell.col))?.kind}`"/><b v-if="cell.row===scene.start.row&&cell.col===scene.start.col">起</b><b v-else-if="cell.row===scene.end.row&&cell.col===scene.end.col">终</b></div></div><footer><span>{{scene.connected?'能源已连通':'保留本次尝试'}}</span><span>旋转 {{scene.rotateCount}} 次</span><span v-if="scene.checkAttempts">检查 {{scene.checkAttempts}} 次</span></footer></div></template>
