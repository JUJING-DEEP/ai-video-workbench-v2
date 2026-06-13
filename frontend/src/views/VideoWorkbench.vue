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
              <label :for="`asset-${asset.type}`">{{ asset.label }}</label>
              <input
                :id="`asset-${asset.type}`"
                v-model="assetPaths[asset.type]"
                type="text"
                :placeholder="asset.placeholder"
              />
              <button
                type="button"
                :disabled="!selectedProject || savingAssetType === asset.type"
                @click="handleBindAsset(asset.type)"
              >
                {{ savingAssetType === asset.type ? '保存中...' : '保存' }}
              </button>
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
  createProject,
  getProjectShots,
  importStoryboard,
  listProjects,
  parseStoryboard
} from '../services/videoWorkbenchApi'

const projectTitle = ref('')
const projects = ref([])
const selectedProjectId = ref('')
const storyboardText = ref('')
const parsed = ref(null)
const shots = ref([])
const selectedShot = ref(null)
const validationReport = ref({ render_ready: false, issues: [] })
const error = ref('')
const assetPaths = ref({ image: '', keyframe: '', video: '' })
const isCreatingProject = ref(false)
const isParsing = ref(false)
const savingAssetType = ref('')

const assetFields = [
  { type: 'image', label: '图片', placeholder: '/path/to/shot-001.png' },
  { type: 'keyframe', label: '关键帧', placeholder: '/path/to/shot-001-keyframe.png' },
  { type: 'video', label: '视频', placeholder: '/path/to/shot-001.mp4' }
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

onMounted(() => {
  refreshProjects()
})

async function refreshProjects() {
  try {
    const payload = await listProjects()
    projects.value = payload.projects || []
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载项目列表失败'
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
    selectedShot.value = null
    validationReport.value = { render_ready: false, issues: [] }
    return
  }

  await loadProjectShots(Number(selectedProjectId.value))
}

async function loadProjectShots(projectId) {
  try {
    const payload = await getProjectShots(projectId)
    parsed.value = { project: selectedProject.value, shots: payload.shots || [] }
    shots.value = payload.shots || []
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
