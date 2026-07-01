# Configuracion y variables de entorno


La configuracion local se toma de `.env`. Crea ese archivo desde `.env.example`.

```powershell
Copy-Item .env.example .env
```

No subas `.env` ni claves reales al repositorio.

## Variables generales

| Variable | Uso |
| --- | --- |
| `APP_NAME` | Nombre mostrado por FastAPI y `/health`. |
| `DATABASE_URL` | Conexion SQLAlchemy. Por defecto SQLite local. |
| `MAX_UPLOAD_SIZE_MB` | Limite de subida de archivos. |
| `RATE_LIMIT_REQUESTS` | Cantidad maxima de requests por ventana. |
| `RATE_LIMIT_WINDOW_SECONDS` | Ventana del rate limit. |
| `CORS_ORIGINS` | Origenes permitidos para el frontend. |
| `WEBHOOK_SECRET` | Secreto opcional para `/webhooks/events`. |

## EmailJS

| Variable | Uso |
| --- | --- |
| `EMAILJS_SERVICE_ID` | Service ID de EmailJS. |
| `EMAILJS_TEMPLATE_ID` | Template por defecto. |
| `EMAILJS_PUBLIC_KEY` | Public key o user ID. |
| `EMAILJS_PRIVATE_KEY` | Access token privado. |
| `EMAILJS_API_URL` | Endpoint de envio EmailJS. |

El backend envia JSON a EmailJS. Si EmailJS responde `403` y hay `EMAILJS_PRIVATE_KEY`, el servicio reintenta sin `accessToken` para soportar templates publicos.

## Apify

| Variable | Uso |
| --- | --- |
| `APIFY_TOKEN` | Token de Apify. |
| `APIFY_ACTOR_ID` | Actor de detalles/busqueda Amazon usado para enriquecer productos. |
| `APIFY_TRACKING_ACTOR_ID` | Actor de tracking/precios Amazon usado para historial, buybox, ofertas y variantes. |
| `APIFY_USER_ID` | Identificador de usuario, si se requiere. |
| `APIFY_API_BASE_URL` | Base URL de Apify. |

Los actores deben aceptar los payloads construidos por `app/services/apify_service.py`.

## Datos del remitente

| Variable | Uso |
| --- | --- |
| `MY_NAME` | Nombre usado en templates de email. |
| `MY_EMAIL` | Email de contacto usado en templates. |
| `MY_PHONE` | Telefono de contacto usado en templates. |

## Firebase/Firestore

| Variable | Uso |
| --- | --- |
| `FIREBASE_ENABLED` | Activa o desactiva sincronizacion. |
| `FIREBASE_CREDENTIALS_PATH` | Ruta local al JSON de service account. |
| `FIREBASE_PROJECT_ID` | Project ID de Firebase. |
| `FIREBASE_NAMESPACE` | Namespace para separar ambientes/datos. |
| `FIREBASE_SYNC_INTERVAL_SECONDS` | Intervalo del sync periodico. |

Recomendacion: guarda el JSON de credenciales fuera del repo o dejalo ignorado por Git, y apunta a el con `FIREBASE_CREDENTIALS_PATH`.

## Desktop

Cuando `SUPPLIERINTEL_DESKTOP=1`, el backend usa rutas bajo:

```text
%APPDATA%\SupplierIntel
```

Archivos esperados:

- `supplier_intelligence.db`
- `app_runtime_settings.json`
- `.env`
- `.env.enc`

Para cifrar un `.env` local con DPAPI:

```powershell
python scripts/protect_desktop_env.py --source .env
```
