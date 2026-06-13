<template>
  <section class="validation-panel">
    <h2>校验结果</h2>
    <p v-if="report?.render_ready" class="validation-panel__ready">可以渲染</p>
    <p v-else class="validation-panel__blocked">暂不可渲染</p>

    <ul v-if="report?.issues?.length">
      <li v-for="issue in report.issues" :key="`${issue.code}-${issue.shot_id ?? 'project'}`">
        <strong>{{ issue.code }}</strong>
        <span>{{ issue.message }}</span>
      </li>
    </ul>
  </section>
</template>

<script setup>
defineProps({
  report: { type: Object, default: () => ({ render_ready: false, issues: [] }) }
})
</script>

<style scoped>
.validation-panel {
  padding: 16px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  background: #ffffff;
}

.validation-panel h2 {
  margin: 0 0 10px;
  font-size: 18px;
}

.validation-panel__ready {
  color: #067647;
  font-weight: 700;
}

.validation-panel__blocked {
  color: #b42318;
  font-weight: 700;
}

ul {
  display: grid;
  gap: 8px;
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}

li {
  display: grid;
  gap: 4px;
  padding: 10px;
  border-radius: 8px;
  background: #fff7ed;
}
</style>
