export type UserProfile = {
  id: number
  name: string
  avatar_data_url: string | null
  is_online: boolean
  created_at: string
  updated_at: string
}

export type CreateUserProfileInput = {
  name: string
  avatarDataUrl?: string | null
}

export type UpdateUserProfileInput = {
  name: string
  avatarDataUrl: string | null
}

export type DeleteUserProfileResponse = {
  success: boolean
  active_profile: UserProfile | null
}
