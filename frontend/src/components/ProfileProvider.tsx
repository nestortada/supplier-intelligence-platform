import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { createProfile, deleteProfile, fetchProfiles, updateProfile } from '../api/profileApi'
import { ProfileContext } from '../contexts/profileContext'
import { useRealtimeEvents } from '../hooks/useRealtimeEvents'
import type { UserProfile } from '../types/profile'

export const ACTIVE_PROFILE_STORAGE_KEY = 'supplierintel.activeProfileId'
export const ACTIVE_PROFILE_NAME_STORAGE_KEY = 'supplierintel.activeProfileName'

type ProfileProviderProps = {
  children: ReactNode
}

function storedProfileId(): number | null {
  const value = window.localStorage.getItem(ACTIVE_PROFILE_STORAGE_KEY)
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

export default function ProfileProvider({ children }: ProfileProviderProps) {
  const [profiles, setProfiles] = useState<UserProfile[]>([])
  const [activeProfile, setActiveProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshProfiles = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const nextProfiles = await fetchProfiles()
      setProfiles(nextProfiles)

      const activeSyncId = window.localStorage.getItem('supplierintel.activeProfileSyncId')
      let restoredProfile = nextProfiles.find((profile) => profile.sync_id === activeSyncId) ?? null

      if (!restoredProfile && activeSyncId === null) {
        const activeId = storedProfileId()
        restoredProfile = nextProfiles.find((profile) => profile.id === activeId) ?? null
      }

      setActiveProfile(restoredProfile)
      if (restoredProfile) {
        window.localStorage.setItem(ACTIVE_PROFILE_NAME_STORAGE_KEY, restoredProfile.name)
        window.localStorage.setItem(ACTIVE_PROFILE_STORAGE_KEY, String(restoredProfile.id))
        if (restoredProfile.sync_id) {
          window.localStorage.setItem('supplierintel.activeProfileSyncId', restoredProfile.sync_id)
        }
      }
      if (!restoredProfile) {
        window.localStorage.removeItem(ACTIVE_PROFILE_STORAGE_KEY)
        window.localStorage.removeItem(ACTIVE_PROFILE_NAME_STORAGE_KEY)
        window.localStorage.removeItem('supplierintel.activeProfileSyncId')
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudieron cargar los perfiles.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void refreshProfiles()
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [refreshProfiles])

  useRealtimeEvents(activeProfile?.id)

  const selectProfile = useCallback((profile: UserProfile) => {
    window.localStorage.setItem(ACTIVE_PROFILE_STORAGE_KEY, String(profile.id))
    window.localStorage.setItem(ACTIVE_PROFILE_NAME_STORAGE_KEY, profile.name)
    if (profile.sync_id) {
      window.localStorage.setItem('supplierintel.activeProfileSyncId', profile.sync_id)
    } else {
      window.localStorage.removeItem('supplierintel.activeProfileSyncId')
    }
    setActiveProfile(profile)
  }, [])

  const createUserProfile = useCallback(
    async (name: string, avatarDataUrl?: string | null) => {
      const profile = await createProfile({ avatarDataUrl, name })
      setProfiles((current) => [...current, profile])
      selectProfile(profile)
      return profile
    },
    [selectProfile],
  )

  const updateActiveProfile = useCallback(
    async (name: string, avatarDataUrl: string | null) => {
      if (!activeProfile) {
        throw new Error('No hay un perfil activo.')
      }

      const updatedProfile = await updateProfile(activeProfile.id, { avatarDataUrl, name })
      setProfiles((current) => current.map((profile) => (profile.id === updatedProfile.id ? updatedProfile : profile)))
      selectProfile(updatedProfile)
      return updatedProfile
    },
    [activeProfile, selectProfile],
  )

  const deleteActiveProfile = useCallback(async () => {
    if (!activeProfile) {
      throw new Error('No hay un perfil activo.')
    }

    const response = await deleteProfile(activeProfile.id)
    const nextProfiles = await fetchProfiles()
    setProfiles(nextProfiles)

    if (response.active_profile) {
      selectProfile(response.active_profile)
      return response.active_profile
    }

    setActiveProfile(null)
    window.localStorage.removeItem(ACTIVE_PROFILE_STORAGE_KEY)
    window.localStorage.removeItem(ACTIVE_PROFILE_NAME_STORAGE_KEY)
    return null
  }, [activeProfile, selectProfile])

  const value = useMemo(
    () => ({
      activeProfile,
      createUserProfile,
      deleteActiveProfile,
      error,
      loading,
      profiles,
      refreshProfiles,
      selectProfile,
      updateActiveProfile,
    }),
    [
      activeProfile,
      createUserProfile,
      deleteActiveProfile,
      error,
      loading,
      profiles,
      refreshProfiles,
      selectProfile,
      updateActiveProfile,
    ],
  )

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>
}
