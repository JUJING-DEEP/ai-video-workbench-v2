// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import VideoWorkbench from '../VideoWorkbench.vue'
import {
  bindShotAsset,
  createProjectAsset,
  createVideoJob,
  generateKeyframe,
  generateProjectImage,
  generateVideo,
  generateRenderPlan,
  exportRenderPlan,
  getTimeline,
  getNanoBananaProviderSettings,
  pollVideoJob,
  getRenderPlan,
  getProjectShots,
  listProjectAssets,
  listProjects,
  reorderShots,
  saveJimengSettings,
  saveNanoBananaProviderSettings,
  uploadProjectAsset
} from '../../services/videoWorkbenchApi'

vi.mock('../../services/videoWorkbenchApi', () => ({
  bindShotAsset: vi.fn().mockResolvedValue({ shot: {} }),
  createProject: vi.fn(),
  createProjectAsset: vi.fn().mockResolvedValue({ asset: {} }),
  createVideoJob: vi.fn().mockResolvedValue({
    job: {
      id: 501,
      project_id: 7,
      shot_id: 1,
      provider: 'jimeng',
      status: 'submitted',
      submit_id: 'fake-submit-501',
      result_url: '',
      output_path: '',
      error_message: ''
    }
  }),
  generateKeyframe: vi.fn().mockResolvedValue({
    asset_id: 31,
    shot_id: 1,
    path: 'data/uploads/7/generated/keyframes/nano-banana-keyframe.png',
    asset_type: 'keyframe'
  }),
  generateProjectImage: vi.fn().mockResolvedValue({
    asset_id: 21,
    image_path: 'data/uploads/7/generated/nano-banana.png',
    asset_type: 'image'
  }),
  generateVideo: vi.fn().mockResolvedValue({
    asset_id: 41,
    shot_id: 1,
    video_path: 'data/uploads/7/generated/videos/jimeng-video-1.mp4',
    asset_type: 'video'
  }),
  generateRenderPlan: vi.fn().mockResolvedValue({
    id: 5,
    project_id: 7,
    items: [
      {
        shot_id: 1,
        order: 1,
        video_path: 'data/uploads/7/generated/videos/jimeng-video-1.mp4',
        duration_seconds: 2
      }
    ]
  }),
  getRenderPlan: vi.fn().mockResolvedValue({
    id: 5,
    project_id: 7,
    items: [
      {
        shot_id: 1,
        order: 1,
        video_path: 'data/uploads/7/generated/videos/jimeng-video-1.mp4',
        duration_seconds: 2
      }
    ]
  }),
  getJimengSettings: vi.fn().mockResolvedValue({
    settings: {
      provider: 'jimeng',
      base_url: 'https://jimeng.example/generate',
      region: 'cn-north-1',
      endpoint: 'https://open.volcengineapi.com',
      model: 'jimeng-v3',
      configured: true,
      enabled: true
    }
  }),
  getTimeline: vi.fn().mockResolvedValue({
    project_id: 7,
    shots: [
      {
        shot_id: 1,
        order: 1,
        title: 'Opening Shot',
        video_path: '/renders/opening.mp4',
        duration_seconds: 2
      },
      {
        shot_id: 2,
        order: 2,
        title: 'Close-up Shot',
        video_path: '',
        duration_seconds: 3
      },
      {
        shot_id: 3,
        order: 3,
        title: 'Ending Shot',
        video_path: '/renders/ending.mp4',
        duration_seconds: 4
      }
    ]
  }),
  exportRenderPlan: vi.fn().mockResolvedValue({
    path: 'data/exports/7/render-plan.json',
    render_plan: {
      project_id: 7,
      shots: [
        {
          shot_id: 1,
          video_path: 'data/uploads/7/generated/videos/jimeng-video-1.mp4',
          duration_seconds: 2
        }
      ]
    }
  }),
  getNanoBananaProviderSettings: vi.fn().mockResolvedValue({
    settings: {
      provider: 'nano_banana',
      base_url: 'https://nano.example/generate',
      configured: true,
      enabled: true,
      credentials: { api_key: true }
    }
  }),
  getProjectShots: vi.fn().mockResolvedValue({
    shots: [
      {
        shot_id: 1,
        mode: 'B',
        kind: 'image',
        start_seconds: 0,
        end_seconds: 2,
        status: 'parsed',
        dialogue_zh: '你好',
        image_prompt: 'Scene: Test',
        image_path: '',
        keyframe_path: '',
        video_path: ''
      }
    ]
  }),
  importStoryboard: vi.fn(),
  listProjects: vi.fn().mockResolvedValue({
    projects: [{ id: 7, title: 'Asset Project', slug: 'asset-project' }]
  }),
  listProjectAssets: vi.fn().mockResolvedValue({
    assets: [
      {
        id: 11,
        project_id: 7,
        asset_type: 'image',
        name: 'Shot 001 Image',
        path: '/library/shot-001.png',
        created_at: '2026-06-13 12:00:00'
      },
      {
        id: 12,
        project_id: 7,
        asset_type: 'keyframe',
        name: 'Hook Keyframe',
        path: '/library/hook-keyframe.png',
        source: 'manual',
        prompt: '',
        created_at: '2026-06-13 12:01:00'
      },
      {
        id: 13,
        project_id: 7,
        asset_type: 'video',
        name: 'Hook Video',
        path: '/library/hook.mp4',
        created_at: '2026-06-13 12:02:00'
      }
    ]
  }),
  parseStoryboard: vi.fn(),
  pollVideoJob: vi.fn().mockResolvedValue({
    job: {
      id: 501,
      project_id: 7,
      shot_id: 1,
      provider: 'jimeng',
      status: 'completed',
      submit_id: 'fake-submit-501',
      result_url: 'https://jimeng.example/results/fake-submit-501.mp4',
      output_path: 'data/uploads/7/generated/videos/jimeng-rest-job-501.mp4',
      error_message: ''
    }
  }),
  reorderShots: vi.fn().mockResolvedValue({ project_id: 7, shot_ids: [2, 1, 3] }),
  saveJimengSettings: vi.fn().mockResolvedValue({
    settings: {
      provider: 'jimeng',
      base_url: 'https://jimeng.example/v2',
      configured: true,
      enabled: true
    }
  }),
  saveNanoBananaProviderSettings: vi.fn().mockResolvedValue({
    settings: {
      provider: 'nano_banana',
      base_url: 'https://nano.example/v2',
      configured: true,
      enabled: true,
      credentials: { api_key: true }
    }
  }),
  uploadProjectAsset: vi.fn().mockResolvedValue({
    name: 'uploaded.png',
    path: 'data/uploads/7/uploaded.png',
    asset_type: 'image'
  })
}))

