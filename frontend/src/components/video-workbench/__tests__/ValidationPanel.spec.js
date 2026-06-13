// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ValidationPanel from '../ValidationPanel.vue'

describe('ValidationPanel', () => {
  it('shows render ready state', () => {
    const wrapper = mount(ValidationPanel, {
      props: { report: { render_ready: true, issues: [] } }
    })

    expect(wrapper.text()).toContain('可以渲染')
  })

  it('shows validation issues', () => {
    const wrapper = mount(ValidationPanel, {
      props: { report: { render_ready: false, issues: [{ code: 'missing_image', shot_id: 1, message: 'Shot 1 needs an image' }] } }
    })

    expect(wrapper.text()).toContain('missing_image')
    expect(wrapper.text()).toContain('Shot 1 needs an image')
  })
})
