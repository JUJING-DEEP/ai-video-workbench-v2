// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import VideoWorkbench from '../VideoWorkbench.vue'
import {
  bindShotAsset,
  getProjectShots,
  listProjects
} from '../../services/videoWorkbenchApi'

vi.mock('../../services/videoWorkbenchApi', () => ({
  bindShotAsset: vi.fn().mockResolvedValue({ shot: {} }),
  createProject: vi.fn(),
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
  parseStoryboard: vi.fn()
}))

async function flushPromises() {
  await Promise.resolve()
  await Promise.resolve()
}

describe('VideoWorkbench', () => {
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
})
