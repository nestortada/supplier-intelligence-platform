const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const ACTIVE_PROFILE_STORAGE_KEY = 'supplierintel.activeProfileId'

export class ApiRequestError extends Error {
  status: number
  details: unknown

  constructor(message: string, status: number, details: unknown) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
    this.details = details
  }
}

type QueryValue = string | number | boolean | null | undefined

export function buildQuery(params: Record<string, QueryValue>): string {
  const query = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return
    }
    query.set(key, String(value))
  })

  const serialized = query.toString()
  return serialized ? `?${serialized}` : ''
}

function resolveApiUrl(path: string): string {
  if (path.startsWith('http')) {
    return path
  }

  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
}

function errorMessageFromPayload(payload: unknown, fallback: string): string {
  if (payload && typeof payload === 'object') {
    const record = payload as Record<string, unknown>
    if (typeof record.error === 'string') {
      return record.error
    }
    if (typeof record.detail === 'string') {
      return record.detail
    }
  }

  if (typeof payload === 'string' && payload.trim()) {
    return payload
  }

  return fallback
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const hasBody = init.body !== undefined && init.body !== null
  const isFormData = typeof FormData !== 'undefined' && init.body instanceof FormData
  const profileId = window.localStorage.getItem(ACTIVE_PROFILE_STORAGE_KEY)

  if (hasBody && !isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (profileId && !headers.has('X-Profile-Id')) {
    headers.set('X-Profile-Id', profileId)
  }

  const response = await fetch(resolveApiUrl(path), {
    ...init,
    headers,
  })

  const contentType = response.headers.get('content-type') ?? ''
  const payload: unknown = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    throw new ApiRequestError(
      errorMessageFromPayload(payload, `Error HTTP ${response.status}`),
      response.status,
      payload,
    )
  }

  return payload as T
}
