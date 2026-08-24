<script setup lang="ts">import { mapCopy } from "../../data/treasureMap";defineEmits<{back:[]}>()</script>
<template><section class="empty-map"><img src="/assets/storybook/planet-explorer.png" alt=""/><p>{{mapCopy.empty}}</p><button @click="$emit('back')">{{mapCopy.back}}</button></section></template>
