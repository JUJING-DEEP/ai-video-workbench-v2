<template>
  <main class="video-workbench">
    <aside class="video-workbench__sidebar">
      <p class="video-workbench__eyebrow">AI Video Workbench</p>
      <h1>短视频生产工作台</h1>
      <p>导入分镜、管理素材、校验对齐并导出成片。</p>
    </aside>

    <section class="video-workbench__main">
      <section class="video-workbench__project-bar" aria-label="项目管理">
        <div class="video-workbench__field">
          <label for="project-title">项目标题</label>
          <input
            id="project-title"
            v-model="projectTitle"
            type="text"
            placeholder="例如：Revenge Bedtime Procrastination"
          />
        </div>

        <button type="button" :disabled="isCreatingProject" @click="handleCreateProject">
          {{ isCreatingProject ? '创建中...' : '创建项目' }}
        </button>

        <div class="video-workbench__field">
          <label for="project-select">当前项目</label>
          <select id="project-select" v-model="selectedProjectId" @change="handleSelectProject">
            <option value="">未选择项目</option>
            <option v-for="project in projects" :key="project.id" :value="String(project.id)">
              {{ project.title }}
            </option>
          </select>
        </div>
      </section>

      <p v-if="selectedProject" class="video-workbench__project-status">
        当前项目：{{ selectedProject.title }} / {{ selectedProject.slug }}
      </p>

      <section class="video-workbench__provider-settings" aria-label="Provider Settings">
        <div>
          <p class="video-workbench__eyebrow">Provider Settings</p>
          <h2>Nano Banana</h2>
        </div>
        <div class="video-workbench__settings-grid">
          <div class="video-workbench__field">
            <label for="nano-banana-api-key">API Key</label>
            <input
              id="nano-banana-api-key"
              v-model="nanoBananaSettings.nano_banana_api_key"
              type="password"
              placeholder="Nano Banana API key"
            />
          </div>
          <div class="video-workbench__field">
            <label for="nano-banana-base-url">Base URL</label>
            <input
              id="nano-banana-base-url"
              v-model="nanoBananaSettings.nano_banana_base_url"
              type="text"
              placeholder="https://..."
            />
          </div>
          <button
            type="button"
            data-testid="save-nano-banana-settings"
            :disabled="isSavingProviderSettings"
            @click="handleSaveProviderSettings"
          >
            {{ isSavingProviderSettings ? '保存中...' : 'Save provider settings' }}
          </button>
        </div>
        <p v-if="providerMessage" class="video-workbench__upload-message">{{ providerMessage }}</p>
        <div class="video-workbench__settings-grid">
          <div class="video-workbench__field">
            <label for="jimeng-api-key">Jimeng API Key</label>
            <input
              id="jimeng-api-key"
              v-model="jimengSettings.api_key"
              type="password"
              placeholder="Jimeng API key"
            />
          </div>
          <div class="video-workbench__field">
            <label for="jimeng-base-url">Jimeng Base URL</label>
            <input
              id="jimeng-base-url"
              v-model="jimengSettings.base_url"
              type="text"
              placeholder="https://..."
            />
          </div>
          <label class="video-workbench__checkbox" for="jimeng-enabled">
            <input id="jimeng-enabled" v-model="jimengSettings.enabled" type="checkbox" />
            Enable Jimeng
          </label>
          <button
            type="button"
            data-testid="save-jimeng-settings"
            :disabled="isSavingJimengSettings"
            @click="handleSaveJimengSettings"
          >
            {{ isSavingJimengSettings ? '保存中...' : 'Save Jimeng settings' }}
          </button>
        </div>
        <p v-if="jimengProviderMessage" class="video-workbench__upload-message">
          {{ jimengProviderMessage }}
        </p>
      </section>

      <section v-if="selectedProject" class="video-workbench__asset-library" aria-label="素材库">
        <div>
          <p class="video-workbench__eyebrow">Asset Library</p>
          <h2>素材库</h2>
        </div>

        <section class="video-workbench__asset-upload" aria-label="上传素材">
          <div class="video-workbench__field">
            <label for="asset-library-upload-type">素材类型</label>
            <select id="asset-library-upload-type" v-model="uploadAssetType">
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
              @change="handleSelectUploadFile"
            />
          </div>
          <button
            type="button"
            data-testid="upload-library-asset"
            :disabled="!selectedUploadFile || isUploadingAsset"
            @click="handleUploadAsset"
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
            v-model="nanoBananaPrompt"
            aria-label="Nano Banana prompt"
            placeholder="Describe the image to generate..."
          ></textarea>
          <button
            type="button"
            data-testid="generate-nano-banana-image"
            :disabled="isGeneratingImage || !selectedProject"
            @click="handleGenerateImage"
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
            v-model="keyframePrompt"
            aria-label="Keyframe prompt"
            placeholder="Describe the keyframe to generate..."
          ></textarea>
          <button
            type="button"
            data-testid="generate-keyframe"
            :disabled="isGeneratingKeyframe || !selectedProject || !selectedShot"
            @click="handleGenerateKeyframe"
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
            <article
              v-for="asset in group.assets"
              :key="asset.id"
              class="video-workbench__library-asset"
            >
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
                  @click="handleBindLibraryAsset(asset, 'image')"
                >
                  Bind as image
                </button>
                <button
                  type="button"
                  :data-testid="`bind-library-asset-${asset.id}-keyframe`"
                  :disabled="!selectedShot || savingAssetType === 'keyframe'"
                  @click="handleBindLibraryAsset(asset, 'keyframe')"
                >
                  Bind as keyframe
                </button>
                <button
                  type="button"
                  :data-testid="`bind-library-asset-${asset.id}-video`"
                  :disabled="!selectedShot || savingAssetType === 'video'"
                  @click="handleBindLibraryAsset(asset, 'video')"
                >
                  Bind as video
                </button>
              </div>
            </article>
          </section>
        </div>

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
              @click="handleGenerateRenderPlan"
            >
              {{ isGeneratingRenderPlan ? 'Generating render plan...' : 'Generate Render Plan' }}
            </button>
            <button
              type="button"
              data-testid="export-render-plan"
              :disabled="isExportingRenderPlan"
              @click="handleExportRenderPlan"
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
                <td>{{ videoStatus(shot) }}</td>
                <td>{{ shot.duration_seconds }}s</td>
                <td class="video-workbench__timeline-actions">
                  <button
                    type="button"
                    :data-testid="`move-shot-${shot.shot_id}-up`"
                    :disabled="index === 0"
                    @click="moveTimelineShot(index, -1)"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    :data-testid="`move-shot-${shot.shot_id}-down`"
                    :disabled="index === timelineShots.length - 1"
                    @click="moveTimelineShot(index, 1)"
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
            @click="handleSaveTimeline"
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
      </section>

      <header class="video-workbench__header">
        <div>
          <p class="video-workbench__eyebrow">Storyboard Import</p>
          <h2>分镜导入</h2>
        </div>
        <button type="button" :disabled="isParsing" @click="handleParse">
          {{ parseButtonLabel }}
        </button>
      </header>

      <textarea
        v-model="storyboardText"
        aria-label="粘贴 Google AI Studio 分镜文本"
        placeholder="粘贴 Google AI Studio 分镜文本..."
      ></textarea>

      <p v-if="error" class="video-workbench__error">{{ error }}</p>

      <div v-if="shots.length" class="video-workbench__workspace">
        <section class="video-workbench__timeline-panel">
          <h3>镜头时间线</h3>
          <ShotTimeline :shots="shots" @select-shot="handleSelectShot" />
        </section>

        <aside v-if="selectedShot" class="video-workbench__detail">
          <h3>#{{ String(selectedShot.shot_id).padStart(3, '0') }}</h3>
          <p>{{ selectedShot.dialogue_zh || '无中文台词' }}</p>
          <pre>{{ selectedShot.image_prompt || selectedShot.i2v_prompt }}</pre>

          <section class="video-workbench__asset-form" aria-label="素材路径绑定">
            <h4>素材路径</h4>
            <div v-for="asset in assetFields" :key="asset.type" class="video-workbench__asset-row">
              <label :for="`asset-${asset.type}`">
                <span>{{ asset.label }} {{ assetStatus(asset.type) }}</span>
              </label>
              <input
                :id="`asset-${asset.type}`"
                v-model="assetPaths[asset.type]"
                type="text"
                :placeholder="asset.placeholder"
              />
              <input
                :id="`asset-${asset.type}-file`"
                type="file"
                :accept="asset.accept"
                @change="handleSelectAssetFile(asset.type, $event)"
              />
              <div v-if="assetPreviews[asset.type]" class="video-workbench__asset-preview">
                <img
                  v-if="assetPreviews[asset.type].kind === 'image'"
                  :src="assetPreviews[asset.type].url"
                  :alt="`${asset.label}预览`"
                />
                <video
                  v-else
                  :src="assetPreviews[asset.type].url"
                  controls
                  :aria-label="`${asset.label}预览`"
                />
              </div>
              <button
                type="button"
                :disabled="!selectedProject || savingAssetType === asset.type"
                @click="handleBindAsset(asset.type)"
              >
                {{ savingAssetType === asset.type ? '保存中...' : '保存' }}
              </button>
            </div>
          </section>

          <section class="video-workbench__video-generator" aria-label="Video Generator">
            <h4>Video Generator</h4>
            <div class="video-workbench__field">
              <label for="video-provider">Provider</label>
              <select id="video-provider" v-model="selectedVideoProvider">
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
              @click="handleGenerateVideo"
            >
              {{ isGeneratingVideo ? 'Generating video...' : 'Generate Video' }}
            </button>
            <p v-if="videoMessage" class="video-workbench__upload-message">{{ videoMessage }}</p>
            <div v-if="assetPreviews.video" class="video-workbench__asset-preview">
              <video :src="assetPreviews.video.url" controls aria-label="视频预览" />
            </div>
          </section>
        </aside>

        <ValidationPanel :report="validationReport" />
      </div>

      <section v-if="parsedJson" class="video-workbench__preview" aria-label="解析结果 JSON 预览">
        <h3>解析结果</h3>
        <pre>{{ parsedJson }}</pre>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import ShotTimeline from '../components/video-workbench/ShotTimeline.vue'
