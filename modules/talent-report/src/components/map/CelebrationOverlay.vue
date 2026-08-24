<script setup lang="ts">
import type { Talent } from "../../data/mockReport";
import { mapCopy, stickerByKey } from "../../data/treasureMap";
defineProps<{talents:Talent[]}>();
defineEmits<{openReport:[];close:[]}>();
</script>
<template><section class="celebration-overlay" role="dialog" aria-modal="true" :aria-labelledby="'celebrate-title'"><div class="celebration-stars" aria-hidden="true"><img v-for="(talent,index) in talents" :key="talent.key" :src="stickerByKey[talent.key]" :style="{'--i':index}" alt=""/></div><h2 id="celebrate-title">{{mapCopy.celebrateTitle}}</h2><p>{{mapCopy.celebrateSub}}</p><div><button @click="$emit('openReport')">{{mapCopy.celebratePrimary}}</button><button @click="$emit('close')">{{mapCopy.celebrateSecondary}}</button></div></section></template>
