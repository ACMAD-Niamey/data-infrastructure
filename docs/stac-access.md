# Accessing data via STAC

How to browse the catalog and read the underlying raster data for a STAC item, as any external
client (a notebook, a script, an AI analysis component) would. A working example lives at
[`notebooks/example.ipynb`](../notebooks/example.ipynb).

## Base URLs

| Environment | STAC API | S3/MinIO endpoint |
|---|---|---|
| Local dev | `http://localhost/stac` | `localhost:9000` |
| Production | `https://e-safari.acmad.org/stac` | `minio.acmad.org` |

The STAC API is a standard [stac-fastapi](https://github.com/stac-utils/stac-fastapi) backed by
pgSTAC (`docker-compose.yml`, service `stac_api`), proxied by nginx at `/stac/`
(`nginx/default.conf` / `default_ssl.conf`). It is spec-compliant, so any STAC client library
works against it — `pystac_client`, `pystac`, raw REST, etc.

`stac_api` is configured with `ROOT_PATH=/stac` / `UVICORN_ROOT_PATH=/stac` so that the
self/root links it returns match the public `/stac` path clients actually use. Without this the
API would advertise broken links (e.g. `http://localhost/` instead of `http://localhost/stac/`),
which breaks any client that follows them — raw fixed-path REST calls happen to work either way,
but `pystac_client.Client.open()`, `.get_collection()`, and pagination do not.

## Browsing and searching

```bash
curl "http://localhost/stac/collections" | jq '.collections[].id'
curl "http://localhost/stac/collections/precipitation-percentile-cpc-uni/items?limit=1"
```

```python
from pystac_client import Client

catalog = Client.open("http://localhost/stac")
search = catalog.search(collections=["precipitation-percentile-cpc-uni"], max_items=1)
item = next(search.items())
```

## Fetching a known item by id

Given just `(stac_url, collection_id, item_id)` — the shape an external user or AI tool would
have — no search is needed:

```python
catalog = Client.open(stac_url)
item = catalog.get_collection(collection_id).get_item(item_id)
```

## Reading the raster data

A STAC item's asset `href` is an `s3://bucket/key` URI into MinIO, **not** a plain HTTPS URL:

```json
"assets": { "data": { "href": "s3://geodata/precipitation-percentile-cpc-uni/.../file.tif" } }
```

`pystac`/`pystac_client` only fetch the item's JSON metadata. To read the actual pixels, use
GDAL's `/vsis3/` virtual filesystem (via `rasterio`), pointed at the MinIO endpoint:

```python
import os, rasterio

os.environ["AWS_S3_ENDPOINT"] = "localhost:9000"   # or minio.acmad.org in prod
os.environ["AWS_HTTPS"] = "NO"                       # "YES" in prod
os.environ["AWS_VIRTUAL_HOSTING"] = "FALSE"
os.environ["AWS_NO_SIGN_REQUEST"] = "YES"            # see "Public buckets" below

href = item.assets["data"].href                      # s3://geodata/...
vsi_path = "/vsis3/" + href.replace("s3://", "")

with rasterio.open(vsi_path) as src:
    band = src.read(1)
```

## Public buckets (current default)

The `geodata` bucket — where all ingested rasters live — has a public anonymous-read policy,
applied automatically on ingest by `set_bucket_public()`
([`ingest/storage.py`](../ingest/storage.py), also called from `uploads/tasks.py` and
`thredds_ingestion/services/ingest_bridge.py`):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "*" },
    "Action": ["s3:GetObject"],
    "Resource": ["arn:aws:s3:::geodata/*"]
  }]
}
```

This means:

- A plain unauthenticated `curl` (or any HTTP client) can already fetch an asset directly, e.g.
  `curl http://localhost:9000/geodata/<key>`.
- For GDAL/rasterio, set `AWS_NO_SIGN_REQUEST=YES` and **do not** set
  `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` — signing isn't needed, and there is no reason to
  hand out real MinIO credentials (especially not the root `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`)
  for something the bucket policy already allows anyone to read.

## Private buckets (requires authentication)

**Not currently supported per-dataset** — `set_bucket_public()` is applied to the whole bucket on
every ingest, with no flag to opt a dataset out. If a dataset must not be public, it needs to live
in its own bucket that this function is never called against, plus one of the following access
patterns:

### Option A — scoped read-only credentials

Create a MinIO **service account / access key scoped to that bucket only** (`mc admin user` /
`mc admin policy`), never reuse `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`. Distribute those
credentials only to authorized consumers (env vars, secrets manager — never committed to a
notebook or repo). Reading is then identical to the public case, minus
`AWS_NO_SIGN_REQUEST`:

```python
os.environ["AWS_ACCESS_KEY_ID"] = "<scoped-read-only-key>"
os.environ["AWS_SECRET_ACCESS_KEY"] = "<scoped-read-only-secret>"
os.environ["AWS_S3_ENDPOINT"] = "minio.acmad.org"
```

### Option B — presigned URLs (preferred for external/one-off sharing)

Server-side, generate a short-lived signed URL for the specific object and hand that out instead
of any credential. The recipient just does a normal HTTPS GET — no AWS/GDAL setup at all:

```python
from ingest.storage import s3_client

url = s3_client().generate_presigned_url(
    "get_object",
    Params={"Bucket": "geodata-private", "Key": key},
    ExpiresIn=3600,
)
```

This is the better fit for "give an external user a link to one dataset" than a shared
credential, since access is time-boxed and per-object rather than bucket-wide.

## Related

- [Ingest and delete API](ingest-delete.md) — how assets get into MinIO/STAC in the first place.
- [`notebooks/example.ipynb`](../notebooks/example.ipynb) — runnable end-to-end example.
