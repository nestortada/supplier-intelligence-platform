# SupplierIntel

SupplierIntel es una plataforma local-first para gestionar proveedores mayoristas, importar catalogos, enriquecer productos con datos de Amazon, calcular oportunidades de compra, enviar campanas de contacto por email y exportar resultados en Excel.

El proyecto incluye:

- Backend FastAPI con SQLAlchemy y SQLite.
- Frontend React, TypeScript, Vite y Tailwind.
- App desktop Windows con Tauri y backend FastAPI como sidecar.
- Sincronizacion opcional con Firebase/Firestore.
- Integraciones con Apify para enriquecimiento de productos y EmailJS para campanas.
- Pruebas automatizadas para APIs, servicios, scoring, sincronizacion y exportacion.

## Inicio rapido

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

API local:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend local:

```text
http://127.0.0.1:5173
```

Si el backend no esta detras de `/api`, define `VITE_API_BASE_URL` antes de ejecutar Vite.

## Flujo principal

1. Crear o seleccionar un perfil.
2. Subir proveedores desde Excel o CSV.
3. Revisar proveedores elegibles y enviar campanas con EmailJS.
4. Subir catalogos de productos por proveedor.
5. Enriquecer productos pendientes con Apify.
6. Ejecutar analisis de oportunidades.
7. Revisar ranking, detalle financiero y productos seleccionados.
8. Exportar reportes Excel.
9. Sincronizar con Firebase si esta habilitado.

## Documentacion

- [Vision general](docs/01-overview.md)
- [Instalacion y ejecucion](docs/02-instalacion.md)
- [Configuracion y variables de entorno](docs/03-configuracion-env.md)
- [Arquitectura](docs/04-arquitectura.md)
- [API backend](docs/05-backend-api.md)
- [Frontend](docs/06-frontend.md)
- [Flujos principales](docs/07-flujos-principales.md)
- [Sincronizacion Firebase](docs/08-sincronizacion-firebase.md)
- [Apify y EmailJS](docs/09-apify-emailjs.md)
- [Desktop Tauri](docs/10-desktop-tauri.md)
- [Testing](docs/11-testing.md)
- [Build, Docker y despliegue](docs/12-deploy-build.md)
- [Troubleshooting](docs/13-troubleshooting.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## Comandos utiles

```powershell
# Backend
uvicorn app.main:app --reload
python -m pytest app/tests -q

# Frontend
cd frontend
npm run dev
npm run build
npm run lint

# Desktop Windows
cd frontend
npm run tauri:dev
npm run tauri:build

# Docker
docker compose up --build
```

## Datos de ejemplo

El repo incluye archivos de prueba para validar los flujos:

- `proveedores_ejemplo.xlsx`
- `catalogo_productos_ejemplo.xlsx`
- `catalogo_productos_amazon_ejemplo.xlsx`
- `catalogo_productos_prueba_apify.xlsx`

## Seguridad

No subas secretos reales al repo. Configura claves en `.env` local o en el archivo cifrado de escritorio `.env.enc`. Para Firebase usa `FIREBASE_CREDENTIALS_PATH` apuntando al JSON local; no pegues el contenido del JSON dentro del codigo.

## Estado tecnico

SQLite es la fuente de datos local de la aplicacion. Firebase/Firestore funciona como espejo opcional para sincronizar perfiles y datos cuando esta habilitado. Los trabajos largos de Apify, analisis y campanas se ejecutan en backend y pueden consultarse o cancelarse desde los endpoints de jobs/campanas.
