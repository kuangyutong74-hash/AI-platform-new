<script setup lang="ts">
import MagicBook from "./MagicBook.vue";
import type { Talent } from "../data/mockReport";
defineProps<{talents:Talent[]}>();
defineEmits<{back:[];childView:[]}>();
</script>
<template><MagicBook :talents="talents" @back="$emit('back')" @child-view="$emit('childView')"/></template>
