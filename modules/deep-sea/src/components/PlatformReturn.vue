<template>
  <a class="platform-return" href="http://localhost:4173/?from=build">← 返回探索星球</a>
</template>

<style scoped>
.platform-return {
  position: fixed; top: 18px; left: 18px; z-index: 10000;
  padding: 10px 16px; border: 1px solid rgb(255 255 255 / 70%);
  border-radius: 999px; color: #164e63; background: rgb(255 255 255 / 88%);
  box-shadow: 0 8px 24px rgb(8 47 73 / 18%); backdrop-filter: blur(12px);
  font: 600 14px/1.2 system-ui, sans-serif; text-decoration: none;
  transition: transform 160ms ease, background 160ms ease;
}
.platform-return:hover { transform: translateY(-1px); background: #fff; }
</style>
