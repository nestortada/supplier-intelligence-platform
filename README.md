# Supplier Intelligence Platform Backend

Backend MVP for finding wholesale suppliers, importing product catalogs, enriching products with Amazon data, scoring opportunities, and exporting results.

## Technologies

- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- pandas and openpyxl
- httpx
- pytest

## Installation

```bash
pip install -r requirements.txt
```

The app creates SQLite tables automatically on startup.

## Environment Variables

Create `.env` from `.env.example` and configure as needed:

```env
DATABASE_URL=sqlite:///./supplier_intelligence.db
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

EMAILJS_SERVICE_ID=
EMAILJS_TEMPLATE_ID=
EMAILJS_PUBLIC_KEY=
EMAILJS_PRIVATE_KEY=
EMAILJS_API_URL=https://api.emailjs.com/api/v1.0/email/send

APIFY_TOKEN=
APIFY_ACTOR_ID=
APIFY_API_BASE_URL=https://api.apify.com/v2

MY_NAME=
MY_EMAIL=
MY_PHONE=

MAX_UPLOAD_SIZE_MB=10
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
```

Runtime scoring and fee settings are stored locally in `app_runtime_settings.json`.

## Run Server

```bash
uvicorn app.main:app --reload
```

Open API docs:

```text
http://127.0.0.1:8000/docs
```

## Health Check

```http
GET /health
```

## Upload Suppliers

```bash
curl.exe -F "file=@proveedores_ejemplo.xlsx" http://127.0.0.1:8000/suppliers/upload
```

Supported files: `.csv`, `.xls`, `.xlsx`.

## Send Email Campaign

Send one supplier:

```http
POST /emails/send/{supplier_id}
```

Send all valid suppliers:

```http
POST /emails/campaigns/valid-suppliers
```

Check campaign:

```http
GET /emails/campaigns/{campaign_id}
```

## Upload Product Catalog

```bash
curl.exe -F "supplier_name=Acme Supply" -F "file=@catalogo_productos_ejemplo.xlsx" http://127.0.0.1:8000/catalogs/upload
```

## Enrich Products With Apify

```http
POST /products/enrich-apify
```

```json
{
  "all_pending": true
}
```

## Analyze Products

```http
POST /products/analyze
```

Analyze all:

```json
{
  "all": true
}
```

Analyze selected products:

```json
{
  "product_ids": [1, 2, 3]
}
```

## Scoring And Fee Settings

```http
GET /settings/scoring
PUT /settings/scoring
GET /settings/fees
PUT /settings/fees
```

Scoring weights must include all scoring keys and sum to `1.0`.

## Ranking And Dashboard

```http
GET /products/ranking
GET /products/{product_id}/analysis
GET /dashboard/summary
GET /dashboard/top-opportunities
GET /dashboard/supplier-performance
```

## Export Results

Download Excel files:

```bash
curl.exe -L -o products.xlsx http://127.0.0.1:8000/exports/products.xlsx
curl.exe -L -o recommended-products.xlsx http://127.0.0.1:8000/exports/recommended-products.xlsx
curl.exe -L -o suppliers.xlsx http://127.0.0.1:8000/exports/suppliers.xlsx
curl.exe -L -o summary-report.xlsx http://127.0.0.1:8000/exports/summary-report.xlsx
```

## Complete Flow

1. Upload suppliers with `/suppliers/upload`.
2. Send supplier outreach with `/emails/campaigns/valid-suppliers`.
3. Upload a supplier catalog with `/catalogs/upload`.
4. Enrich pending products with `/products/enrich-apify`.
5. Analyze products with `/products/analyze`.
6. Review `/products/ranking` and dashboard endpoints.
7. Export Excel reports from `/exports/*`.

## Error Format

Controlled errors use:

```json
{
  "success": false,
  "error": "Invalid file format",
  "details": "Only Excel and CSV files are allowed"
}
```

## Known Limitations

- Runtime settings are local-file based, not multi-instance safe.
- Rate limiting is in-memory and resets on process restart.
- Apify field mapping is flexible but depends on actor output shape.
- No user authentication or role-based authorization yet.

## Next Improvements

- Add user auth and API keys.
- Move runtime settings to database.
- Add migrations with Alembic.
- Add frontend dashboard.
- Add product matching review workflows.
- Add cloud storage for imported and exported files.

## Tests

```bash
python -m pytest app/tests -q
```
