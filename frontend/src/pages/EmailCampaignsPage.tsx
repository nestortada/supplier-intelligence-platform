import { Loader2, Mail, RefreshCcw, XCircle } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import { DEFAULT_EMAIL_SUBJECT } from '../constants/email'
import { clearSupplierDatabase, retrySupplierEmail, uploadSuppliersFile } from '../api/emailApi'
import CampaignCreator from '../components/CampaignCreator'
import CampaignLiveMonitor from '../components/CampaignLiveMonitor'
import EmailLogsTable from '../components/EmailLogsTable'
import KpiCards from '../components/KpiCards'
import { useCampaignPolling } from '../hooks/useCampaignPolling'
import { useEligibleSuppliers } from '../hooks/useEligibleSuppliers'
import { useEmailCampaigns } from '../hooks/useEmailCampaigns'
import { useEmailLogs } from '../hooks/useEmailLogs'
import { useRealtimeRefresh } from '../hooks/useRealtimeRefresh'
import { useSuppliers } from '../hooks/useSuppliers'
import { useToast } from '../hooks/useToast'
import type { EmailLog, EmailLogFilters, LaunchCampaignInput } from '../types/api'

const defaultLogFilters: EmailLogFilters = {
  status: 'all',
  lookupType: 'none',
  lookupValue: '',
}

const emailRealtimeEvents = ['email_campaign.created', 'email_campaign.updated', 'email.sent', 'webhook.received']

