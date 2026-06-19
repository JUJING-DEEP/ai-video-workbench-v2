<template>
  <section class="video-workbench__video-generator" aria-label="Video Generator">
    <h4>Video Generator</h4>
    <div class="video-workbench__field">
      <label for="video-provider">Provider</label>
      <select
        id="video-provider"
        :value="selectedVideoProvider"
        @change="$emit('update:selected-video-provider', $event.target.value)"
      >
        <option value="mock">Mock Provider</option>
        <option value="jimeng">Jimeng Provider</option>
      </select>
    </div>
    <p class="video-workbench__muted">Current Provider: {{ selectedVideoProviderLabel }}</p>
    <p class="video-workbench__muted">
      Current Keyframe: {{ selectedShot.keyframe_path || '未绑定' }}
    </p>
    <p v-if="!selectedShot.keyframe_path" class="video-workbench__muted">
      Please generate or bind a keyframe first.
    </p>
    <button
      type="button"
      data-testid="generate-video"
      :disabled="isGeneratingVideo || !selectedProject || !selectedShot.keyframe_path"
      @click="$emit('generate-video')"
    >
      {{ isGeneratingVideo ? 'Generating video...' : 'Generate Video' }}
    </button>
    <p v-if="videoMessage" class="video-workbench__upload-message">{{ videoMessage }}</p>
    <div v-if="assetPreviews.video" class="video-workbench__asset-preview">
      <video :src="assetPreviews.video.url" controls aria-label="视频预览" />
    </div>

    <section class="video-workbench__video-job" aria-label="Jimeng REST Job">
      <h5>Jimeng REST Job</h5>
      <p class="video-workbench__muted">
        Job status: {{ videoJob?.status || 'not submitted' }}
      </p>
      <div class="video-workbench__render-actions">
        <button
          type="button"
          data-testid="submit-video-job"
          :disabled="
            isSubmittingVideoJob ||
              !selectedProject ||
              !selectedShot ||
              !selectedShot.keyframe_path
          "
          @click="$emit('submit-video-job')"
        >
          {{ isSubmittingVideoJob ? 'Submitting Jimeng Job...' : 'Submit Jimeng Job' }}
        </button>
        <button
          type="button"
          data-testid="poll-video-job"
          :disabled="isPollingVideoJob || !videoJob"
          @click="$emit('poll-video-job')"
        >
          {{ isPollingVideoJob ? 'Polling Job...' : 'Poll Job' }}
        </button>
      </div>
      <p v-if="videoJobMessage" class="video-workbench__upload-message">
        {{ videoJobMessage }}
      </p>
      <div v-if="videoJob?.output_path" class="video-workbench__asset-preview">
        <video :src="videoJob.output_path" controls aria-label="Jimeng job video preview" />
      </div>
    </section>
  </section>
</template>

<script setup>
defineProps({
  selectedProject: { type: Object, default: null },
  selectedShot: { type: Object, required: true },
  selectedVideoProvider: { type: String, default: 'mock' },
  selectedVideoProviderLabel: { type: String, default: 'Mock Provider' },
  isGeneratingVideo: { type: Boolean, default: false },
  videoMessage: { type: String, default: '' },
  assetPreviews: { type: Object, required: true },
  videoJob: { type: Object, default: null },
  videoJobMessage: { type: String, default: '' },
  isSubmittingVideoJob: { type: Boolean, default: false },
  isPollingVideoJob: { type: Boolean, default: false }
})

defineEmits([
  'update:selected-video-provider',
  'generate-video',
  'submit-video-job',
  'poll-video-job'
])
</script>
