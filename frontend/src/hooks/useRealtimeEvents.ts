import { useEffect, useRef } from 'react'
import { REALTIME_EVENT_NAME } from '../types/realtime'
import type { RealtimeEvent } from '../types/realtime'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')
const WS_BASE_URL = (import.meta.env.VITE_WS_BASE_URL ?? '').replace(/\/$/, '')

function realtimeUrl(profileId: number | null): string {
  const query = profileId ? `?${new URLSearchParams({ profile_id: String(profileId) }).toString()}` : ''
  const absoluteBaseUrl = WS_BASE_URL || (API_BASE_URL.startsWith('http') ? API_BASE_URL : '')

  if (absoluteBaseUrl) {
    const url = new URL(absoluteBaseUrl)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    url.pathname = '/ws/realtime'
    url.search = query
    return url.toString()
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  if (import.meta.env.DEV) {
    return `${protocol}//${window.location.hostname}:8000/ws/realtime${query}`
  }

  return `${protocol}//${window.location.host}/ws/realtime${query}`
}

export function useRealtimeEvents(
  profileId: number | null | undefined,
  onEvent?: (event: RealtimeEvent) => void,
  options: { connectWithoutProfile?: boolean } = {},
) {
  const connectWithoutProfile = options.connectWithoutProfile ?? false
  const onEventRef = useRef(onEvent)

  useEffect(() => {
    onEventRef.current = onEvent
  }, [onEvent])

  useEffect(() => {
    if (!profileId && !connectWithoutProfile) {
      return undefined
    }

    let socket: WebSocket | null = null
    let reconnectTimer: number | null = null
    let closedByEffect = false

    const connect = () => {
      socket = new WebSocket(realtimeUrl(profileId ?? null))

      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data as string) as RealtimeEvent
          window.dispatchEvent(new CustomEvent<RealtimeEvent>(REALTIME_EVENT_NAME, { detail: event }))
          onEventRef.current?.(event)
        } catch {
          // Ignore malformed realtime messages; HTTP refresh paths remain available.
        }
      }

      socket.onclose = () => {
        if (closedByEffect) {
          return
        }
        reconnectTimer = window.setTimeout(connect, 2500)
      }
    }

    connect()

    return () => {
      closedByEffect = true
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer)
      }
      socket?.close()
    }
  }, [connectWithoutProfile, profileId])
}
