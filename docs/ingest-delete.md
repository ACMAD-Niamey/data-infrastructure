# Ingest and delete API (raster STAC items)

Base path: `/api/ingest/`

Authentication: same as ingest (`IsAuthenticated` — session or token per project setup).

## Ingest (create catalog entry)

```http
POST /api/ingest/ingest/datasets/{dataset_id}/items
```

Registers a STAC item for a raster already stored in MinIO. Optionally converts GeoTIFFs to COG in place. See OpenAPI at `/api/docs/` for the full request body.

Response: `202` with `{ "run_id", "status": "accepted" }`.

## Delete (remove catalog entry)

Deletion runs asynchronously (Celery). Track runs in Django admin under **Deletion runs** or poll status by run id if you add a status endpoint later.

### Mode: STAC catalog only (default)

Removes the STAC item from pgSTAC. The MinIO file is **left in place**.

### Mode: STAC + MinIO file

Pass query parameter `delete_object=true`. The worker reads `assets.data.href` from the STAC item, deletes that object from MinIO, then deletes the STAC item.

---

### Delete by STAC item id

```http
DELETE /api/ingest/ingest/datasets/{dataset_id}/items/{item_id}
DELETE /api/ingest/ingest/datasets/{dataset_id}/items/{item_id}?delete_object=true
```

Example (catalog only):

```bash
curl -X DELETE -u user:pass \
  "http://localhost/api/ingest/ingest/datasets/lu/items/lu_2026-02-01T000000Z"
```

Example (catalog + file):

```bash
curl -X DELETE -u user:pass \
  "http://localhost/api/ingest/ingest/datasets/lu/items/lu_2026-02-01T000000Z?delete_object=true"
```

Response `202`:

```json
{
  "run_id": 1,
  "status": "accepted",
  "item_id": "lu_2026-02-01T000000Z",
  "delete_object": false
}
```

---

### Delete by datetime

Use when you know the ingest datetime but not the generated item id. Temporal fields match ingest cadence rules on the dataset.

```http
DELETE /api/ingest/ingest/datasets/{dataset_id}/items/delete
DELETE /api/ingest/ingest/datasets/{dataset_id}/items/delete?delete_object=true
Content-Type: application/json
```

**Monthly / daily** — body:

```json
{ "datetime": "2026-02-01T00:00:00Z" }
```

**Dekadal / seasonal** — body:

```json
{
  "start_datetime": "2026-04-01T00:00:00Z",
  "end_datetime": "2026-04-10T23:59:59Z"
}
```

**Explicit item id in body** (skips STAC search):

```json
{ "item_id": "lu_2026-02-01T000000Z" }
```

The service searches STAC for items in the resolved time window:

- **0 matches** → `404`
- **2+ matches** → `409` with `item_ids` — use delete-by-id instead
- **1 match** → `202` and async delete

---

## Item id convention

If ingest did not set a custom `item_id`, ids are derived as:

```text
{dataset_id}_{datetime}
```

with `:` and `+` removed from the datetime string (same as ingest `build_item`).

---

## Prerequisites

- **stac-fastapi** must have the transactions extension enabled (see `docker-compose.yml`).
- **Worker** must reach `STAC_API_URL` and `MINIO_ENDPOINT` (internal Docker hostnames).
- For `delete_object=true`, `assets.data.href` must be `s3://bucket/key`.

## Related

- Upload rasters: `/api/uploads/`
- Catalog UI: `/api/catalog/datasets/{id}/availability/` and `visualization/`