import ValidationPanel from '../components/video-workbench/ValidationPanel.vue'
import {
  bindShotAsset,
  createProjectAsset,
  createProject,
  exportRenderPlan,
  generateKeyframe,
  generateProjectImage,
  generateRenderPlan,
  generateVideo,
  getJimengSettings,
  getNanoBananaProviderSettings,
  getProjectShots,
  getRenderPlan,
  getTimeline,
  importStoryboard,
  listProjectAssets,
  listProjects,
  parseStoryboard,
  reorderShots,
  saveJimengSettings,
  saveNanoBananaProviderSettings,
  uploadProjectAsset
} from '../services/videoWorkbenchApi'

const projectTitle = ref('')
const projects = ref([])
const selectedProjectId = ref('')
const storyboardText = ref('')
const parsed = ref(null)
const shots = ref([])
const projectAssets = ref([])
const selectedShot = ref(null)
const validationReport = ref({ render_ready: false, issues: [] })
const error = ref('')
const assetPaths = ref({ image: '', keyframe: '', video: '' })
const assetPreviews = ref({ image: null, keyframe: null, video: null })
const isCreatingProject = ref(false)
const isParsing = ref(false)
const savingAssetType = ref('')
const uploadAssetType = ref('image')
const selectedUploadFile = ref(null)
const isUploadingAsset = ref(false)
const uploadMessage = ref('')
const nanoBananaSettings = ref({ nano_banana_api_key: '', nano_banana_base_url: '' })
const jimengSettings = ref({ api_key: '', base_url: '', enabled: true })
const providerMessage = ref('')
const jimengProviderMessage = ref('')
const isSavingProviderSettings = ref(false)
const isSavingJimengSettings = ref(false)
const nanoBananaPrompt = ref('')
const isGeneratingImage = ref(false)
const generationMessage = ref('')
const keyframePrompt = ref('')
const isGeneratingKeyframe = ref(false)
const keyframeMessage = ref('')
const isGeneratingVideo = ref(false)
const videoMessage = ref('')
const selectedVideoProvider = ref('mock')
const renderPlan = ref(null)
const renderPlanMessage = ref('')
const isGeneratingRenderPlan = ref(false)
const isExportingRenderPlan = ref(false)
const timeline = ref({ project_id: null, shots: [] })
const timelineMessage = ref('')
const isSavingTimeline = ref(false)

