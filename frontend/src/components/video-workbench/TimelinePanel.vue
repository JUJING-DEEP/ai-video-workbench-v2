<template>
  <section class="video-workbench__render-pipeline" aria-label="Timeline Editor">
    <div>
      <p class="video-workbench__eyebrow">Timeline Editor</p>
      <h3>Timeline</h3>
    </div>
    <table v-if="timelineShots.length" class="video-workbench__render-table">
      <thead>
        <tr>
          <th>Order</th>
          <th>Title</th>
          <th>Video Status</th>
          <th>Duration</th>
          <th>Move</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(shot, index) in timelineShots" :key="shot.shot_id">
          <td>#{{ shot.order }}</td>
          <td>{{ shot.title }}</td>
          <td>{{ shot.video_path ? 'Video ready' : 'Video missing' }}</td>
          <td>{{ shot.duration_seconds }}s</td>
          <td class="video-workbench__timeline-actions">
            <button
              type="button"
              :data-testid="`move-shot-${shot.shot_id}-up`"
              :disabled="index === 0"
              @click="$emit('move-timeline-shot', index, -1)"
            >
              ↑
            </button>
            <button
              type="button"
              :data-testid="`move-shot-${shot.shot_id}-down`"
              :disabled="index === timelineShots.length - 1"
              @click="$emit('move-timeline-shot', index, 1)"
            >
              ↓
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="video-workbench__muted">暂无 Timeline。</p>
    <button
      type="button"
      data-testid="save-timeline"
      :disabled="isSavingTimeline || !timelineShots.length"
      @click="$emit('save-timeline')"
    >
      {{ isSavingTimeline ? 'Saving timeline...' : 'Save Timeline' }}
    </button>
    <p v-if="timelineMessage" class="video-workbench__upload-message">
      {{ timelineMessage }}
    </p>
    <div v-if="timelineShots.length" class="video-workbench__timeline-preview">
      <h4>Timeline Preview</h4>
      <ol data-testid="timeline-preview">
        <li v-for="(shot, index) in timelineShots" :key="`preview-${shot.shot_id}`">
          {{ index + 1 }}. {{ shot.title }}
        </li>
      </ol>
    </div>
  </section>
</template>

<script setup>
defineProps({
  timelineShots: { type: Array, default: () => [] },
  timelineMessage: { type: String, default: '' },
  isSavingTimeline: { type: Boolean, default: false }
})

defineEmits(['move-timeline-shot', 'save-timeline'])
</script>
