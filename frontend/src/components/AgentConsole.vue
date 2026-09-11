<script setup lang="ts">
import { onMounted, ref } from "vue";
import { getAgentCapabilities, runAgent } from "../services/agentApi";
import type { AgentCapability, AgentRun } from "../types/agent";

const capabilities = ref<AgentCapability[]>([]);
const selectedSkill = ref("");
const input = ref("请解释当前旧系统页面的业务入口");
const running = ref(false);
const error = ref("");
const lastRun = ref<AgentRun | null>(null);

onMounted(async () => {
  try {
    capabilities.value = await getAgentCapabilities();
    selectedSkill.value = capabilities.value[0]?.name ?? "";
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Agent 能力加载失败";
  }
});

async function submit() {
  if (!selectedSkill.value || !input.value.trim()) return;
  running.value = true;
  error.value = "";
  try {
    lastRun.value = await runAgent(selectedSkill.value, input.value.trim());
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Agent 执行失败";
  } finally {
    running.value = false;
  }
}
</script>

<template>
  <section class="agent-console">
    <div class="agent-console__intro">
      <span class="eyebrow">AGENT RUNTIME / LOCAL DEMO</span>
      <h2>智能体工作台</h2>
      <p>网页和 CLI 共用同一套只读 Agent API，后续可替换为真实运行时。</p>
    </div>
    <div class="agent-console__form">
      <label>能力<select v-model="selectedSkill"><option v-for="item in capabilities" :key="item.name" :value="item.name">{{ item.label }}</option></select></label>
      <label>任务输入<textarea v-model="input" rows="3" /></label>
      <button class="primary-button" :disabled="running || !selectedSkill" @click="submit">{{ running ? "执行中..." : "运行只读 Demo" }}</button>
    </div>
    <p v-if="error" class="agent-error">{{ error }}</p>
    <article v-if="lastRun" class="agent-result"><div><strong>{{ lastRun.status }}</strong><small>{{ lastRun.id }}</small></div><p>{{ lastRun.output }}</p></article>
    <div v-if="capabilities.length" class="agent-capabilities"><article v-for="item in capabilities" :key="item.name"><strong>{{ item.label }}</strong><small>{{ item.name }}</small><p>{{ item.description }}</p></article></div>
  </section>
</template>

