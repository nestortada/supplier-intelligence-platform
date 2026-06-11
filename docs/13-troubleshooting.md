# Troubleshooting

## Backend no arranca

Revisa:

- Entorno virtual activo.
- Dependencias instaladas con `pip install -r requirements.txt`.
- `.env` valido.
- Puerto `8000` libre.

Validacion:

```powershell
uvicorn app.main:app --reload
```

## Frontend no conecta al backend

Revisa:

- Backend corriendo en `http://127.0.0.1:8000`.
- `VITE_API_BASE_URL` correcto.
- `CORS_ORIGINS` incluye el origen de Vite.

Ejemplo:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

## Swagger funciona pero frontend no

Probable causa: el frontend esta llamando `/api` y no al backend directo.

Solucion en desarrollo:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

## EmailJS devuelve template no encontrado

Causa probable:

- `EMAILJS_TEMPLATE_ID` incorrecto.
- Se envio un placeholder desde Swagger.

Solucion:

- Configurar template real en `.env`.
- Probar `POST /emails/send/{supplier_id}` con proveedor valido.
- Revisar `GET /emails/logs`.

## EmailJS devuelve 403

Causa probable:

- Private key invalida.
- Template configurado para otro tipo de acceso.

El backend reintenta sin `accessToken` cuando aplica. Si sigue fallando, revisa permisos en EmailJS.

## Apify no retorna datos

Revisa:

- `APIFY_TOKEN`.
- `APIFY_ACTOR_ID`.
- Que el actor acepte el payload actual.
- Que el producto tenga UPC/EAN/SKU/nombre suficiente.

Prueba enfocada:

```powershell
python -m pytest app/tests/test_apify_service.py -q
```

## Firebase no sincroniza

Revisa:

- `FIREBASE_ENABLED=true`.
- `FIREBASE_CREDENTIALS_PATH` apunta a un JSON existente.
- `FIREBASE_PROJECT_ID` correcto.
- Reglas/permisos de service account.
- Namespace esperado.

Validacion:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/sync/status
Invoke-RestMethod -Method Post http://127.0.0.1:8000/sync/run
```

## Datos mezclados entre usuarios

Revisa que el frontend o cliente envie:

```http
X-Profile-Id: <id>
```

Sin ese header, el backend usa el perfil por defecto.

## Jobs quedan corriendo o no avanzan

Revisa:

- `GET /jobs`
- `GET /jobs/{job_id}`
- `PATCH /jobs/{job_id}/cancel`

Para campanas:

- `GET /emails/campaigns`
- `PATCH /emails/campaigns/{campaign_id}/cancel`

## SQLite bloqueado

Puede pasar si hay varios procesos usando la misma base.

Soluciones:

- Cerrar servidores duplicados.
- Evitar abrir la DB con herramientas externas durante ejecucion.
- En Docker, usar el volumen configurado.

## Build frontend falla con `spawn EPERM`

En entornos restringidos puede fallar el build de Vite por permisos. Repite:

```powershell
cd frontend
npm run build
```

en una terminal normal de Windows.

## `.env.enc` no funciona en otro equipo

Es esperado. El cifrado DPAPI queda ligado al usuario/equipo que genero el archivo.

Cada usuario debe generar su propio `.env.enc`:

```powershell
python scripts/protect_desktop_env.py --source .env
```
