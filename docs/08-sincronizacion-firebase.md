# Sincronizacion Firebase

SupplierIntel usa un modelo local-first:

- SQLite es la base usada por la aplicacion en tiempo de ejecucion.
- Firestore es un espejo remoto opcional.
- El backend sincroniza cambios cuando `FIREBASE_ENABLED=true`.

## Configuracion

En `.env`:

```env
FIREBASE_ENABLED=true
FIREBASE_CREDENTIALS_PATH=C:\ruta\segura\firebase-adminsdk.json
FIREBASE_PROJECT_ID=tu-project-id
FIREBASE_NAMESPACE=default
FIREBASE_SYNC_INTERVAL_SECONDS=60
```

No pegues el contenido del JSON de credenciales dentro del codigo. Usa una ruta local.

## Componentes

| Archivo | Uso |
| --- | --- |
| `app/services/firestore_sync_client.py` | Cliente Firestore. |
| `app/services/sync_service.py` | Orquestacion push/pull. |
| `app/core/sync_events.py` | Captura cambios locales en SQLAlchemy. |
| `app/core/sync_schema.py` | Asegura columnas/tablas de sync. |
| `app/models/sync.py` | Modelos `SyncOutbox` y `SyncState`. |
| `app/routers/sync.py` | Endpoints de sync. |

## Tablas y campos

| Elemento | Funcion |
| --- | --- |
| `sync_outbox` | Cola de cambios locales pendientes. |
| `sync_state` | Estado del ultimo sync. |
| `sync_id` | Identificador estable por entidad. |
| `sync_updated_at` | Marca de ultima actualizacion. |
| `sync_deleted_at` | Marca de eliminacion/tombstone. |

## Estrategia de conflicto

La estrategia es "last change wins":

- Si el cambio local es mas nuevo, se empuja a Firestore.
- Si el cambio remoto es mas nuevo, se aplica en SQLite.
- Las eliminaciones via tombstone tambien se comparan por fecha.

## Endpoints

```http
GET /sync/status
POST /sync/run
```

`/sync/status` indica si esta habilitado, namespace y estado general.

`/sync/run` ejecuta una pasada manual de push/pull.

## Sync periodico

En `app/main.py`, si `FIREBASE_ENABLED=true`, se crea un loop al iniciar FastAPI. El intervalo minimo efectivo es 5 segundos y se controla con:

```env
FIREBASE_SYNC_INTERVAL_SECONDS=60
```

## Pruebas recomendadas

```powershell
python -m pytest app/tests/test_sync_service.py -q
```

Luego correr suite completa:

```powershell
python -m pytest app/tests -q
```
