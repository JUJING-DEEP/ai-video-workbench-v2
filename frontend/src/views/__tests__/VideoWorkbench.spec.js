// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import VideoWorkbench from '../VideoWorkbench.vue'
import {
  bindShotAsset,
  getProjectShots,
  listProjectAssets,
  listProjects
} from '../../services/videoWorkbenchApi'

vi.mock('../../services/videoWorkbenchApi', () => ({
  bindShotAsset: vi.fn().mockResolvedValue({ shot: {} }),
  createProject: vi.fn(),
  createProjectAsset: vi.fn(),
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
  parseStoryboard: vi.fn()
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
})
