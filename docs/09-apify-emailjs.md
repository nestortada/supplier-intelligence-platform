# Apify y EmailJS

## Apify

Apify se usa para enriquecer productos con datos de Amazon.

### Configuracion

```env
APIFY_TOKEN=your_apify_token
APIFY_ACTOR_ID=your_actor_id
APIFY_USER_ID=your_apify_user_id
APIFY_API_BASE_URL=https://api.apify.com/v2
```

### Codigo principal

| Archivo | Uso |
| --- | --- |
| `app/services/apify_service.py` | Construye input, llama al actor y mapea resultados. |
| `app/routers/products.py` | Crea jobs de enriquecimiento. |
| `app/models/amazon_data.py` | Guarda datos Amazon. |

### Flujo

1. El usuario llama `POST /products/enrich-apify`.
2. El backend selecciona productos por `all_pending` o `product_ids`.
3. Se crea un `BackgroundJob`.
4. Por producto, `build_apify_input` arma el payload.
5. `ApifyService` inicia actor y lee dataset.
6. El resultado se mapea a `AmazonProductData`.
7. El job publica progreso y finaliza.

### Errores comunes

| Error | Causa probable | Solucion |
| --- | --- | --- |
| `APIFY_TOKEN is required` | Falta token. | Configurar `.env`. |
| `APIFY_ACTOR_ID is required` | Falta actor. | Configurar actor correcto. |
| Respuesta vacia | Actor no encontro producto. | Revisar UPC/EAN/SKU/nombre. |
| Timeout o red | Sin acceso externo o actor lento. | Probar token/actor fuera del sandbox o aumentar espera. |

### Pruebas

```powershell
python -m pytest app/tests/test_apify_service.py -q
python -m pytest app/tests/test_apify_api.py -q
```

## EmailJS

EmailJS se usa para enviar emails a proveedores.

### Configuracion

```env
EMAILJS_SERVICE_ID=your_emailjs_service_id
EMAILJS_TEMPLATE_ID=your_emailjs_template_id
EMAILJS_PUBLIC_KEY=your_emailjs_public_key
EMAILJS_PRIVATE_KEY=your_emailjs_private_key
EMAILJS_API_URL=https://api.emailjs.com/api/v1.0/email/send
```

Datos usados en templates:

```env
MY_NAME=Your Name
MY_EMAIL=you@example.com
MY_PHONE=0000000000
```

### Codigo principal

| Archivo | Uso |
| --- | --- |
| `app/services/emailjs_service.py` | Cliente HTTP a EmailJS. |
| `app/routers/emails.py` | Campanas, envio individual y logs. |
| `app/models/email_campaign.py` | Campanas y logs. |

### Flujo

1. El usuario consulta proveedores elegibles.
2. Crea campana o envia a un proveedor.
3. El backend arma parametros de template.
4. EmailJS recibe JSON.
5. El resultado se guarda en `EmailLog`.
6. La campana actualiza contadores.

### Reglas de elegibilidad

Un proveedor debe tener email valido y no estar marcado como no enviable por las reglas del backend.

### Errores comunes

| Error | Causa probable | Solucion |
| --- | --- | --- |
| Template ID not found | `template_id` invalido. | Usar `EMAILJS_TEMPLATE_ID` real. |
| 403 | Access token o permisos. | Revisar private key; el backend reintenta sin token si aplica. |
| Sin proveedores elegibles | Emails invalidos o duplicados. | Revisar carga de proveedores. |

### Pruebas

```powershell
python -m pytest app/tests/test_email_helpers.py -q
python -m pytest app/tests/test_emailjs_service.py -q
python -m pytest app/tests/test_email_campaigns_api.py -q
```
