// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ShotTimeline from '../ShotTimeline.vue'

describe('ShotTimeline', () => {
  it('renders shot cards and emits selection', async () => {
    const wrapper = mount(ShotTimeline, {
      props: {
        shots: [
          { shot_id: 1, mode: 'B', kind: 'image', start_seconds: 0, end_seconds: 2, status: 'parsed' },
          { shot_id: 10, mode: 'KEY_NODE', kind: 'key_node_video', start_seconds: 18, end_seconds: 21, status: 'video_pending' }
        ]
      }
    })

    expect(wrapper.text()).toContain('#001')
    expect(wrapper.text()).toContain('KEY_NODE')

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('select-shot')[0][0].shot_id).toBe(1)
  })
})
