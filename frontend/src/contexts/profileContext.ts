import { createContext } from 'react'
import type { UserProfile } from '../types/profile'

export type ProfileContextValue = {
  activeProfile: UserProfile | null
  error: string | null
  loading: boolean
  profiles: UserProfile[]
  createUserProfile: (name: string, avatarDataUrl?: string | null) => Promise<UserProfile>
  deleteActiveProfile: () => Promise<UserProfile | null>
  refreshProfiles: () => Promise<void>
  selectProfile: (profile: UserProfile) => void
  updateActiveProfile: (name: string, avatarDataUrl: string | null) => Promise<UserProfile>
}

export const ProfileContext = createContext<ProfileContextValue | null>(null)