const assetFields = [
  { type: 'image', label: '图片', placeholder: '/path/to/shot-001.png', accept: 'image/*' },
  {
    type: 'keyframe',
    label: '关键帧',
    placeholder: '/path/to/shot-001-keyframe.png',
    accept: 'image/*'
  },
  { type: 'video', label: '视频', placeholder: '/path/to/shot-001.mp4', accept: 'video/*' }
]

const selectedProject = computed(() => {
  return projects.value.find((project) => String(project.id) === selectedProjectId.value) || null
})

const parseButtonLabel = computed(() => {
  if (isParsing.value) {
    return selectedProject.value ? '保存中...' : '解析中...'
  }
  return selectedProject.value ? '保存分镜到项目' : '解析分镜'
})

const parsedJson = computed(() => {
  if (!parsed.value) {
    return ''
  }
  return JSON.stringify(parsed.value, null, 2)
})

const assetLibraryGroups = computed(() => [
  {
    type: 'image',
    title: 'Image assets',
    assets: projectAssets.value.filter((asset) => asset.asset_type === 'image')
  },
  {
    type: 'keyframe',
    title: 'Keyframe assets',
    assets: projectAssets.value.filter((asset) => asset.asset_type === 'keyframe')
  },
  {
    type: 'video',
    title: 'Video assets',
    assets: projectAssets.value.filter((asset) => asset.asset_type === 'video')
  }
])

