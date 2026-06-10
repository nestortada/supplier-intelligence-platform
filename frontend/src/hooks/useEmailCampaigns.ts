import { useCallback, useEffect, useState } from 'react'
import { cancelCampaign, createEligibleCampaign, createSpecificCampaign, fetchCampaigns } from '../api/emailApi'
import type { CampaignStatus, CampaignSummary, CreateCampaignInput } from '../types/api'

function campaignFromStatus(
  status: CampaignStatus,
  subject: string,
  templateId: string | null,
): CampaignSummary {
  const now = new Date().toISOString()
  return {
    ...status,
    subject,
    template_id: templateId,
    created_at: now,
    updated_at: now,
  }
}

function upsertCampaign(items: CampaignSummary[], campaign: CampaignSummary): CampaignSummary[] {
  const remaining = items.filter((item) => item.campaign_id !== campaign.campaign_id)
  return [campaign, ...remaining].sort((left, right) => right.campaign_id - left.campaign_id)
}

export function useEmailCampaigns() {
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadCampaigns = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchCampaigns()
      setCampaigns(response.items)
      setTotal(response.total)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudieron cargar las campañas.')
    } finally {
      setLoading(false)
    }
  }, [])

  const updateCampaignStatus = useCallback((status: CampaignStatus) => {
    setCampaigns((current) =>
      current.map((campaign) =>
        campaign.campaign_id === status.campaign_id
          ? {
              ...campaign,
              ...status,
              updated_at: new Date().toISOString(),
            }
          : campaign,
      ),
    )
  }, [])

  const launchSpecificCampaign = useCallback(
    async (input: CreateCampaignInput) => {
      const status = await createSpecificCampaign(input)
      const campaign = campaignFromStatus(status, input.subject, input.templateId)
      setCampaigns((current) => upsertCampaign(current, campaign))
      setTotal((current) => Math.max(current, campaigns.length + 1))
      void loadCampaigns()
      return status
    },
    [campaigns.length, loadCampaigns],
  )

  const launchEligibleCampaign = useCallback(
    async (input: CreateCampaignInput) => {
      const status = await createEligibleCampaign(input)
      const campaign = campaignFromStatus(status, input.subject, input.templateId)
      setCampaigns((current) => upsertCampaign(current, campaign))
      setTotal((current) => Math.max(current, campaigns.length + 1))
      void loadCampaigns()
      return status
    },
    [campaigns.length, loadCampaigns],
  )

  const cancelEmailCampaign = useCallback(async (campaignId: number) => {
    const status = await cancelCampaign(campaignId)
    updateCampaignStatus(status)
    void loadCampaigns()
    return status
  }, [loadCampaigns, updateCampaignStatus])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadCampaigns()
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [loadCampaigns])

  return {
    campaigns,
    total,
    loading,
    error,
    refresh: loadCampaigns,
    updateCampaignStatus,
    launchSpecificCampaign,
    launchEligibleCampaign,
    cancelEmailCampaign,
  }
}