async function flushPromises() {
  await Promise.resolve()
  await Promise.resolve()
}

describe('VideoWorkbench', () => {
  beforeEach(() => {
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:preview-url'),
      revokeObjectURL: vi.fn()
    })
  })

  it('binds an image asset path for the selected shot', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    const imageInput = wrapper.find('#asset-image')
    await imageInput.setValue('/renders/shot-001.png')
    await wrapper.find('.video-workbench__asset-row button').trigger('click')
    await flushPromises()

    expect(listProjects).toHaveBeenCalled()
    expect(getProjectShots).toHaveBeenCalledWith(7)
    expect(bindShotAsset).toHaveBeenCalledWith(7, 1, 'image', '/renders/shot-001.png')
  })

  it('shows bound and unbound status for selected shot assets', async () => {
    getProjectShots.mockResolvedValueOnce({
      shots: [
        {
          shot_id: 1,
          mode: 'B',
          kind: 'image',
          start_seconds: 0,
          end_seconds: 2,
          status: 'image_ready',
          dialogue_zh: '你好',
          image_prompt: 'Scene: Test',
          image_path: '/renders/shot-001.png',
          keyframe_path: '',
          video_path: ''
        }
      ]
    })

    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    expect(wrapper.text()).toContain('图片 已绑定')
    expect(wrapper.text()).toContain('关键帧 未绑定')
    expect(wrapper.text()).toContain('视频 未绑定')
  })

  it('previews a selected local image file and fills the asset path', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    const file = new File(['image-bytes'], 'shot-001.png', { type: 'image/png' })
    const fileInput = wrapper.find('#asset-image-file')
    Object.defineProperty(fileInput.element, 'files', {
      value: [file],
      configurable: true
    })
    await fileInput.trigger('change')
    await flushPromises()

    expect(URL.createObjectURL).toHaveBeenCalledWith(file)
    expect(wrapper.find('#asset-image').element.value).toBe('shot-001.png')
    expect(wrapper.find('img[alt="图片预览"]').attributes('src')).toBe('blob:preview-url')
  })

  it('shows project assets in the asset library', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    expect(listProjectAssets).toHaveBeenCalledWith(7)
    expect(wrapper.text()).toContain('Image assets')
    expect(wrapper.text()).toContain('Shot 001 Image')
    expect(wrapper.text()).toContain('/library/shot-001.png')
    expect(wrapper.text()).toContain('Keyframe assets')
    expect(wrapper.text()).toContain('Hook Keyframe')
    expect(wrapper.text()).toContain('Video assets')
    expect(wrapper.text()).toContain('Hook Video')
  })

  it('binds an asset library item to the selected shot', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="bind-library-asset-11-image"]').trigger('click')
    await flushPromises()

    expect(bindShotAsset).toHaveBeenCalledWith(7, 1, 'image', '/library/shot-001.png')
  })

  it('disables asset library binding when no shot is selected', async () => {
    getProjectShots.mockResolvedValueOnce({ shots: [] })

    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    expect(wrapper.find('[data-testid="bind-library-asset-11-image"]').attributes('disabled')).toBeDefined()
  })

  it('uploads a local asset and creates an asset library entry', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('#asset-library-upload-type').setValue('image')
    const file = new File(['image-bytes'], 'uploaded.png', { type: 'image/png' })
    const fileInput = wrapper.find('#asset-library-upload-file')
    Object.defineProperty(fileInput.element, 'files', {
      value: [file],
      configurable: true
    })
    await fileInput.trigger('change')
    await wrapper.find('[data-testid="upload-library-asset"]').trigger('click')
    await flushPromises()

    expect(uploadProjectAsset).toHaveBeenCalledWith(7, 'image', file)
    expect(createProjectAsset).toHaveBeenCalledWith(7, {
      asset_type: 'image',
      name: 'uploaded.png',
      path: 'data/uploads/7/uploaded.png'
    })
    expect(listProjectAssets).toHaveBeenCalledWith(7)
    expect(wrapper.text()).toContain('素材上传成功。')
  })

  it('shows an upload failure message', async () => {
    uploadProjectAsset.mockRejectedValueOnce(new Error('Upload failed'))

    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    const file = new File(['video-bytes'], 'bad.mp4', { type: 'video/mp4' })
    const fileInput = wrapper.find('#asset-library-upload-file')
    Object.defineProperty(fileInput.element, 'files', {
      value: [file],
      configurable: true
    })
    await fileInput.trigger('change')
    await wrapper.find('[data-testid="upload-library-asset"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Upload failed')
  })

  it('saves Nano Banana provider settings', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#nano-banana-api-key').setValue('new-key')
    await wrapper.find('#nano-banana-base-url').setValue('https://nano.example/v2')
    await wrapper.find('[data-testid="save-nano-banana-settings"]').trigger('click')
    await flushPromises()

    expect(getNanoBananaProviderSettings).toHaveBeenCalled()
    expect(saveNanoBananaProviderSettings).toHaveBeenCalledWith({
      api_key: 'new-key',
      base_url: 'https://nano.example/v2',
      enabled: true
    })
    expect(wrapper.text()).toContain('Provider settings saved.')
  })

  it('saves Jimeng REST provider settings', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#jimeng-access-key').setValue('new-access-key')
    await wrapper.find('#jimeng-secret-key').setValue('new-secret-key')
    await wrapper.find('#jimeng-region').setValue('cn-north-1')
    await wrapper.find('#jimeng-endpoint').setValue('https://open.volcengineapi.com')
    await wrapper.find('#jimeng-model').setValue('jimeng-v3')
    await wrapper.find('[data-testid="save-jimeng-settings"]').trigger('click')
    await flushPromises()

    expect(saveJimengSettings).toHaveBeenCalledWith({
      api_key: '',
      base_url: 'https://jimeng.example/generate',
      access_key: 'new-access-key',
      secret_key: 'new-secret-key',
      region: 'cn-north-1',
      endpoint: 'https://open.volcengineapi.com',
      model: 'jimeng-v3',
      enabled: true
    })
  })

  it('does not prefill provider credentials from settings responses', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    expect(wrapper.find('#nano-banana-api-key').element.value).toBe('')
    expect(wrapper.find('#jimeng-api-key').element.value).toBe('')
    expect(wrapper.text()).not.toContain('existing-key')
    expect(wrapper.text()).not.toContain('existing-jimeng-key')
  })

  it('generates an image and refreshes the asset library', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('#nano-banana-prompt').setValue('Draw a tired stickman.')
    await wrapper.find('[data-testid="generate-nano-banana-image"]').trigger('click')
    await flushPromises()

    expect(generateProjectImage).toHaveBeenCalledWith(7, 'Draw a tired stickman.')
    expect(listProjectAssets).toHaveBeenCalledWith(7)
    expect(wrapper.text()).toContain('Image generated.')
  })

  it('shows Nano Banana generation failures', async () => {
    generateProjectImage.mockRejectedValueOnce(new Error('Provider error'))

    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('#nano-banana-prompt').setValue('Draw a tired stickman.')
    await wrapper.find('[data-testid="generate-nano-banana-image"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Provider error')
  })

  it('renders the keyframe generator panel', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    expect(wrapper.text()).toContain('AI Keyframe Generator')
    expect(wrapper.find('#keyframe-prompt').exists()).toBe(true)
    expect(wrapper.find('[data-testid="generate-keyframe"]').exists()).toBe(true)
  })

  it('disables keyframe generation when no shot is selected', async () => {
    getProjectShots.mockResolvedValueOnce({ shots: [] })

    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    expect(wrapper.find('[data-testid="generate-keyframe"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('请先选择一个 Shot。')
  })

  it('calls generateKeyframe with the selected shot and prompt', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('#keyframe-prompt').setValue('Draw a keyframe.')
    await wrapper.find('[data-testid="generate-keyframe"]').trigger('click')
    await flushPromises()

    expect(generateKeyframe).toHaveBeenCalledWith(7, 1, 'Draw a keyframe.')
  })

  it('shows keyframe generation loading state', async () => {
    let resolveGenerate
    generateKeyframe.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveGenerate = resolve
      })
    )

    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('#keyframe-prompt').setValue('Draw a keyframe.')
    await wrapper.find('[data-testid="generate-keyframe"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Generating keyframe...')

    resolveGenerate({
      asset_id: 31,
      shot_id: 1,
      path: 'data/uploads/7/generated/keyframes/nano-banana-keyframe.png',
      asset_type: 'keyframe'
    })
    await flushPromises()
  })

  it('shows a keyframe generation success message and preview', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('#keyframe-prompt').setValue('Draw a keyframe.')
    await wrapper.find('[data-testid="generate-keyframe"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Keyframe generated.')
    expect(wrapper.find('img[alt="关键帧预览"]').attributes('src')).toBe(
      'data/uploads/7/generated/keyframes/nano-banana-keyframe.png'
    )
  })

  it('refreshes the asset library after keyframe generation', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('#keyframe-prompt').setValue('Draw a keyframe.')
    await wrapper.find('[data-testid="generate-keyframe"]').trigger('click')
    await flushPromises()

    expect(listProjectAssets).toHaveBeenCalledWith(7)
  })

  it('shows keyframe generation errors', async () => {
    generateKeyframe.mockRejectedValueOnce(new Error('Invalid Nano Banana API key.'))

    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('#keyframe-prompt').setValue('Draw a keyframe.')
    await wrapper.find('[data-testid="generate-keyframe"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Invalid Nano Banana API key.')
  })

  it('renders the video generator panel', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    expect(wrapper.text()).toContain('Video Generator')
    expect(wrapper.find('[data-testid="generate-video"]').exists()).toBe(true)
  })

  it('disables video generation without a keyframe', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    expect(wrapper.find('[data-testid="generate-video"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Please generate or bind a keyframe first.')
  })

  it('calls generateVideo for the selected shot', async () => {
    getProjectShots.mockResolvedValueOnce({
      shots: [
        {
          shot_id: 1,
          mode: 'B',
          kind: 'image',
          start_seconds: 0,
          end_seconds: 2,
          status: 'keyframe_ready',
          dialogue_zh: '你好',
          image_prompt: 'Scene: Test',
          image_path: '',
          keyframe_path: 'data/uploads/7/generated/keyframes/keyframe.png',
          video_path: ''
        }
      ]
    })
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="generate-video"]').trigger('click')
    await flushPromises()

    expect(generateVideo).toHaveBeenCalledWith(7, 1, 'mock')
  })

  it('shows video generation loading state', async () => {
    getProjectShots.mockResolvedValueOnce({
      shots: [
        {
          shot_id: 1,
          mode: 'B',
          kind: 'image',
          start_seconds: 0,
          end_seconds: 2,
          status: 'keyframe_ready',
          dialogue_zh: '你好',
          image_prompt: 'Scene: Test',
          image_path: '',
          keyframe_path: 'data/uploads/7/generated/keyframes/keyframe.png',
          video_path: ''
        }
      ]
    })
    let resolveGenerate
    generateVideo.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveGenerate = resolve
      })
    )

    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="generate-video"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Generating video...')

    resolveGenerate({
      asset_id: 41,
      shot_id: 1,
      video_path: 'data/uploads/7/generated/videos/jimeng-video-1.mp4',
      asset_type: 'video'
    })
    await flushPromises()
  })

  it('shows video generation success state and preview', async () => {
    getProjectShots.mockResolvedValueOnce({
      shots: [
        {
          shot_id: 1,
          mode: 'B',
          kind: 'image',
          start_seconds: 0,
          end_seconds: 2,
          status: 'keyframe_ready',
          dialogue_zh: '你好',
          image_prompt: 'Scene: Test',
          image_path: '',
          keyframe_path: 'data/uploads/7/generated/keyframes/keyframe.png',
          video_path: ''
        }
      ]
    })
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="generate-video"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Video generated.')
    expect(wrapper.find('video[aria-label="视频预览"]').attributes('src')).toBe(
      'data/uploads/7/generated/videos/jimeng-video-1.mp4'
    )
  })

  it('refreshes asset library after video generation', async () => {
    getProjectShots.mockResolvedValueOnce({
      shots: [
        {
          shot_id: 1,
          mode: 'B',
          kind: 'image',
          start_seconds: 0,
          end_seconds: 2,
          status: 'keyframe_ready',
          dialogue_zh: '你好',
          image_prompt: 'Scene: Test',
          image_path: '',
          keyframe_path: 'data/uploads/7/generated/keyframes/keyframe.png',
          video_path: ''
        }
      ]
    })
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="generate-video"]').trigger('click')
    await flushPromises()

    expect(listProjectAssets).toHaveBeenCalledWith(7)
  })

  it('shows video generation errors', async () => {
    getProjectShots.mockResolvedValueOnce({
      shots: [
        {
          shot_id: 1,
          mode: 'B',
          kind: 'image',
          start_seconds: 0,
          end_seconds: 2,
          status: 'keyframe_ready',
          dialogue_zh: '你好',
          image_prompt: 'Scene: Test',
          image_path: '',
          keyframe_path: 'data/uploads/7/generated/keyframes/keyframe.png',
          video_path: ''
        }
      ]
    })
    generateVideo.mockRejectedValueOnce(new Error('Video provider error.'))

    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="generate-video"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Video provider error.')
  })


  it('renders provider selector for video generation', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    const selector = wrapper.find('#video-provider')
    expect(selector.exists()).toBe(true)
    expect(selector.element.value).toBe('mock')
    expect(wrapper.text()).toContain('Mock Provider')
    expect(wrapper.text()).toContain('Jimeng Provider')
  })

  it('changes the selected video provider', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('#video-provider').setValue('jimeng')

    expect(wrapper.text()).toContain('Current Provider: Jimeng Provider')
  })

  it('calls generateVideo with the selected provider', async () => {
    getProjectShots.mockResolvedValueOnce({
      shots: [
        {
          shot_id: 1,
          mode: 'B',
          kind: 'image',
          start_seconds: 0,
          end_seconds: 2,
          status: 'keyframe_ready',
          dialogue_zh: '你好',
          image_prompt: 'Scene: Test',
          image_path: '',
          keyframe_path: 'data/uploads/7/generated/keyframes/keyframe.png',
          video_path: ''
        }
      ]
    })
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()
    await wrapper.find('#video-provider').setValue('jimeng')

    await wrapper.find('[data-testid="generate-video"]').trigger('click')
    await flushPromises()

    expect(generateVideo).toHaveBeenCalledWith(7, 1, 'jimeng')
  })

  it('shows the current video provider', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    expect(wrapper.text()).toContain('Current Provider: Mock Provider')
  })


  it('renders video job controls', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    expect(wrapper.text()).toContain('Jimeng REST Job')
    expect(wrapper.find('[data-testid="submit-video-job"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="poll-video-job"]').exists()).toBe(true)
  })

  it('disables submit job button without a keyframe', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    expect(wrapper.find('[data-testid="submit-video-job"]').attributes('disabled')).toBeDefined()
  })

  it('calls createVideoJob for the selected shot', async () => {
    getProjectShots.mockResolvedValueOnce({
      shots: [
        {
          shot_id: 1,
          mode: 'B',
          kind: 'image',
          start_seconds: 0,
          end_seconds: 2,
          status: 'keyframe_ready',
          dialogue_zh: '你好',
          image_prompt: 'Scene: Test',
          image_path: '',
          keyframe_path: 'data/uploads/7/generated/keyframes/keyframe.png',
          video_path: ''
        }
      ]
    })
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="submit-video-job"]').trigger('click')
    await flushPromises()

    expect(createVideoJob).toHaveBeenCalledWith(7, 1)
  })

  it('shows submitted job status', async () => {
    getProjectShots.mockResolvedValueOnce({
      shots: [
        {
          shot_id: 1,
          mode: 'B',
          kind: 'image',
          start_seconds: 0,
          end_seconds: 2,
          status: 'keyframe_ready',
          dialogue_zh: '你好',
          image_prompt: 'Scene: Test',
          image_path: '',
          keyframe_path: 'data/uploads/7/generated/keyframes/keyframe.png',
          video_path: ''
        }
      ]
    })
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()
    await wrapper.find('[data-testid="submit-video-job"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Job status: submitted')
  })

  it('calls pollVideoJob', async () => {
    getProjectShots.mockResolvedValueOnce({
      shots: [
        {
          shot_id: 1,
          mode: 'B',
          kind: 'image',
          start_seconds: 0,
          end_seconds: 2,
          status: 'keyframe_ready',
          dialogue_zh: '你好',
          image_prompt: 'Scene: Test',
          image_path: '',
          keyframe_path: 'data/uploads/7/generated/keyframes/keyframe.png',
          video_path: ''
        }
      ]
    })
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()
    await wrapper.find('[data-testid="submit-video-job"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="poll-video-job"]').trigger('click')
    await flushPromises()

    expect(pollVideoJob).toHaveBeenCalledWith(501)
  })

  it('shows completed video job preview', async () => {
    getProjectShots.mockResolvedValueOnce({
      shots: [
        {
          shot_id: 1,
          mode: 'B',
          kind: 'image',
          start_seconds: 0,
          end_seconds: 2,
          status: 'keyframe_ready',
          dialogue_zh: '你好',
          image_prompt: 'Scene: Test',
          image_path: '',
          keyframe_path: 'data/uploads/7/generated/keyframes/keyframe.png',
          video_path: ''
        }
      ]
    })
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()
    await wrapper.find('[data-testid="submit-video-job"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="poll-video-job"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Job status: completed')
    expect(wrapper.find('video[aria-label="Jimeng job video preview"]').attributes('src')).toBe(
      'data/uploads/7/generated/videos/jimeng-rest-job-501.mp4'
    )
  })

  it('shows video job provider errors', async () => {
    pollVideoJob.mockRejectedValueOnce(new Error('Jimeng provider error.'))
    getProjectShots.mockResolvedValueOnce({
      shots: [
        {
          shot_id: 1,
          mode: 'B',
          kind: 'image',
          start_seconds: 0,
          end_seconds: 2,
          status: 'keyframe_ready',
          dialogue_zh: '你好',
          image_prompt: 'Scene: Test',
          image_path: '',
          keyframe_path: 'data/uploads/7/generated/keyframes/keyframe.png',
          video_path: ''
        }
      ]
    })
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()
    await wrapper.find('[data-testid="submit-video-job"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="poll-video-job"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Jimeng provider error.')
  })

  it('renders the render pipeline panel', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    expect(wrapper.text()).toContain('Render Pipeline')
    expect(wrapper.find('[data-testid="generate-render-plan"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="export-render-plan"]').exists()).toBe(true)
  })

  it('calls generateRenderPlan', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="generate-render-plan"]').trigger('click')
    await flushPromises()

    expect(generateRenderPlan).toHaveBeenCalledWith(7)
  })

  it('shows the render plan list', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="generate-render-plan"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Shot Order')
    expect(wrapper.text()).toContain('data/uploads/7/generated/videos/jimeng-video-1.mp4')
    expect(wrapper.text()).toContain('2s')
  })

  it('calls exportRenderPlan', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="export-render-plan"]').trigger('click')
    await flushPromises()

    expect(exportRenderPlan).toHaveBeenCalledWith(7)
  })

  it('shows export success', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="export-render-plan"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Render plan exported.')
    expect(wrapper.text()).toContain('data/exports/7/render-plan.json')
  })

  it('renders the timeline panel', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    expect(wrapper.text()).toContain('Timeline Editor')
    expect(wrapper.text()).toContain('Opening Shot')
    expect(wrapper.text()).toContain('Video ready')
    expect(wrapper.text()).toContain('3s')
  })

  it('moves a timeline shot up', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="move-shot-2-up"]').trigger('click')
    await flushPromises()

    const previewText = wrapper.find('[data-testid="timeline-preview"]').text()
    expect(previewText.indexOf('1. Close-up Shot')).toBeLessThan(
      previewText.indexOf('2. Opening Shot')
    )
  })

  it('moves a timeline shot down', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="move-shot-1-down"]').trigger('click')
    await flushPromises()

    const previewText = wrapper.find('[data-testid="timeline-preview"]').text()
    expect(previewText.indexOf('1. Close-up Shot')).toBeLessThan(
      previewText.indexOf('2. Opening Shot')
    )
  })

  it('calls reorderShots when saving the timeline', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="move-shot-2-up"]').trigger('click')
    await wrapper.find('[data-testid="save-timeline"]').trigger('click')
    await flushPromises()

    expect(reorderShots).toHaveBeenCalledWith(7, [2, 1, 3])
  })

  it('shows updated order after timeline movement', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="move-shot-3-up"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('2. Ending Shot')
  })

  it('renders the save timeline button', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    expect(wrapper.find('[data-testid="save-timeline"]').exists()).toBe(true)
  })

  it('refreshes timeline and render plan after saving', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-select').setValue('7')
    await flushPromises()

    await wrapper.find('[data-testid="save-timeline"]').trigger('click')
    await flushPromises()

    expect(getTimeline).toHaveBeenCalledWith(7)
    expect(getRenderPlan).toHaveBeenCalledWith(7)
  })
})
