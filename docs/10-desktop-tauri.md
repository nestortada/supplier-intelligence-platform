# Desktop Tauri

La app desktop empaqueta el frontend React/Vite dentro de Tauri y ejecuta el backend FastAPI como sidecar local.

El backend desktop escucha por defecto en:

```text
127.0.0.1:18765
```

## Requisitos en Windows

- Node.js 22 o superior.
- Python 3.11 o superior.
- Rust/Cargo instalado desde `https://rustup.rs`.
- Microsoft Visual Studio Build Tools con workload C++ desktop.
- WebView2 Runtime en equipos destino, o instalador Tauri con bootstrapper.

## Desarrollo

Desde `frontend`:

```powershell
npm install
npm run tauri:dev
```

`tauri:dev` compila primero el backend FastAPI con PyInstaller y luego abre la ventana Tauri.

## Build de instalador Windows

Desde `frontend`:

```powershell
npm run tauri:build
```

Los instaladores quedan en:

```text
frontend/src-tauri/target/release/bundle/
```

Artefactos comunes:

```text
frontend/src-tauri/target/release/bundle/nsis/SupplierIntel_0.1.0_x64-setup.exe
frontend/src-tauri/target/release/bundle/msi/SupplierIntel_0.1.0_x64_en-US.msi
```

## Backend sidecar

Script:

```text
scripts/build_desktop_backend.ps1
```

Hace lo siguiente:

1. Ejecuta PyInstaller sobre `app/desktop_server.py`.
2. Genera `dist/supplierintel-backend.exe`.
3. Copia el ejecutable a `frontend/src-tauri/binaries`.
4. Usa el target triple de Rust para que Tauri encuentre el sidecar.

## Datos locales

Cuando `SUPPLIERINTEL_DESKTOP=1`, el backend usa:

```text
%APPDATA%\SupplierIntel\supplier_intelligence.db
%APPDATA%\SupplierIntel\app_runtime_settings.json
%APPDATA%\SupplierIntel\.env
%APPDATA%\SupplierIntel\.env.enc
```

Esto evita escribir la base SQLite dentro de la carpeta de instalacion.

## Secretos y API keys

No distribuyas tus API keys dentro del instalador ni dentro del repo.

En una app desktop no existe una forma perfecta de ocultar secretos que la app necesita usar localmente. Un usuario avanzado podria inspeccionar procesos, memoria o binarios. Para proteger claves propias de forma fuerte, mueve esas llamadas a un backend remoto controlado por ti.

Para proteger contra lectura casual en el computador del usuario, el backend desktop soporta `.env.enc` cifrado con Windows DPAPI. Ese archivo queda ligado al usuario de Windows que lo creo.

Crear `.env.enc`:

```powershell
python scripts/protect_desktop_env.py --source .env
```

O:

```powershell
scripts\protect_desktop_env.ps1 --source .env
```

Importante: un `.env.enc` creado en tu computador no sirve para otro usuario/computador.

## Recomendacion de distribucion

- Usa el `.exe` NSIS para usuarios normales.
- Usa `.msi` para despliegue administrado en empresa.
- No envies `dist`, `target`, `binaries` ni `.env`.
- No empaquetes claves privadas si los usuarios no deben verlas.
