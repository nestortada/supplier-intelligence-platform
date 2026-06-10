import { useEffect } from 'react'
import { fetchCampaignStatus } from '../api/emailApi'
import type { CampaignStatus, CampaignSummary } from '../types/api'

type UpdateCampaignStatus = (status: CampaignStatus) => void

export function useCampaignPolling(campaigns: CampaignSummary[], onUpdate: UpdateCampaignStatus) {
  useEffect(() => {
    const activeCampaigns = campaigns.filter((campaign) => campaign.status === 'in_progress')

    if (activeCampaigns.length === 0) {
      return undefined
    }

    let cancelled = false

    const pollCampaigns = async () => {
      const statuses = await Promise.allSettled(
        activeCampaigns.map((campaign) => fetchCampaignStatus(campaign.campaign_id)),
      )

      if (cancelled) {
        return
      }

      statuses.forEach((result) => {
        if (result.status === 'fulfilled') {
          onUpdate(result.value)
        }
      })
    }

    void pollCampaigns()
    const interval = window.setInterval(() => {
      void pollCampaigns()
    }, 2000)

    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [campaigns, onUpdate])
}
