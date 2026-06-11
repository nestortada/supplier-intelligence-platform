# API backend

Base local:

```text
http://127.0.0.1:8000
```

Documentacion interactiva:

```text
http://127.0.0.1:8000/docs
```

## Perfil activo

La mayoria de endpoints operan sobre un perfil. El perfil activo se envia con:

```http
X-Profile-Id: 1
```

Si no se envia, el backend crea o usa el perfil por defecto.

## Health

| Metodo | Ruta | Uso |
| --- | --- | --- |
| GET | `/health` | Verifica que el backend esta vivo. |

## Perfiles

| Metodo | Ruta | Uso |
| --- | --- | --- |
| GET | `/profiles` | Lista perfiles. |
| POST | `/profiles` | Crea perfil. |
| PATCH | `/profiles/{profile_id}` | Actualiza nombre o avatar del perfil activo. |
| DELETE | `/profiles/{profile_id}` | Elimina perfil activo y sus datos asociados. |

## Proveedores

| Metodo | Ruta | Uso |
| --- | --- | --- |
| POST | `/suppliers/upload` | Sube proveedores desde CSV/XLS/XLSX. |
| GET | `/suppliers` | Lista proveedores con filtros/paginacion. |
| GET | `/suppliers/{supplier_id}` | Consulta proveedor. |
| DELETE | `/suppliers/database` | Elimina proveedores y datos relacionados del perfil activo. |
| DELETE | `/suppliers/{supplier_id}` | Elimina un proveedor. |

Ejemplo:

```powershell
curl.exe -F "file=@proveedores_ejemplo.xlsx" http://127.0.0.1:8000/suppliers/upload
```

## Catalogos

| Metodo | Ruta | Uso |
| --- | --- | --- |
| GET | `/catalogs` | Lista catalogos/resumen. |
| POST | `/catalogs/upload` | Sube catalogo de productos para un proveedor. |

Ejemplo:

```powershell
curl.exe -F "supplier_name=Acme Supply" -F "file=@catalogo_productos_ejemplo.xlsx" http://127.0.0.1:8000/catalogs/upload
```

## Productos

| Metodo | Ruta | Uso |
| --- | --- | --- |
| GET | `/products` | Lista productos. |
| GET | `/products/ranking` | Ranking de oportunidades. |
| GET | `/products/selected` | Lista productos seleccionados. |
| PATCH | `/products/selected/performance` | Actualiza rendimiento de producto seleccionado. |
| DELETE | `/products/selected` | Limpia seleccionados sin borrar productos. |
| PATCH | `/products/{product_id}/selection` | Marca/desmarca producto. |
| POST | `/products/bulk-update-status` | Actualiza estado en lote. |
| POST | `/products/enrich-apify` | Crea job de enriquecimiento Apify. |
| POST | `/products/analyze` | Crea job de analisis. |
| GET | `/products/{product_id}/analysis` | Detalle de analisis. |
| GET | `/products/{product_id}` | Consulta producto. |
| DELETE | `/products/database` | Elimina productos, analisis y datos Amazon del perfil activo. |
| DELETE | `/products/{product_id}` | Elimina producto. |

Enriquecer pendientes:

```json
{
  "all_pending": true,
  "run_analysis_after": true
}
```

Analizar todos:

```json
{
  "all": true
}
```

Analizar seleccionados:

```json
{
  "product_ids": [1, 2, 3]
}
```

## Email y campanas

| Metodo | Ruta | Uso |
| --- | --- | --- |
| GET | `/emails/eligible-suppliers` | Lista proveedores aptos para campana. |
| POST | `/emails/send/{supplier_id}` | Envia email a un proveedor. |
| POST | `/emails/campaigns` | Crea campana para proveedores especificos. |
| POST | `/emails/campaigns/valid-suppliers` | Crea campana para todos los proveedores validos. |
| PATCH | `/emails/campaigns/{campaign_id}/cancel` | Cancela campana activa. |
| GET | `/emails/campaigns` | Lista campanas. |
| GET | `/emails/campaigns/{campaign_id}` | Estado de campana. |
| GET | `/emails/logs` | Logs de emails enviados/fallidos. |

## Jobs

| Metodo | Ruta | Uso |
| --- | --- | --- |
| GET | `/jobs` | Lista jobs del perfil activo. |
| GET | `/jobs/{job_id}` | Consulta job. |
| PATCH | `/jobs/{job_id}/cancel` | Solicita cancelacion. |

## Dashboard

| Metodo | Ruta | Uso |
| --- | --- | --- |
| GET | `/dashboard/summary` | KPIs generales. |
| GET | `/dashboard/top-opportunities` | Mejores oportunidades. |
| GET | `/dashboard/supplier-performance` | Rendimiento por proveedor. |

## Settings

| Metodo | Ruta | Uso |
| --- | --- | --- |
| GET | `/settings/scoring` | Obtiene pesos de scoring. |
| PUT | `/settings/scoring` | Actualiza pesos. |
| GET | `/settings/fees` | Obtiene fees/costos. |
| PUT | `/settings/fees` | Actualiza fees/costos. |

Los pesos de scoring deben incluir todas las claves esperadas y sumar `1.0`.

## Exportaciones

| Metodo | Ruta | Uso |
| --- | --- | --- |
| GET | `/exports` | Lista exportaciones disponibles. |
| GET | `/exports/products.xlsx` | Exporta productos. |
| GET | `/exports/recommended-products.xlsx` | Exporta recomendados. |
| GET | `/exports/suppliers.xlsx` | Exporta proveedores. |
| GET | `/exports/summary-report.xlsx` | Exporta resumen. |

## Sync

| Metodo | Ruta | Uso |
| --- | --- | --- |
| GET | `/sync/status` | Estado de sincronizacion. |
| POST | `/sync/run` | Ejecuta sincronizacion manual. |

## Realtime y webhooks

| Metodo | Ruta | Uso |
| --- | --- | --- |
| WS | `/ws/realtime` | WebSocket de eventos. |
| POST | `/webhooks/events` | Publica evento validado por secreto opcional. |

## Formato de error

Los errores controlados usan una forma similar a:

```json
{
  "success": false,
  "error": "Invalid file format",
  "details": "Only Excel and CSV files are allowed"
}
```
