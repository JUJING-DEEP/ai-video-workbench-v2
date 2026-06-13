<template>
  <section class="shot-timeline" aria-label="镜头时间线">
    <button
      v-for="shot in shots"
      :key="shot.shot_id"
      class="shot-card"
      type="button"
      @click="$emit('select-shot', shot)"
    >
      <strong>#{{ String(shot.shot_id).padStart(3, '0') }}</strong>
      <span>{{ shot.mode }}</span>
      <span>{{ formatTime(shot.start_seconds) }} - {{ formatTime(shot.end_seconds) }}</span>
      <small>{{ shot.status }}</small>
    </button>
  </section>
</template>

<script setup>
defineProps({
  shots: { type: Array, required: true }
})

defineEmits(['select-shot'])

function formatTime(value) {
  const total = Math.round(value)
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}
</script>

<style scoped>
.shot-timeline {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}

.shot-card {
  display: grid;
  gap: 6px;
  min-height: 112px;
  padding: 12px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  background: #ffffff;
  color: #1f2933;
  text-align: left;
}

.shot-card strong {
  font-size: 16px;
}

.shot-card span,
.shot-card small {
  color: #475467;
}
</style>
