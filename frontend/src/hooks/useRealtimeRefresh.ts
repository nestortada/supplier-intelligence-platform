import { useEffect } from 'react'
import { REALTIME_EVENT_NAME } from '../types/realtime'
import type { RealtimeEvent } from '../types/realtime'


export function useRealtimeRefresh(eventTypes: string[], refresh: () => void) {
  useEffect(() => {
    const eventTypeSet = new Set(eventTypes)
    const handleRealtimeEvent = (event: Event) => {
      const detail = (event as CustomEvent<RealtimeEvent>).detail
      if (!detail || !eventTypeSet.has(detail.type)) {
        return
      }
      refresh()
    }

    window.addEventListener(REALTIME_EVENT_NAME, handleRealtimeEvent)
    const interval = window.setInterval(() => {
      refresh()
    }, 5000)

    return () => {
      window.removeEventListener(REALTIME_EVENT_NAME, handleRealtimeEvent)
      window.clearInterval(interval)
    }
  }, [eventTypes, refresh])
}
