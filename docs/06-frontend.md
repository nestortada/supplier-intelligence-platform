# Frontend

El frontend esta construido con React, TypeScript, Vite y Tailwind.

## Scripts

Desde `frontend`:

```powershell
npm install
npm run dev
npm run build
npm run lint
npm run preview
```

Desktop:

```powershell
npm run tauri:dev
npm run tauri:build
```

## Configuracion de API

El cliente HTTP esta en:

```text
frontend/src/api/http.ts
```

Usa:

```text
VITE_API_BASE_URL
```

Si no existe, usa `/api`.

Para desarrollo contra FastAPI local:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

## Perfil activo

El frontend guarda el perfil activo en `localStorage`:

```text
supplierintel.activeProfileId
```

Cada request agrega:

```http
X-Profile-Id: <id>
```

## Paginas

| Archivo | Funcion |
| --- | --- |
| `DashboardPage.tsx` | KPIs y resumen general. |
| `OpportunityRankingPage.tsx` | Ranking, filtros, seleccion y eliminacion masiva de productos. |
| `ProductAnalysisDetailPage.tsx` | Detalle financiero y datos Amazon. |
| `SelectedProductsPage.tsx` | Productos seleccionados para seguimiento/venta. |
| `EmailCampaignsPage.tsx` | Proveedores elegibles, campanas y logs. |
| `ProfileSelectionPage.tsx` | Seleccion/creacion de perfiles. |
| `SettingsPage.tsx` | Configuracion de perfil, scoring, fees y acciones destructivas. |

## Componentes importantes

| Archivo | Funcion |
| --- | --- |
| `AppShell.tsx` | Layout principal de navegacion. |
| `ProfileProvider.tsx` | Carga y expone perfil activo. |
| `CampaignCreator.tsx` | Crea campanas de email. |
| `CampaignLiveMonitor.tsx` | Monitorea campanas activas. |
| `ConfirmDialog.tsx` | Confirmaciones para acciones sensibles. |
| `KpiCards.tsx` | Tarjetas de metricas. |
| `ProgressBar.tsx` | Progreso de jobs/campanas. |
| `ToastProvider.tsx` | Notificaciones. |

## Hooks

| Hook | Uso |
| --- | --- |
| `useProfile` | Perfil activo. |
| `useSuppliers` | Proveedores. |
| `useEmailCampaigns` | Campanas. |
| `useCampaignPolling` | Polling de campanas. |
| `useRealtimeEvents` | WebSocket. |
| `useRealtimeRefresh` | Refresco por eventos. |
| `useToast` | Notificaciones. |

## Criterios de UI

- Las acciones largas deben mostrar progreso.
- Acciones conflictivas deben deshabilitarse mientras corre un job.
- Las acciones destructivas deben pedir confirmacion.
- El usuario debe poder cambiar de pagina y volver sin perder el estado del proceso.
- La fuente de verdad para jobs es el backend, no el estado temporal de React.
