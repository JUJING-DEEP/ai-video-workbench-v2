// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import demoProject from '../../demo/coffee-commercial.json'
import VideoWorkbench from '../src/views/VideoWorkbench.vue'
import {
  bindShotAsset,
  createProject,
  createProjectAsset,
  exportRenderPlan,
  generateRenderPlan,
  getJimengSettings,
  getNanoBananaProviderSettings,
  getProjectShots,
  getRenderPlan,
  getTimeline,
  importStoryboard,
  listProjectAssets,
  listProjects,
  reorderShots,
  uploadProjectAsset
} from '../src/services/videoWorkbenchApi'

vi.mock('../src/services/videoWorkbenchApi', () => ({
  bindShotAsset: vi.fn(),
  createProject: vi.fn(),
  createProjectAsset: vi.fn(),
  exportRenderPlan: vi.fn(),
  generateRenderPlan: vi.fn(),
  getJimengSettings: vi.fn(),
  getNanoBananaProviderSettings: vi.fn(),
  getProjectShots: vi.fn(),
  getRenderPlan: vi.fn(),
  getTimeline: vi.fn(),
  importStoryboard: vi.fn(),
  listProjectAssets: vi.fn(),
  listProjects: vi.fn(),
  parseStoryboard: vi.fn(),
  pollVideoJob: vi.fn(),
  reorderShots: vi.fn(),
  saveJimengSettings: vi.fn(),
  saveNanoBananaProviderSettings: vi.fn(),
  uploadProjectAsset: vi.fn()
}))

async function flushPromises() {
  await Promise.resolve()
  await Promise.resolve()
}

describe('VideoWorkbench browser E2E smoke', () => {
  beforeEach(() => {
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:coffee-preview'),
      revokeObjectURL: vi.fn()
    })

    listProjects
      .mockResolvedValueOnce({ projects: [] })
      .mockResolvedValue({ projects: [demoProject.project] })
    createProject.mockResolvedValue({ project: demoProject.project })
    importStoryboard.mockResolvedValue({ shots: demoProject.shots })
    getProjectShots.mockResolvedValue({ shots: demoProject.shots })
    getNanoBananaProviderSettings.mockResolvedValue({
      settings: { provider: 'nano_banana', configured: false, enabled: false }
    })
    getJimengSettings.mockResolvedValue({
      settings: { provider: 'jimeng', configured: false, enabled: false }
    })
    listProjectAssets.mockResolvedValue({ assets: demoProject.assets })
    uploadProjectAsset.mockResolvedValue({
      name: demoProject.assets[0].name,
      path: demoProject.assets[0].path,
      asset_type: demoProject.assets[0].asset_type
    })
    createProjectAsset.mockResolvedValue({ asset: demoProject.assets[0] })
    bindShotAsset.mockResolvedValue({ shot: demoProject.shots[0] })
    getTimeline.mockResolvedValue({
      project_id: demoProject.project.id,
      shots: demoProject.timeline
    })
    reorderShots.mockResolvedValue({
      project_id: demoProject.project.id,
      shot_ids: [2, 1, 3]
    })
    generateRenderPlan.mockResolvedValue(demoProject.render_plan)
    getRenderPlan.mockResolvedValue(demoProject.render_plan)
    exportRenderPlan.mockResolvedValue({
      path: demoProject.render_plan.export_path,
      render_plan: demoProject.render_plan
    })
  })

  it('imports the coffee demo, uploads and binds an asset, reorders timeline, and exports a render plan', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('#project-title').setValue(demoProject.project.title)
    await wrapper.find('.video-workbench__project-bar button').trigger('click')
    await flushPromises()

    await wrapper.find('textarea[aria-label="粘贴 Google AI Studio 分镜文本"]').setValue(
      demoProject.storyboard_text
    )
    await wrapper.find('.video-workbench__header button').trigger('click')
    await flushPromises()

    const file = new File(['coffee-image'], demoProject.assets[0].name, { type: 'image/png' })
    const uploadInput = wrapper.find('#asset-library-upload-file')
    Object.defineProperty(uploadInput.element, 'files', {
      value: [file],
      configurable: true
    })
    await uploadInput.trigger('change')
    await wrapper.find('[data-testid="upload-library-asset"]').trigger('click')
    await flushPromises()

    await wrapper.find(`[data-testid="bind-library-asset-${demoProject.assets[0].id}-image"]`).trigger('click')
    await flushPromises()

    await wrapper.find('[data-testid="move-shot-2-up"]').trigger('click')
    await wrapper.find('[data-testid="save-timeline"]').trigger('click')
    await flushPromises()

    await wrapper.find('[data-testid="generate-render-plan"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="export-render-plan"]').trigger('click')
    await flushPromises()

    expect(createProject).toHaveBeenCalledWith({
      title: demoProject.project.title,
      role_card: '',
      audio_path: '',
      audio_duration_seconds: null
    })
    expect(importStoryboard).toHaveBeenCalledWith(demoProject.project.id, demoProject.storyboard_text.trim())
    expect(uploadProjectAsset).toHaveBeenCalledWith(demoProject.project.id, 'image', file)
    expect(bindShotAsset).toHaveBeenCalledWith(
      demoProject.project.id,
      demoProject.shots[0].shot_id,
      'image',
      demoProject.assets[0].path
    )
    expect(reorderShots).toHaveBeenCalledWith(demoProject.project.id, [2, 1, 3])
    expect(generateRenderPlan).toHaveBeenCalledWith(demoProject.project.id)
    expect(exportRenderPlan).toHaveBeenCalledWith(demoProject.project.id)
    expect(wrapper.text()).toContain('Render plan exported.')
  })
})
