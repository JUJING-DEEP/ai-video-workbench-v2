// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
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
  for (let index = 0; index < 20; index += 1) {
    await Promise.resolve()
    await nextTick()
  }
}

describe('VideoWorkbench browser E2E smoke', () => {
  let currentTimeline

  beforeEach(() => {
    currentTimeline = demoProject.timeline

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
    createProjectAsset.mockImplementation((_projectId, asset) => Promise.resolve({ asset }))
    bindShotAsset.mockImplementation((_projectId, shotId) => {
      return Promise.resolve({ shot: demoProject.shots.find((shot) => shot.shot_id === shotId) })
    })
    getTimeline.mockImplementation(() => Promise.resolve({
      project_id: demoProject.project.id,
      shots: currentTimeline
    }))
    reorderShots.mockImplementation((_projectId, shotIds) => {
      currentTimeline = shotIds.map((shotId, index) => {
        const shot = demoProject.timeline.find((item) => item.shot_id === shotId)
        return { ...shot, order: index + 1 }
      })
      return Promise.resolve({
        project_id: demoProject.project.id,
        shot_ids: shotIds
      })
    })
    generateRenderPlan.mockImplementation(() => Promise.resolve({
      ...demoProject.render_plan,
      items: currentTimeline.map((shot, index) => ({
        shot_id: shot.shot_id,
        order: index + 1,
        video_path: shot.video_path,
        duration_seconds: shot.duration_seconds
      }))
    }))
    getRenderPlan.mockResolvedValue(demoProject.render_plan)
    exportRenderPlan.mockImplementation(() => Promise.resolve({
      path: demoProject.render_plan.export_path,
      render_plan: {
        project_id: demoProject.project.id,
        shots: currentTimeline.map((shot) => ({
          shot_id: shot.shot_id,
          video_path: shot.video_path,
          duration_seconds: shot.duration_seconds
        }))
      }
    }))
  })

  it('imports the coffee demo, verifies assets, reorders timeline, and exports a render plan', async () => {
    const wrapper = mount(VideoWorkbench)
    await flushPromises()

    await wrapper.find('[data-testid="import-demo"]').trigger('click')
    await flushPromises()

    await wrapper.find('[data-testid="move-shot-2-up"]').trigger('click')
    await wrapper.find('[data-testid="save-timeline"]').trigger('click')
    await flushPromises()

    await wrapper.find('[data-testid="generate-render-plan"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="export-render-plan"]').trigger('click')
    await flushPromises()

    const renderRows = wrapper
      .find('[aria-label="Render Pipeline"]')
      .findAll('tbody tr')
      .map((row) => row.text())

    expect(createProject).toHaveBeenCalledWith({
      title: demoProject.project.title,
      role_card: demoProject.project.role_card,
      audio_path: demoProject.project.audio_path,
      audio_duration_seconds: demoProject.project.audio_duration_seconds
    })
    expect(importStoryboard).toHaveBeenCalledWith(demoProject.project.id, demoProject.storyboard_text.trim())
    expect(createProjectAsset).toHaveBeenCalledTimes(demoProject.assets.length)
    expect(bindShotAsset).toHaveBeenCalledWith(
      demoProject.project.id,
      demoProject.shots[0].shot_id,
      'image',
      demoProject.shots[0].image_path
    )
    expect(wrapper.text()).toContain('coffee-shot-001.png')
    expect(reorderShots).toHaveBeenCalledWith(demoProject.project.id, [1, 2, 3])
    expect(reorderShots).toHaveBeenCalledWith(demoProject.project.id, [2, 1, 3])
    expect(generateRenderPlan).toHaveBeenCalledWith(demoProject.project.id)
    expect(exportRenderPlan).toHaveBeenCalledWith(demoProject.project.id)
    expect(renderRows).toEqual([
      '#1demo/assets/coffee-shot-002.mp44s',
      '#2demo/assets/coffee-shot-001.mp44s',
      '#3demo/assets/coffee-shot-003.mp44s'
    ])
    expect(wrapper.text()).toContain('Render plan exported.')
  })
})
