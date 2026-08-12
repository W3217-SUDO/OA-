<script setup lang="ts">
const parityRules = [
  "旧系统菜单、路由、字段与权限必须逐项对齐",
  "旧库当前只读，重构期间不会写入 8091 数据",
  "钉钉和智能体将作为扩展能力接入",
];
</script>

<template>
  <main class="parity-shell">
    <header class="parity-header">Sunhold Legacy Parity Rebuild</header>
    <section class="parity-panel">
      <h1>旧系统等价重建基线</h1>
      <ul>
        <li v-for="rule in parityRules" :key="rule">{{ rule }}</li>
      </ul>
    </section>
  </main>
</template>