const uploadAccept = computed(() => {
  return uploadAssetType.value === 'video' ? 'video/*' : 'image/*'
})

const renderPlanItems = computed(() => renderPlan.value?.items || [])
const timelineShots = computed(() => timeline.value?.shots || [])
const selectedVideoProviderLabel = computed(() =>
  selectedVideoProvider.value === 'jimeng' ? 'Jimeng Provider' : 'Mock Provider'
)

onMounted(() => {
  refreshProjects()
  loadProviderSettings()
})

async function refreshProjects() {
  try {
    const payload = await listProjects()
    projects.value = payload.projects || []
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载项目列表失败'
  }
}

async function loadProviderSettings() {
  try {
    const [payload, jimengPayload] = await Promise.all([
      getNanoBananaProviderSettings(),
      getJimengSettings()
    ])
    nanoBananaSettings.value = {
      nano_banana_api_key: payload.settings?.nano_banana_api_key || '',
      nano_banana_base_url: payload.settings?.nano_banana_base_url || ''
    }
    jimengSettings.value = {
      api_key: jimengPayload.settings?.api_key || '',
      base_url: jimengPayload.settings?.base_url || '',
      enabled: jimengPayload.settings?.enabled !== false
    }
  } catch (err) {
    providerMessage.value = err instanceof Error ? err.message : '加载 Provider Settings 失败'
  }
}

async function handleSaveJimengSettings() {
  jimengProviderMessage.value = ''
  isSavingJimengSettings.value = true

  try {
    await saveJimengSettings({
      api_key: jimengSettings.value.api_key.trim(),
      base_url: jimengSettings.value.base_url.trim(),
      enabled: jimengSettings.value.enabled
    })
    jimengProviderMessage.value = 'Jimeng settings saved.'
  } catch (err) {
    jimengProviderMessage.value = err instanceof Error ? err.message : '保存 Jimeng Settings 失败'
  } finally {
    isSavingJimengSettings.value = false
  }
}

async function handleSaveProviderSettings() {
  providerMessage.value = ''
  isSavingProviderSettings.value = true

  try {
    await saveNanoBananaProviderSettings({
      nano_banana_api_key: nanoBananaSettings.value.nano_banana_api_key.trim(),
      nano_banana_base_url: nanoBananaSettings.value.nano_banana_base_url.trim()
    })
    providerMessage.value = 'Provider settings saved.'
  } catch (err) {
    providerMessage.value = err instanceof Error ? err.message : '保存 Provider Settings 失败'
  } finally {
    isSavingProviderSettings.value = false
  }
}

