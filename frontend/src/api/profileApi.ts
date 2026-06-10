import { apiRequest } from './http'
import type { CreateUserProfileInput, DeleteUserProfileResponse, UpdateUserProfileInput, UserProfile } from '../types/profile'

export function fetchProfiles(): Promise<UserProfile[]> {
  return apiRequest<UserProfile[]>('/profiles')
}

export function createProfile(input: CreateUserProfileInput): Promise<UserProfile> {
  return apiRequest<UserProfile>('/profiles', {
    method: 'POST',
    body: JSON.stringify({
      name: input.name,
      avatar_data_url: input.avatarDataUrl ?? null,
    }),
  })
}

export function updateProfile(profileId: number, input: UpdateUserProfileInput): Promise<UserProfile> {
  return apiRequest<UserProfile>(`/profiles/${profileId}`, {
    method: 'PATCH',
    body: JSON.stringify({
      name: input.name,
      avatar_data_url: input.avatarDataUrl,
    }),
  })
}

export function deleteProfile(profileId: number): Promise<DeleteUserProfileResponse> {
  return apiRequest<DeleteUserProfileResponse>(`/profiles/${profileId}`, {
    method: 'DELETE',
  })
}
