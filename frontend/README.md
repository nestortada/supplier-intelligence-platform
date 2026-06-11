# SupplierIntel Frontend

Frontend de SupplierIntel construido con React, TypeScript, Vite y Tailwind.

## Requisitos

- Node.js 22 o superior.
- npm.
- Backend FastAPI corriendo si se trabaja en modo desarrollo.

## Instalacion

```powershell
npm install
```

## Desarrollo

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

Vite abre normalmente en:

```text
http://127.0.0.1:5173
```

Si `VITE_API_BASE_URL` no se define, el cliente usa `/api`. Ese modo sirve cuando Nginx o un proxy redirige `/api` al backend.

## Scripts

| Script | Uso |
| --- | --- |
| `npm run dev` | Servidor Vite con HMR. |
| `npm run build` | TypeScript build y Vite production build. |
| `npm run lint` | ESLint. |
| `npm run preview` | Sirve el build localmente. |
| `npm run desktop:backend` | Compila el backend sidecar con PyInstaller. |
| `npm run tauri:dev` | Ejecuta app desktop en desarrollo. |
| `npm run tauri:build` | Genera instalador desktop. |

## Estructura

| Ruta | Uso |
| --- | --- |
| `src/pages` | Paginas principales. |
| `src/components` | Componentes reutilizables. |
| `src/api` | Clientes HTTP por dominio. |
| `src/hooks` | Hooks de datos, polling y realtime. |
| `src/contexts` | Contextos globales. |
| `src/types` | Tipos TypeScript. |
| `src-tauri` | Configuracion y codigo Tauri. |

## Perfil activo

El frontend guarda el perfil activo en:

```text
supplierintel.activeProfileId
```

El cliente HTTP agrega ese valor como:

```http
X-Profile-Id: <id>
```

## Mas documentacion

Ver:

- `../docs/06-frontend.md`
- `../docs/10-desktop-tauri.md`
- `../docs/05-backend-api.md`
