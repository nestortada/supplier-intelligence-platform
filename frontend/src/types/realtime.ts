export type RealtimeEvent = {
  type: string
  profile_id: number | null
  payload: Record<string, unknown>
  created_at?: string
}

export const REALTIME_EVENT_NAME = 'supplierintel:realtime'
