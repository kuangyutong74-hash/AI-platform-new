import { ref } from "vue";

export function useBookFlip(total = 9) {
  const currentSpread = ref(0);
  const fromSpread = ref(0);
  const targetSpread = ref(0);
  const direction = ref<"next" | "prev">("next");
  const flipping = ref(false);
  let timer: number | undefined;
  let settleTimer: number | undefined;

  function goTo(index: number) {
    const target = Math.max(0, Math.min(total - 1, index));
    if (flipping.value || target === currentSpread.value) return false;
    fromSpread.value = currentSpread.value;
    targetSpread.value = target;
    direction.value = target > currentSpread.value ? "next" : "prev";
    flipping.value = true;
    window.clearTimeout(timer);
    window.clearTimeout(settleTimer);
    timer = window.setTimeout(() => {
      currentSpread.value = target;
    }, 460);
    settleTimer = window.setTimeout(() => {
      flipping.value = false;
      fromSpread.value = target;
    }, 920);
    return true;
  }

  return { currentSpread, fromSpread, targetSpread, direction, flipping, goTo, next: () => goTo(currentSpread.value + 1), prev: () => goTo(currentSpread.value - 1) };
}
