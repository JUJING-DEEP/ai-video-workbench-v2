export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function readErrorMessage(response) {
  const fallback = `Request failed: ${response.status}`
  const contentType = response.headers.get('content-type') || ''

  if (contentType.includes('application/json')) {
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') {
        return body.detail
      }
      if (body.detail) {
        return JSON.stringify(body.detail)
      }
      return JSON.stringify(body)
    } catch {
      return fallback
    }
  }

  const text = await response.text()
  return text || fallback
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  })

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }

  return response.json()
}

export function parseStoryboard(text) {
  return request('/api/video-workbench/parse', {
    method: 'POST',
    body: JSON.stringify({ text })
  })
}

export function listProjects() {
  return request('/api/video-workbench/projects')
}

export function createProject(project) {
  return request('/api/video-workbench/projects', {
    method: 'POST',
    body: JSON.stringify(project)
  })
}

export function getProjectShots(projectId) {
  return request(`/api/video-workbench/projects/${projectId}/shots`)
}

export function importStoryboard(projectId, text) {
  return request(`/api/video-workbench/projects/${projectId}/storyboard`, {
    method: 'POST',
    body: JSON.stringify({ text })
  })
}

export function bindShotAsset(projectId, shotId, assetType, path) {
  return request(`/api/video-workbench/projects/${projectId}/shots/${shotId}/assets`, {
    method: 'POST',
    body: JSON.stringify({ asset_type: assetType, path })
  })
}

export function listProjectAssets(projectId) {
  return request(`/api/video-workbench/projects/${projectId}/assets`)
}

export function createProjectAsset(projectId, asset) {
  return request(`/api/video-workbench/projects/${projectId}/assets`, {
    method: 'POST',
    body: JSON.stringify(asset)
  })
}
