<script setup lang="ts">
defineProps<{direction:"next"|"prev"}>();
</script>

<template>
  <div class="turning-leaf turning-leaf--real" :class="`turning-leaf--${direction}`" aria-hidden="true" inert>
    <span class="spine-cast-shadow"/>
    <span class="page-floor-shadow"/>
    <div class="turn-page">
      <div class="turn-face turn-face--front"><div class="flip-sheet-scroll"><slot name="front"/></div></div>
      <div class="turn-face turn-face--back"><div class="flip-sheet-scroll"><slot name="back"/></div></div>
      <span class="turn-page-light"/>
      <span class="turn-page-shade"/>
      <span class="turn-page-edge"/>
    </div>
  </div>
</template>
