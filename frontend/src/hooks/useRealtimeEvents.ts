import { useEffect } from 'react'
import { REALTIME_EVENT_NAME } from '../types/realtime'
import type { RealtimeEvent } from '../types/realtime'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')

function realtimeUrl(profileId: number): string {
  const query = new URLSearchParams({ profile_id: String(profileId) }).toString()

  if (API_BASE_URL.startsWith('http')) {
    const url = new URL(API_BASE_URL)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    url.pathname = '/ws/realtime'
    url.search = query
    return url.toString()
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/realtime?${query}`
}

export function useRealtimeEvents(profileId: number | null | undefined, onEvent?: (event: RealtimeEvent) => void) {
  useEffect(() => {
    if (!profileId) {
      return undefined
    }

    let socket: WebSocket | null = null
    let reconnectTimer: number | null = null
    let closedByEffect = false

    const connect = () => {
      socket = new WebSocket(realtimeUrl(profileId))

      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data as string) as RealtimeEvent
          window.dispatchEvent(new CustomEvent<RealtimeEvent>(REALTIME_EVENT_NAME, { detail: event }))
          onEvent?.(event)
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
  }, [onEvent, profileId])
}
