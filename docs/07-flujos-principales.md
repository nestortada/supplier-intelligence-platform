# Flujos principales

## 1. Perfil

1. El usuario entra a la aplicacion.
2. El backend crea un perfil por defecto si no existe.
3. El frontend guarda el perfil activo en `localStorage`.
4. Las requests usan `X-Profile-Id`.

Endpoints:

- `GET /profiles`
- `POST /profiles`
- `PATCH /profiles/{profile_id}`
- `DELETE /profiles/{profile_id}`

## 2. Carga de proveedores

1. El usuario sube `.csv`, `.xls` o `.xlsx`.
2. El backend mapea columnas y valida emails.
3. Se eliminan duplicados por email normalizado.
4. Los proveedores quedan asociados al perfil activo.

Endpoint:

```text
POST /suppliers/upload
```

Archivo de ejemplo:

```text
proveedores_ejemplo.xlsx
```

## 3. Campana de email

1. El frontend consulta proveedores elegibles.
2. El usuario crea campana.
3. El backend crea `EmailCampaign`.
4. El envio corre como tarea de backend.
5. Cada resultado queda en `EmailLog`.
6. La campana se puede consultar o cancelar.

Endpoints:

- `GET /emails/eligible-suppliers`
- `POST /emails/campaigns`
- `POST /emails/campaigns/valid-suppliers`
- `GET /emails/campaigns/{campaign_id}`
- `PATCH /emails/campaigns/{campaign_id}/cancel`
- `GET /emails/logs`

## 4. Carga de catalogo

1. El usuario selecciona proveedor o escribe nombre.
2. El backend crea o resuelve el proveedor.
3. El archivo se parsea con mapeo flexible de columnas.
4. Los productos quedan en estado pendiente de analisis.

Endpoint:

```text
POST /catalogs/upload
```

Archivos de ejemplo:

- `catalogo_productos_ejemplo.xlsx`
- `catalogo_productos_amazon_ejemplo.xlsx`

## 5. Enriquecimiento Apify

1. El usuario ejecuta enriquecimiento.
2. El backend crea un `BackgroundJob`.
3. Para cada producto, se construye input para Apify.
4. Se guarda informacion Amazon en `amazon_product_data`.
5. El job reporta progreso.
6. Opcionalmente se encadena analisis con `run_analysis_after`.

Endpoint:

```text
POST /products/enrich-apify
```

Payload comun:

```json
{
  "all_pending": true,
  "run_analysis_after": true
}
```

## 6. Analisis de productos

1. El usuario analiza todos o una seleccion.
2. El backend crea job de analisis.
3. Se aplican fees y pesos configurados.
4. Se calcula recomendacion.
5. Se actualiza ranking.

Endpoint:

```text
POST /products/analyze
```

## 7. Ranking y seleccion

1. El usuario revisa `/products/ranking`.
2. Puede filtrar, ver detalle y seleccionar productos.
3. Los productos seleccionados aparecen en la pagina de seleccionados.
4. Puede actualizar rendimiento o limpiar seleccionados.
5. Puede eliminar todos los productos creados desde ranking.

Endpoints:

- `GET /products/ranking`
- `GET /products/{product_id}/analysis`
- `PATCH /products/{product_id}/selection`
- `GET /products/selected`
- `DELETE /products/database`

## 8. Exportacion

1. El usuario descarga reportes Excel.
2. Los reportes se generan desde SQLite filtrando el perfil activo.

Endpoints:

- `GET /exports/products.xlsx`
- `GET /exports/recommended-products.xlsx`
- `GET /exports/suppliers.xlsx`
- `GET /exports/summary-report.xlsx`

## 9. Sincronizacion

1. Cambios locales generan outbox.
2. `/sync/run` empuja cambios locales y trae cambios remotos.
3. Si Firebase esta habilitado, tambien existe sync periodico.

Endpoints:

- `GET /sync/status`
- `POST /sync/run`
