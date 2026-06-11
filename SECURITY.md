# Security Policy

## Alcance

Esta politica aplica a SupplierIntel, incluyendo:

- Backend FastAPI.
- Frontend React/Vite.
- App desktop Tauri.
- Sincronizacion Firebase/Firestore.
- Integraciones con Apify y EmailJS.
- Scripts de build y proteccion de entorno.

## Reportar vulnerabilidades

No abras issues publicos con secretos, tokens, credenciales o pasos de explotacion sensibles.

Para reportar un problema de seguridad, contacta al mantenedor del proyecto por un canal privado acordado por el equipo. Incluye:

- Descripcion clara del problema.
- Impacto esperado.
- Pasos minimos para reproducir.
- Version, commit o entorno afectado.
- Evidencia sin exponer datos privados de terceros.

## Secretos y credenciales

Nunca se deben commitear:

- `.env`
- `.env.enc`
- Tokens de Apify.
- Claves de EmailJS.
- JSON de Firebase service account.
- Bases SQLite con datos reales.
- Logs con datos personales o credenciales.

Las variables deben documentarse en `.env.example` con placeholders.

Para Firebase, usa:

```env
FIREBASE_CREDENTIALS_PATH=C:\ruta\segura\firebase-adminsdk.json
```

No pegues el contenido del JSON en codigo, documentacion o issues.

## App desktop

El modo desktop puede usar `.env.enc` cifrado con Windows DPAPI:

```powershell
python scripts/protect_desktop_env.py --source .env
```

Limitaciones importantes:

- `.env.enc` queda ligado al usuario/equipo que lo crea.
- Una app desktop no puede ocultar perfectamente claves que necesita usar localmente.
- Para proteger claves propias de forma fuerte, usa un backend remoto controlado por ti y no distribuyas esas claves en el instalador.

## Dependencias

Al actualizar dependencias:

- Revisar changelog si la dependencia toca seguridad, red, build o serializacion.
- Ejecutar pruebas relevantes.
- No introducir paquetes nuevos sin una razon clara.

Comandos recomendados:

```powershell
python -m pytest app/tests -q
cd frontend
npm run lint
npm run build
```

## Datos personales

SupplierIntel puede procesar nombres, emails, telefonos, proveedores y datos comerciales. Trata esos datos como sensibles:

- No subir bases reales.
- No incluir datos reales en capturas publicas.
- No compartir exports con informacion privada.
- Borrar datos de prueba antes de distribuir builds.

## Superficie de riesgo principal

| Area | Riesgo | Mitigacion |
| --- | --- | --- |
| `.env` | Filtracion de claves. | `.gitignore`, `.env.example`, revision antes de commit. |
| Firebase JSON | Acceso al proyecto remoto. | Guardar fuera del repo y usar `FIREBASE_CREDENTIALS_PATH`. |
| EmailJS | Envio no autorizado. | Limitar claves y revisar templates/permisos. |
| Apify | Uso indebido de token o costos. | Proteger token y validar actor. |
| Desktop | Claves inspeccionables localmente. | Preferir backend remoto para secretos propios. |
| SQLite | Datos privados locales. | No commitear bases ni exports reales. |

## Respuesta a incidentes

Si una clave se expone:

1. Revocar o rotar la clave inmediatamente.
2. Eliminarla del entorno afectado.
3. Revisar logs y uso de la clave.
4. Actualizar `.env.example` si faltaba documentacion.
5. Si estuvo en Git, asumir que quedo comprometida aunque se borre despues.
