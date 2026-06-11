# Testing

## Suite completa

Desde la raiz del repo:

```powershell
python -m pytest app/tests -q
```

## Pruebas por area

Backend API y jobs:

```powershell
python -m pytest app/tests/test_dashboard_jobs_api.py -q
python -m pytest app/tests/test_product_analysis_api.py -q
python -m pytest app/tests/test_catalogs_api.py -q
```

Proveedores, perfiles y settings:

```powershell
python -m pytest app/tests/test_profiles_scope.py -q
python -m pytest app/tests/test_settings_api.py -q
```

Apify:

```powershell
python -m pytest app/tests/test_apify_service.py -q
python -m pytest app/tests/test_apify_api.py -q
```

EmailJS:

```powershell
python -m pytest app/tests/test_email_helpers.py -q
python -m pytest app/tests/test_emailjs_service.py -q
python -m pytest app/tests/test_email_campaigns_api.py -q
```

Exportaciones:

```powershell
python -m pytest app/tests/test_export_service.py -q
```

Sync Firebase:

```powershell
python -m pytest app/tests/test_sync_service.py -q
```

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

## Cuando correr cada cosa

| Cambio | Prueba minima |
| --- | --- |
| Router FastAPI | Test API del modulo y suite completa si toca modelos compartidos. |
| Scoring o fees | `test_product_scoring_engine.py` y `test_settings_api.py`. |
| Apify | Tests de servicio y API de Apify. |
| EmailJS | Helpers, servicio y campanas. |
| Sync | `test_sync_service.py` y suite completa. |
| Frontend | `npm run lint` y `npm run build`. |
| Desktop | `npm run tauri:dev` o `npm run tauri:build`. |

## Notas

- Algunas pruebas de servicios externos usan mocks; no reemplazan una validacion real con credenciales.
- Si `npm run build` falla con `spawn EPERM` en un entorno restringido, repite la prueba fuera del sandbox.
- Antes de cambios grandes en persistencia o sync, corre primero la prueba enfocada y luego la suite completa.