async function handleCreateProject() {
  const title = projectTitle.value.trim()
  error.value = ''

  if (!title) {
    error.value = '请先输入项目标题。'
    return
  }

  isCreatingProject.value = true

  try {
    const payload = await createProject({
      title,
      role_card: '',
      audio_path: '',
      audio_duration_seconds: null
    })
    const project = payload.project
    await refreshProjects()
    selectedProjectId.value = String(project.id)
    projectTitle.value = ''
    await loadProjectShots(project.id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '创建项目失败'
  } finally {
    isCreatingProject.value = false
  }
}

async function handleSelectProject() {
  error.value = ''

  if (!selectedProjectId.value) {
    parsed.value = null
    shots.value = []
    projectAssets.value = []
    renderPlan.value = null
    timeline.value = { project_id: null, shots: [] }
    selectedShot.value = null
    validationReport.value = { render_ready: false, issues: [] }
    return
  }

  await loadProjectShots(Number(selectedProjectId.value))
}

async function loadProjectShots(projectId) {
  try {
    const [payload, assetPayload, renderPayload, timelinePayload] = await Promise.all([
      getProjectShots(projectId),
      listProjectAssets(projectId),
      getRenderPlan(projectId),
      getTimeline(projectId)
    ])
    parsed.value = { project: selectedProject.value, shots: payload.shots || [] }
    shots.value = payload.shots || []
    projectAssets.value = assetPayload.assets || []
    renderPlan.value = renderPayload
    timeline.value = timelinePayload
    selectedShot.value = findUpdatedSelectedShot(shots.value)
    syncAssetPaths()
    validationReport.value = buildValidationReport(shots.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载项目镜头失败'
  }
}

async function handleParse() {
  const trimmedText = storyboardText.value.trim()

  error.value = ''
  parsed.value = null
  shots.value = []
  selectedShot.value = null
  validationReport.value = { render_ready: false, issues: [] }

  if (!trimmedText) {
    error.value = '请先粘贴 Google AI Studio 分镜文本。'
    return
  }

  isParsing.value = true

  try {
    parsed.value = selectedProject.value
      ? await importStoryboard(selectedProject.value.id, trimmedText)
      : await parseStoryboard(trimmedText)
    shots.value = parsed.value.shots || []
    selectedShot.value = shots.value[0] || null
    syncAssetPaths()
    validationReport.value = buildValidationReport(shots.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '解析分镜失败'
  } finally {
    isParsing.value = false
  }
}

function handleSelectShot(shot) {
  selectedShot.value = shot
  syncAssetPaths()
}

function handleSelectAssetFile(assetType, event) {
  const file = event.target.files?.[0]
  if (!file) {
    return
  }

  const previousPreview = assetPreviews.value[assetType]
  if (previousPreview) {
    URL.revokeObjectURL(previousPreview.url)
  }

  assetPaths.value[assetType] = file.name
  assetPreviews.value[assetType] = {
    url: URL.createObjectURL(file),
    kind: file.type.startsWith('video/') ? 'video' : 'image'
  }
}

async function handleBindAsset(assetType) {
  error.value = ''

  if (!selectedProject.value || !selectedShot.value) {
    error.value = '请先选择项目和镜头。'
    return
  }

  const path = assetPaths.value[assetType].trim()
  if (!path) {
    error.value = '请先输入素材路径。'
    return
  }

  savingAssetType.value = assetType

  try {
    await bindShotAsset(selectedProject.value.id, selectedShot.value.shot_id, assetType, path)
    await loadProjectShots(selectedProject.value.id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '保存素材路径失败'
  } finally {
    savingAssetType.value = ''
  }
}

async function handleBindLibraryAsset(asset, assetType) {
  error.value = ''

  if (!selectedProject.value || !selectedShot.value) {
    error.value = '请先选择项目和镜头。'
    return
  }

  savingAssetType.value = assetType

  try {
    await bindShotAsset(selectedProject.value.id, selectedShot.value.shot_id, assetType, asset.path)
    await loadProjectShots(selectedProject.value.id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '绑定素材失败'
  } finally {
    savingAssetType.value = ''
  }
}

function handleSelectUploadFile(event) {
  selectedUploadFile.value = event.target.files?.[0] || null
}

async function handleUploadAsset() {
  error.value = ''
  uploadMessage.value = ''

  if (!selectedProject.value || !selectedUploadFile.value) {
    uploadMessage.value = '请先选择项目和素材文件。'
    return
  }

  isUploadingAsset.value = true

  try {
    const uploaded = await uploadProjectAsset(
      selectedProject.value.id,
      uploadAssetType.value,
      selectedUploadFile.value
    )
    await createProjectAsset(selectedProject.value.id, {
      asset_type: uploaded.asset_type,
      name: uploaded.name,
      path: uploaded.path
    })
    const assetPayload = await listProjectAssets(selectedProject.value.id)
    projectAssets.value = assetPayload.assets || []
    uploadMessage.value = '素材上传成功。'
  } catch (err) {
    uploadMessage.value = err instanceof Error ? err.message : '素材上传失败'
  } finally {
    isUploadingAsset.value = false
  }
}

async function handleGenerateImage() {
  generationMessage.value = ''

  if (!selectedProject.value) {
    generationMessage.value = '请先选择项目。'
    return
  }

  const prompt = nanoBananaPrompt.value.trim()
  if (!prompt) {
    generationMessage.value = '请输入生成提示词。'
    return
  }

  isGeneratingImage.value = true

  try {
    await generateProjectImage(selectedProject.value.id, prompt)
    const assetPayload = await listProjectAssets(selectedProject.value.id)
    projectAssets.value = assetPayload.assets || []
    generationMessage.value = 'Image generated.'
  } catch (err) {
    generationMessage.value = err instanceof Error ? err.message : '图片生成失败'
  } finally {
    isGeneratingImage.value = false
  }
}

async function handleGenerateKeyframe() {
  keyframeMessage.value = ''

  if (!selectedProject.value || !selectedShot.value) {
    keyframeMessage.value = '请先选择一个 Shot。'
    return
  }

  const prompt = keyframePrompt.value.trim()
  if (!prompt) {
    keyframeMessage.value = '请输入关键帧提示词。'
    return
  }

  isGeneratingKeyframe.value = true

  try {
    const result = await generateKeyframe(selectedProject.value.id, selectedShot.value.shot_id, prompt)
    await loadProjectShots(selectedProject.value.id)
    assetPreviews.value.keyframe = {
      url: result.path,
      kind: 'image'
    }
    keyframeMessage.value = 'Keyframe generated.'
  } catch (err) {
    keyframeMessage.value = err instanceof Error ? err.message : '关键帧生成失败'
  } finally {
    isGeneratingKeyframe.value = false
  }
}

async function handleGenerateVideo() {
  videoMessage.value = ''

  if (!selectedProject.value || !selectedShot.value) {
    videoMessage.value = '请先选择项目和镜头。'
    return
  }

  if (!selectedShot.value.keyframe_path) {
    videoMessage.value = 'Please generate or bind a keyframe first.'
    return
  }

  isGeneratingVideo.value = true

  try {
    const result = await generateVideo(
      selectedProject.value.id,
      selectedShot.value.shot_id,
      selectedVideoProvider.value
    )
    await loadProjectShots(selectedProject.value.id)
    assetPreviews.value.video = {
      url: result.video_path,
      kind: 'video'
    }
    videoMessage.value = 'Video generated.'
  } catch (err) {
    videoMessage.value = err instanceof Error ? err.message : '视频生成失败'
  } finally {
    isGeneratingVideo.value = false
  }
}

async function handleGenerateRenderPlan() {
  renderPlanMessage.value = ''

  if (!selectedProject.value) {
    renderPlanMessage.value = '请先选择项目。'
    return
  }

  isGeneratingRenderPlan.value = true

  try {
    renderPlan.value = await generateRenderPlan(selectedProject.value.id)
  } catch (err) {
    renderPlanMessage.value = err instanceof Error ? err.message : '生成 Render Plan 失败'
  } finally {
    isGeneratingRenderPlan.value = false
  }
}

async function handleExportRenderPlan() {
  renderPlanMessage.value = ''

  if (!selectedProject.value) {
    renderPlanMessage.value = '请先选择项目。'
    return
  }

  isExportingRenderPlan.value = true

  try {
    const exported = await exportRenderPlan(selectedProject.value.id)
    renderPlanMessage.value = `Render plan exported. ${exported.path}`
  } catch (err) {
    renderPlanMessage.value = err instanceof Error ? err.message : '导出 Render Plan 失败'
  } finally {
    isExportingRenderPlan.value = false
  }
}

function moveTimelineShot(index, direction) {
  const nextIndex = index + direction
  const currentShots = [...timelineShots.value]

  if (nextIndex < 0 || nextIndex >= currentShots.length) {
    return
  }

  const shot = currentShots[index]
  currentShots[index] = currentShots[nextIndex]
  currentShots[nextIndex] = shot
  timeline.value = {
    ...timeline.value,
    shots: currentShots.map((currentShot, currentIndex) => ({
      ...currentShot,
      order: currentIndex + 1
    }))
  }
}

async function handleSaveTimeline() {
  timelineMessage.value = ''

  if (!selectedProject.value) {
    timelineMessage.value = '请先选择项目。'
    return
  }

  isSavingTimeline.value = true

  try {
    const shotIds = timelineShots.value.map((shot) => shot.shot_id)
    await reorderShots(selectedProject.value.id, shotIds)
    await loadProjectShots(selectedProject.value.id)
    timelineMessage.value = 'Timeline saved.'
  } catch (err) {
    timelineMessage.value = err instanceof Error ? err.message : '保存 Timeline 失败'
  } finally {
    isSavingTimeline.value = false
  }
}

function findUpdatedSelectedShot(currentShots) {
  if (!selectedShot.value) {
    return currentShots[0] || null
  }
  return (
    currentShots.find((shot) => shot.shot_id === selectedShot.value.shot_id) ||
    currentShots[0] ||
    null
  )
}

function syncAssetPaths() {
  assetPaths.value = {
    image: selectedShot.value?.image_path || '',
    keyframe: selectedShot.value?.keyframe_path || '',
    video: selectedShot.value?.video_path || ''
  }
  assetPreviews.value = {
    image: selectedShot.value?.image_path
      ? { url: selectedShot.value.image_path, kind: 'image' }
      : null,
    keyframe: selectedShot.value?.keyframe_path
      ? { url: selectedShot.value.keyframe_path, kind: 'image' }
      : null,
    video: selectedShot.value?.video_path ? { url: selectedShot.value.video_path, kind: 'video' } : null
  }
}

function assetStatus(assetType) {
  return assetPaths.value[assetType] ? '已绑定' : '未绑定'
}

function canPreviewAsset(asset) {
  return ['image', 'keyframe', 'video'].includes(asset.asset_type)
}

function videoStatus(shot) {
  return shot.video_path ? 'Video ready' : 'Video missing'
}

function buildValidationReport(currentShots) {
  const missingAssets = currentShots.filter((shot) => {
    if (shot.kind === 'key_node_video') {
      return !shot.video_path
    }
    return !shot.image_path
  })

  return {
    render_ready: currentShots.length > 0 && missingAssets.length === 0,
    issues: currentShots.length
      ? missingAssets.map((shot) => ({
          code: 'asset_missing',
          message: `#${String(shot.shot_id).padStart(3, '0')} 缺少${
            shot.kind === 'key_node_video' ? '视频' : '图片'
          }素材路径。`
        }))
      : [{ code: 'no_shots', message: '没有解析到镜头，请检查分镜文本格式。' }]
  }
}
</script>

<style scoped>
.video-workbench {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  background: #f6f7f9;
  color: #1f2933;
}

.video-workbench__sidebar {
  padding: 32px 24px;
  background: #111827;
  color: #f9fafb;
}

.video-workbench__sidebar h1,
.video-workbench__main h2,
.video-workbench__preview h3 {
  margin: 0;
}

.video-workbench__sidebar h1 {
  margin-top: 8px;
  font-size: 28px;
  line-height: 1.2;
}

.video-workbench__sidebar p:last-child {
  margin-top: 16px;
  color: #cbd5e1;
  line-height: 1.7;
}

.video-workbench__eyebrow {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.video-workbench__sidebar .video-workbench__eyebrow {
  color: #93c5fd;
}

.video-workbench__main {
  min-width: 0;
  padding: 32px;
}

.video-workbench__project-bar {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto minmax(180px, 260px);
  gap: 12px;
  align-items: end;
  margin-bottom: 24px;
}

.video-workbench__field {
  display: grid;
  gap: 6px;
}

.video-workbench__field label {
  font-size: 13px;
  font-weight: 700;
  color: #475467;
}

.video-workbench__field input,
.video-workbench__field select {
  min-height: 42px;
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #111827;
  padding: 0 12px;
  font: inherit;
}

.video-workbench__project-status {
  margin: 0 0 18px;
  color: #475467;
  font-weight: 700;
}

.video-workbench__asset-library {
  margin-bottom: 24px;
  padding: 20px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  background: #ffffff;
}

.video-workbench__asset-library h2,
.video-workbench__asset-library h3 {
  margin: 0;
}

.video-workbench__provider-settings {
  margin-bottom: 24px;
  padding: 20px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  background: #ffffff;
}

.video-workbench__provider-settings h2 {
  margin: 0;
}

.video-workbench__settings-grid {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) minmax(220px, 1.5fr) auto;
  gap: 12px;
  align-items: end;
  margin-top: 16px;
}

.video-workbench__asset-upload {
  display: grid;
  grid-template-columns: minmax(140px, 180px) minmax(180px, 1fr) auto;
  gap: 12px;
  align-items: end;
  margin-top: 16px;
}

.video-workbench__upload-message {
  margin: 12px 0 0;
  color: #047857;
  font-weight: 700;
}

.video-workbench__ai-generator {
  display: grid;
  gap: 12px;
  margin-top: 18px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.video-workbench__ai-generator textarea {
  min-height: 120px;
  margin: 0;
}

.video-workbench__asset-groups {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.video-workbench__asset-group {
  display: grid;
  gap: 10px;
  align-content: start;
}

.video-workbench__library-asset {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.video-workbench__library-asset div:first-child {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.video-workbench__library-asset p {
  margin: 0;
  overflow-wrap: anywhere;
  color: #475467;
  font-size: 13px;
}

.video-workbench__library-asset span,
.video-workbench__library-asset small,
.video-workbench__muted {
  color: #64748b;
  font-size: 12px;
}

.video-workbench__asset-actions {
  display: grid;
  gap: 6px;
}

.video-workbench__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.video-workbench__header h2 {
  margin-top: 4px;
  font-size: 24px;
}

textarea {
  width: 100%;
  min-height: 260px;
  margin: 20px 0 12px;
  padding: 14px;
  resize: vertical;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #111827;
  font: inherit;
  line-height: 1.6;
}

button {
  min-height: 42px;
  padding: 0 16px;
  border: 0;
  border-radius: 8px;
  background: #2563eb;
  color: #ffffff;
  font-weight: 700;
}

.video-workbench__error {
  margin: 0 0 12px;
  color: #b42318;
  font-weight: 700;
}

.video-workbench__workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
  margin-top: 20px;
}

.video-workbench__timeline-panel,
.video-workbench__detail {
  min-width: 0;
}

.video-workbench__timeline-panel h3,
.video-workbench__detail h3 {
  margin: 0 0 12px;
  font-size: 18px;
}

.video-workbench__detail {
  padding: 16px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  background: #ffffff;
}

.video-workbench__detail p {
  margin: 0 0 12px;
  line-height: 1.6;
}

.video-workbench__asset-form {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.video-workbench__asset-form h4 {
  margin: 0;
  font-size: 16px;
}

.video-workbench__asset-row {
  display: grid;
  gap: 6px;
}

.video-workbench__asset-row label {
  font-size: 13px;
  font-weight: 700;
  color: #475467;
}

.video-workbench__asset-row input {
  min-height: 38px;
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #111827;
  padding: 0 10px;
  font: inherit;
}

.video-workbench__asset-preview {
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.video-workbench__asset-preview img,
.video-workbench__asset-preview video {
  display: block;
  width: 100%;
  max-height: 180px;
  object-fit: contain;
}

.video-workbench__preview {
  margin-top: 16px;
}

.video-workbench__preview h3 {
  font-size: 18px;
}

pre {
  max-height: 420px;
  margin-top: 12px;
  overflow: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
  padding: 16px;
  color: #0f172a;
  white-space: pre-wrap;
}

@media (max-width: 760px) {
  .video-workbench {
    grid-template-columns: 1fr;
  }

  .video-workbench__sidebar,
  .video-workbench__main {
    padding: 24px 18px;
  }

  .video-workbench__header {
    align-items: stretch;
    flex-direction: column;
  }

  .video-workbench__project-bar {
    grid-template-columns: 1fr;
  }

  .video-workbench__workspace {
    grid-template-columns: 1fr;
  }

  button {
    width: 100%;
  }
}
</style>
