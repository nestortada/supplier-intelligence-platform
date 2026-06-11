# Contributing

Gracias por contribuir a SupplierIntel. Este proyecto combina backend FastAPI, frontend React/Vite, app desktop Tauri y sincronizacion opcional con Firebase, asi que los cambios deben mantenerse pequenos, verificables y alineados con el flujo real de la aplicacion.

## Requisitos locales

- Python 3.11 o superior.
- Node.js 22 o superior.
- npm.
- Rust/Cargo y Visual Studio Build Tools si trabajas en desktop Tauri.

## Preparar el entorno

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

## Flujo de trabajo

1. Mantener los cambios enfocados en un problema o feature.
2. Revisar la documentacion existente antes de cambiar contratos.
3. Actualizar tests cuando cambie comportamiento observable.
4. Actualizar `README.md` o `docs/` cuando cambien comandos, endpoints, variables o flujos.
5. No incluir secretos, bases locales ni artefactos de build.

## Estilo de codigo

Backend:

- Usar FastAPI routers en `app/routers`.
- Mantener modelos SQLAlchemy en `app/models`.
- Mantener schemas Pydantic en `app/schemas`.
- Poner integraciones y logica de negocio en `app/services`.
- Mantener SQLite como fuente runtime local; Firebase es sincronizacion opcional.

Frontend:

- Usar TypeScript.
- Reutilizar `frontend/src/api/http.ts` para requests.
- Respetar `X-Profile-Id` para datos por perfil.
- Mantener jobs largos como procesos del backend, no como estado temporal de React.
- Usar confirmacion para acciones destructivas.

## Tests

Suite completa:

```powershell
python -m pytest app/tests -q
```

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

Pruebas enfocadas recomendadas:

```powershell
python -m pytest app/tests/test_sync_service.py -q
python -m pytest app/tests/test_apify_service.py -q
python -m pytest app/tests/test_email_campaigns_api.py -q
python -m pytest app/tests/test_product_analysis_api.py -q
```

## Commits y pull requests

Antes de abrir un PR:

- Explica que cambio y por que.
- Incluye los comandos de verificacion ejecutados.
- Menciona migraciones, cambios de `.env.example` o cambios de endpoints.
- Adjunta capturas si cambias UI.
- No mezcles refactors grandes con features o fixes pequenos.

## Datos y secretos

No hacer commit de:

- `.env`
- `.env.enc`
- JSON de Firebase service account.
- `supplier_intelligence.db`
- Archivos `.db`, `.sqlite`, `.sqlite3`
- `frontend/dist`, `dist`, `build`, `target`, `node_modules`

Usa `.env.example` para documentar variables nuevas sin valores reales.
