# Instalacion y ejecucion

## Requisitos

Backend:

- Python 3.11 o superior.
- pip.
- Acceso a PowerShell en Windows.

Frontend:

- Node.js 22 o superior.
- npm.

Desktop Tauri:

- Rust/Cargo desde `https://rustup.rs`.
- Microsoft Visual Studio Build Tools con workload C++ desktop.
- WebView2 Runtime en Windows.

## Instalar backend

Desde la raiz del repo:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Ejecutar:

```powershell
uvicorn app.main:app --reload
```

Validar:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Instalar frontend

```powershell
cd frontend
npm install
npm run dev
```

Por defecto Vite abre en:

```text
http://127.0.0.1:5173
```

El frontend usa `VITE_API_BASE_URL`. Si no se define, usa `/api`.

Para desarrollo directo contra FastAPI:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

## Ejecutar con Docker Compose

```powershell
docker compose up --build
```

Servicios:

- Frontend: `http://localhost`
- Backend: `http://localhost:8000`
- Docs API: `http://localhost:8000/docs`

La base SQLite se persiste en el volumen Docker `db_data`.

## Ejecutar app desktop

Desde `frontend`:

```powershell
npm run tauri:dev
```

Para construir instalador:

```powershell
npm run tauri:build
```

Ver tambien [Desktop Tauri](10-desktop-tauri.md).
