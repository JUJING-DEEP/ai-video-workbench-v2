<template>
  <section class="video-workbench__render-pipeline" aria-label="Render Pipeline">
    <div>
      <p class="video-workbench__eyebrow">Render Pipeline</p>
      <h3>Render Plan</h3>
    </div>
    <div class="video-workbench__render-actions">
      <button
        type="button"
        data-testid="generate-render-plan"
        :disabled="isGeneratingRenderPlan"
        @click="$emit('generate-render-plan')"
      >
        {{ isGeneratingRenderPlan ? 'Generating render plan...' : 'Generate Render Plan' }}
      </button>
      <button
        type="button"
        data-testid="export-render-plan"
        :disabled="isExportingRenderPlan"
        @click="$emit('export-render-plan')"
      >
        {{ isExportingRenderPlan ? 'Exporting...' : 'Export Render Plan' }}
      </button>
    </div>
    <p v-if="renderPlanMessage" class="video-workbench__upload-message">
      {{ renderPlanMessage }}
    </p>
    <table v-if="renderPlanItems.length" class="video-workbench__render-table">
      <thead>
        <tr>
          <th>Shot Order</th>
          <th>Video Path</th>
          <th>Duration</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in renderPlanItems" :key="item.shot_id">
          <td>#{{ item.order }}</td>
          <td>{{ item.video_path }}</td>
          <td>{{ item.duration_seconds }}s</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup>
defineProps({
  renderPlanItems: { type: Array, default: () => [] },
  renderPlanMessage: { type: String, default: '' },
  isGeneratingRenderPlan: { type: Boolean, default: false },
  isExportingRenderPlan: { type: Boolean, default: false }
})

defineEmits(['generate-render-plan', 'export-render-plan'])
</script>
