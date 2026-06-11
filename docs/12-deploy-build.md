# Build, Docker y despliegue

## Backend local

```powershell
uvicorn app.main:app --reload
```

Produccion simple:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Frontend build

Desde `frontend`:

```powershell
npm install
npm run build
```

Salida:

```text
frontend/dist
```

## Docker Compose

Desde la raiz:

```powershell
docker compose up --build
```

Servicios:

- `backend`: FastAPI en puerto `8000`.
- `frontend`: Nginx sirviendo build React en puerto `80`.
- `db_data`: volumen persistente para SQLite.

El compose define:

```env
DATABASE_URL=sqlite:////app/data/supplier_intelligence.db
```

## Docker backend

Archivo:

```text
Dockerfile.backend
```

Construccion manual:

```powershell
docker build -f Dockerfile.backend -t supplierintel-backend .
docker run --env-file .env -p 8000:8000 supplierintel-backend
```

## Desktop Windows

Desde `frontend`:

```powershell
npm run tauri:build
```

Esto ejecuta:

1. `npm run desktop:backend`
2. `tauri build`

El backend se empaqueta como sidecar con PyInstaller.

## Archivos que no se deben distribuir

- `.env` con claves reales.
- JSON de Firebase service account.
- `supplier_intelligence.db` si contiene datos privados.
- Carpetas intermedias `dist`, `target` o `binaries` salvo que sepas exactamente que estas entregando.

## Checklist antes de entregar

1. `.env.example` actualizado.
2. README apunta a docs correctos.
3. `python -m pytest app/tests -q` pasa.
4. `npm run build` pasa.
5. Si es desktop, `npm run tauri:build` genera instalador.
6. No hay secretos reales en Git.
7. El instalador o Docker se prueba en una maquina limpia.
