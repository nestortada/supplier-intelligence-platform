# Vision general

SupplierIntel ayuda a evaluar proveedores y productos para tomar decisiones de compra con datos mas claros.

## Problema que resuelve

El flujo normal de evaluacion de proveedores suele mezclar hojas de calculo, busquedas manuales, emails y calculos financieros separados. SupplierIntel centraliza ese proceso:

- Importa proveedores desde Excel o CSV.
- Valida emails y datos basicos.
- Ejecuta campanas de contacto.
- Importa catalogos de productos.
- Enriquece productos con informacion de Amazon mediante Apify.
- Calcula margen, ROI, competencia, ventas estimadas y recomendacion.
- Muestra ranking de oportunidades.
- Exporta reportes Excel.

## Usuarios objetivo

- Compradores o analistas que revisan proveedores mayoristas.
- Equipos que necesitan priorizar productos para reventa.
- Usuarios que quieren trabajar localmente con opcion de sincronizacion.

## Modulos principales

| Modulo | Responsabilidad |
| --- | --- |
| Perfiles | Separar datos por usuario o contexto de trabajo. |
| Proveedores | Carga, validacion, consulta y eliminacion de proveedores. |
| Campanas email | Envio individual o masivo via EmailJS. |
| Catalogos | Carga de productos por proveedor. |
| Enriquecimiento | Consulta de datos de Amazon con Apify. |
| Analisis | Scoring financiero y recomendacion de compra. |
| Ranking | Vista ordenada de mejores oportunidades. |
| Seleccionados | Productos marcados para seguimiento o venta. |
| Dashboard | KPIs y resumen operativo. |
| Exportaciones | Archivos Excel para productos, proveedores y resumen. |
| Sync | Sincronizacion opcional con Firebase/Firestore. |
| Desktop | Empaquetado Windows con Tauri. |

## Principio local-first

La aplicacion funciona con SQLite como base local. Esto permite trabajar sin depender de una base remota para cada accion. Firebase se usa como sincronizacion opcional alrededor de SQLite, no como reemplazo del runtime local.
