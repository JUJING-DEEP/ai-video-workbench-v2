<template>
  <section class="video-workbench__asset-library" aria-label="素材库">
    <div>
      <p class="video-workbench__eyebrow">Asset Library</p>
      <h2>素材库</h2>
    </div>

    <section class="video-workbench__asset-upload" aria-label="上传素材">
      <div class="video-workbench__field">
        <label for="asset-library-upload-type">素材类型</label>
        <select
          id="asset-library-upload-type"
          :value="uploadAssetType"
          @change="$emit('update:upload-asset-type', $event.target.value)"
        >
          <option value="image">image</option>
          <option value="keyframe">keyframe</option>
          <option value="video">video</option>
        </select>
      </div>
      <div class="video-workbench__field">
        <label for="asset-library-upload-file">本地文件</label>
        <input
          id="asset-library-upload-file"
          type="file"
          :accept="uploadAccept"
          @change="$emit('select-upload-file', $event)"
        >
      </div>
      <button
        type="button"
        data-testid="upload-library-asset"
        :disabled="!selectedUploadFile || isUploadingAsset"
        @click="$emit('upload-asset')"
      >
        {{ isUploadingAsset ? '上传中...' : 'Upload asset' }}
      </button>
    </section>

    <p v-if="uploadMessage" class="video-workbench__upload-message">{{ uploadMessage }}</p>

    <section class="video-workbench__ai-generator" aria-label="AI Image Generator">
      <div>
        <p class="video-workbench__eyebrow">AI Image Generator</p>
        <h3>Nano Banana image</h3>
      </div>
      <textarea
        id="nano-banana-prompt"
        :value="nanoBananaPrompt"
        aria-label="Nano Banana prompt"
        placeholder="Describe the image to generate..."
        @input="$emit('update:nano-banana-prompt', $event.target.value)"
      />
      <button
        type="button"
        data-testid="generate-nano-banana-image"
        :disabled="isGeneratingImage || !selectedProject"
        @click="$emit('generate-image')"
      >
        {{ isGeneratingImage ? 'Generating...' : 'Generate image' }}
      </button>
      <p v-if="generationMessage" class="video-workbench__upload-message">
        {{ generationMessage }}
      </p>
    </section>

    <section class="video-workbench__ai-generator" aria-label="AI Keyframe Generator">
      <div>
        <p class="video-workbench__eyebrow">AI Keyframe Generator</p>
        <h3>Shot keyframe</h3>
      </div>
      <p v-if="!selectedShot" class="video-workbench__muted">请先选择一个 Shot。</p>
      <textarea
        id="keyframe-prompt"
        :value="keyframePrompt"
        aria-label="Keyframe prompt"
        placeholder="Describe the keyframe to generate..."
        @input="$emit('update:keyframe-prompt', $event.target.value)"
      />
      <button
        type="button"
        data-testid="generate-keyframe"
        :disabled="isGeneratingKeyframe || !selectedProject || !selectedShot"
        @click="$emit('generate-keyframe')"
      >
        {{ isGeneratingKeyframe ? 'Generating keyframe...' : 'Generate Keyframe' }}
      </button>
      <p v-if="keyframeMessage" class="video-workbench__upload-message">
        {{ keyframeMessage }}
      </p>
    </section>

    <div class="video-workbench__asset-groups">
      <section
        v-for="group in assetLibraryGroups"
        :key="group.type"
        class="video-workbench__asset-group"
      >
        <h3>{{ group.title }}</h3>
        <p v-if="!group.assets.length" class="video-workbench__muted">暂无素材</p>
        <article v-for="asset in group.assets" :key="asset.id" class="video-workbench__library-asset">
          <div>
            <strong>{{ asset.name }}</strong>
            <span>{{ asset.asset_type }}</span>
          </div>
          <p>{{ asset.path }}</p>
          <small>source: {{ asset.source || 'manual' }}</small>
          <small v-if="asset.prompt">prompt: {{ asset.prompt }}</small>
          <small>{{ canPreviewAsset(asset) ? '可预览' : '不可预览' }}</small>
          <div class="video-workbench__asset-actions">
            <button
              type="button"
              :data-testid="`bind-library-asset-${asset.id}-image`"
              :disabled="!selectedShot || savingAssetType === 'image'"
              @click="$emit('bind-library-asset', asset, 'image')"
            >
              Bind as image
            </button>
            <button
              type="button"
              :data-testid="`bind-library-asset-${asset.id}-keyframe`"
              :disabled="!selectedShot || savingAssetType === 'keyframe'"
              @click="$emit('bind-library-asset', asset, 'keyframe')"
            >
              Bind as keyframe
            </button>
            <button
              type="button"
              :data-testid="`bind-library-asset-${asset.id}-video`"
              :disabled="!selectedShot || savingAssetType === 'video'"
              @click="$emit('bind-library-asset', asset, 'video')"
            >
              Bind as video
            </button>
          </div>
        </article>
      </section>
    </div>

    <RenderPipelinePanel
      :render-plan-items="renderPlanItems"
      :render-plan-message="renderPlanMessage"
      :is-generating-render-plan="isGeneratingRenderPlan"
      :is-exporting-render-plan="isExportingRenderPlan"
      @generate-render-plan="$emit('generate-render-plan')"
      @export-render-plan="$emit('export-render-plan')"
    />

    <TimelinePanel
      :timeline-shots="timelineShots"
      :timeline-message="timelineMessage"
      :is-saving-timeline="isSavingTimeline"
      @move-timeline-shot="(index, direction) => $emit('move-timeline-shot', index, direction)"
      @save-timeline="$emit('save-timeline')"
    />
  </section>
</template>

<script setup>
import RenderPipelinePanel from './RenderPipelinePanel.vue'
import TimelinePanel from './TimelinePanel.vue'

defineProps({
  selectedProject: { type: Object, required: true },
  selectedShot: { type: Object, default: null },
  uploadAssetType: { type: String, default: 'image' },
  uploadAccept: { type: String, default: 'image/*' },
  selectedUploadFile: { type: Object, default: null },
  isUploadingAsset: { type: Boolean, default: false },
  uploadMessage: { type: String, default: '' },
  nanoBananaPrompt: { type: String, default: '' },
  isGeneratingImage: { type: Boolean, default: false },
  generationMessage: { type: String, default: '' },
  keyframePrompt: { type: String, default: '' },
  isGeneratingKeyframe: { type: Boolean, default: false },
  keyframeMessage: { type: String, default: '' },
  assetLibraryGroups: { type: Array, default: () => [] },
  savingAssetType: { type: String, default: '' },
  renderPlanItems: { type: Array, default: () => [] },
  renderPlanMessage: { type: String, default: '' },
  isGeneratingRenderPlan: { type: Boolean, default: false },
  isExportingRenderPlan: { type: Boolean, default: false },
  timelineShots: { type: Array, default: () => [] },
  timelineMessage: { type: String, default: '' },
  isSavingTimeline: { type: Boolean, default: false },
  canPreviewAsset: { type: Function, required: true }
})

defineEmits([
  'update:upload-asset-type',
  'update:nano-banana-prompt',
  'update:keyframe-prompt',
  'select-upload-file',
  'upload-asset',
  'generate-image',
  'generate-keyframe',
  'bind-library-asset',
  'generate-render-plan',
  'export-render-plan',
  'move-timeline-shot',
  'save-timeline'
])
</script>