export default function EmailCampaignsPage() {
  const [supplierSearch, setSupplierSearch] = useState('')
  const [logFilters, setLogFilters] = useState<EmailLogFilters>(defaultLogFilters)
  const allLogFilters = useMemo<EmailLogFilters>(() => defaultLogFilters, [])

  const { addToast } = useToast()
  const eligibleSuppliers = useEligibleSuppliers()
  const suppliers = useSuppliers({
    search: supplierSearch,
    hasValidEmail: true,
    pageSize: 50,
  })
  const allLogs = useEmailLogs(allLogFilters)
  const filteredLogs = useEmailLogs(logFilters)
  const campaigns = useEmailCampaigns()
  const [cancelingCampaignId, setCancelingCampaignId] = useState<number | null>(null)
  const activeCampaign = useMemo(
    () => campaigns.campaigns.find((campaign) => campaign.status === 'in_progress') ?? null,
    [campaigns.campaigns],
  )

  useCampaignPolling(campaigns.campaigns, campaigns.updateCampaignStatus)

  const refreshEmailData = useCallback(() => {
    void allLogs.refresh()
    void filteredLogs.refresh()
    void campaigns.refresh()
    void eligibleSuppliers.refresh()
  }, [allLogs, campaigns, eligibleSuppliers, filteredLogs])

  useRealtimeRefresh(emailRealtimeEvents, refreshEmailData)

  const handleLaunch = useCallback(
    async (input: LaunchCampaignInput) => {
      if (input.target === 'specific' && input.supplierIds.length === 0) {
        addToast({
          tone: 'error',
          title: 'Selecciona proveedores',
          message: 'Necesitas elegir al menos un proveedor para lanzar una campaña específica.',
        })
        return
      }

      try {
        if (input.target === 'eligible') {
          await campaigns.launchEligibleCampaign(input)
        } else {
          await campaigns.launchSpecificCampaign(input)
        }

        addToast({
          tone: 'success',
          title: 'Campaña lanzada',
          message: 'El monitor se actualizará mientras el backend procesa los envíos.',
        })
        refreshEmailData()
      } catch (caught) {
        addToast({
          tone: 'error',
          title: 'No se pudo lanzar la campaña',
          message: caught instanceof Error ? caught.message : 'Intenta nuevamente.',
        })
        throw caught
      }
    },
    [addToast, campaigns, refreshEmailData],
  )

  const handleRetry = useCallback(
    async (log: EmailLog) => {
      if (!log.supplier_id) {
        addToast({
          tone: 'error',
          title: 'Proveedor no disponible',
          message: 'Este log no tiene un proveedor asociado para reintentar.',
        })
        return
      }

      try {
        const response = await retrySupplierEmail(log.supplier_id, DEFAULT_EMAIL_SUBJECT)
        if (!response.success) {
          throw new Error(response.error || 'El proveedor respondio con estado fallido.')
        }

        addToast({
          tone: 'success',
          title: 'Correo reenviado',
          message: `Proveedor ${response.supplier_id} procesado correctamente.`,
        })
        refreshEmailData()
      } catch (caught) {
        addToast({
          tone: 'error',
          title: 'No se pudo reintentar',
          message: caught instanceof Error ? caught.message : 'Intenta nuevamente.',
        })
      }
    },
    [addToast, refreshEmailData],
  )

  const handleUploadSuppliers = useCallback(
    async (file: File) => {
      try {
        const response = await uploadSuppliersFile(file)
        addToast({
          tone: 'success',
          title: 'Base cargada',
          message: `${response.suppliers_created} proveedores creados, ${response.duplicates_removed} duplicados omitidos.`,
        })
        refreshEmailData()
        void suppliers.refresh()
      } catch (caught) {
        addToast({
          tone: 'error',
          title: 'No se pudo subir el archivo',
          message: caught instanceof Error ? caught.message : 'Revisa el formato del Excel o CSV.',
        })
      }
    },
    [addToast, refreshEmailData, suppliers],
  )

  const handleClearDatabase = useCallback(async () => {
    try {
      const response = await clearSupplierDatabase()
      addToast({
        tone: 'success',
        title: 'Base eliminada',
        message: `${response.suppliers_deleted} proveedores y ${response.email_logs_deleted} logs eliminados.`,
      })
      refreshEmailData()
      void suppliers.refresh()
    } catch (caught) {
      addToast({
        tone: 'error',
        title: 'No se pudo eliminar la base',
        message: caught instanceof Error ? caught.message : 'Intenta nuevamente.',
      })
    }
  }, [addToast, refreshEmailData, suppliers])

  const handleCancelCampaign = useCallback(async () => {
    if (!activeCampaign) {
      return
    }

    setCancelingCampaignId(activeCampaign.campaign_id)
    try {
      await campaigns.cancelEmailCampaign(activeCampaign.campaign_id)
      addToast({
        tone: 'info',
        title: 'Cancelacion enviada',
        message: 'La campana se detendra antes del siguiente proveedor.',
      })
      refreshEmailData()
    } catch (caught) {
      addToast({
        tone: 'error',
        title: 'No se pudo cancelar',
        message: caught instanceof Error ? caught.message : 'Intenta nuevamente.',
      })
    } finally {
      setCancelingCampaignId(null)
    }
  }, [activeCampaign, addToast, campaigns, refreshEmailData])

  return (
    <div className="mx-auto max-w-[1440px] space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-sm font-semibold text-primary">
            <Mail className="h-4 w-4" />
            Outreach
          </div>
          <h1 className="font-display text-3xl font-semibold text-text md:text-4xl">Campañas de email</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted md:text-base">
            Gestiona comunicación con proveedores, monitorea entregas y audita cada envío desde una sola pantalla.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          {activeCampaign ? (
            <button
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-4 py-2.5 text-sm font-semibold text-danger transition hover:bg-danger/20 disabled:opacity-60"
              disabled={cancelingCampaignId === activeCampaign.campaign_id}
              onClick={() => void handleCancelCampaign()}
              type="button"
            >
              {cancelingCampaignId === activeCampaign.campaign_id ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}
              Cancelar campaÃ±a
            </button>
          ) : null}
          <button
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-outline/40 px-4 py-2.5 text-sm font-semibold text-muted transition hover:bg-white/5 hover:text-primary"
            onClick={refreshEmailData}
            type="button"
          >
            <RefreshCcw className="h-4 w-4" />
            Actualizar datos
          </button>
        </div>
      </header>

      <KpiCards loading={allLogs.loading} logs={allLogs.logs} />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <div className="xl:col-span-7">
          <CampaignCreator
            eligibleCount={eligibleSuppliers.total}
            eligibleLoading={eligibleSuppliers.loading}
            onClearDatabase={handleClearDatabase}
            executionActive={Boolean(activeCampaign)}
            onLaunch={handleLaunch}
            onSupplierSearchChange={setSupplierSearch}
            onUploadSuppliers={handleUploadSuppliers}
            supplierSearch={supplierSearch}
            suppliers={suppliers.suppliers}
            suppliersError={suppliers.error}
            suppliersLoading={suppliers.loading}
          />
        </div>
        <div className="xl:col-span-5">
          <CampaignLiveMonitor
            campaigns={campaigns.campaigns}
            error={campaigns.error}
            loading={campaigns.loading}
            onRefresh={campaigns.refresh}
          />
        </div>
      </div>

      <EmailLogsTable
        error={filteredLogs.error}
        filters={logFilters}
        loading={filteredLogs.loading}
        logs={filteredLogs.logs}
        onFiltersChange={setLogFilters}
        onRefresh={filteredLogs.refresh}
        onRetry={handleRetry}
      />
    </div>
  )
}
