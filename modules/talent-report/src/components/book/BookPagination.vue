<script setup lang="ts">
defineProps<{ current:number }>();
defineEmits<{ select:[index:number] }>();
</script>
<template><nav class="bookmark-nav" aria-label="跨页导航"><button v-for="n in 9" :key="n" :class="{active:current===n-1}" :aria-current="current===n-1?'page':undefined" :aria-label="`前往第 ${n} 跨页`" @click="$emit('select',n-1)">{{n}}</button></nav></template>
