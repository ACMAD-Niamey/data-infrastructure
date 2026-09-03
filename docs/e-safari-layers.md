# e-safari dynamic layers

Editors configure map layers via **Dataset pages** under a Wagtail project; the e-safari UI loads them from the catalog API. Optional **Layer style** snippets add colormap, legend, and tile parameters.

## Prerequisites

- Datasets ingested into pgSTAC for the target `dataset_id`
- `VITE_PROJECT_SLUG` in e-safari-ui matches the Wagtail **project page** slug (default: `e-safari`)

## Editor workflow

### 1. Layer icons

1. In Wagtail admin, open **Snippets → Layer icons**.
2. Create an icon: **title**, **slug** (e.g. `agriculture`, `rain`), and upload an **image** in **Images** (SVG or PNG; SVG enabled via `WAGTAILIMAGES_EXTENSIONS`).

Reuse the same icon on multiple datasets.

### 2. Dataset pages (required for UI listing)

Under the **e-safari** project page:

1. Create or edit a **Dataset** child page.
2. Set **dataset_id** (stable API id, e.g. `lu`, `drone-imagery`) — this is also the **UI layer id** in 1:1 mode.
3. Set **cadence** (`daily`, `dekadal`, `monthly`, or `seasonal`).
4. Choose an **icon** on the dataset page.
5. Enable **is published for UI**.
6. Add **description** (shown on the layer info control in the UI).
7. Set **sort order** if needed (lower numbers appear first).

Publish the dataset page.

No Layer snippet is required for a dataset to appear in the sidebar.

### 3. Layer style snippets (optional)

1. Open **Snippets → Layer styles**.
2. Create one style per dataset: pick the **dataset**, set legend/colormap/tile params.
3. **layer_id** defaults to `dataset_id` if left blank.

Use this when you need TiTiler colormap, legend, opacity, or zoom limits. Visualization reads style from the linked snippet.

**Multiple styles per dataset.** Check **"allow multiple layer styles"** on the dataset page to attach more than one style — e.g. one per data source, each with its own **`stac_collection_id`** (under *Layer details*) that ingestion targets. Each style then needs a distinct non-blank `layer_id`. The UI still renders one entry per dataset — the **primary** style (the `default_visible` one, else first by title). See `docs/thredds-ingestion.md` → *Multiple sources for one dataset*.

### 4. Ingest data

```http
POST /api/ingest/ingest/datasets/{dataset_id}/items
```

### 5. Verify

```bash
curl "https://<host>/api/catalog/ui/layers?project=e-safari"
```

Expect one entry per published dataset with an icon; `layers[].id` equals `layers[].dataset.id`.

## IDs

| Use | Field |
|-----|--------|
| UI layer list, map layer key `raster-{id}` | `dataset_id` (API `layers[].id`) |
| Availability & visualization APIs | `dataset_id` (`layers[].dataset.id`) |
| Future: multiple styles per dataset | distinct `layer_id` on style snippet (follow-up) |

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/catalog/ui/layers?project=e-safari` | Published datasets with icons (+ merged style if present) |
| `GET /api/catalog/datasets/{id}/availability/?cadence=...` | Date options for selectors |
| `GET /api/catalog/datasets/{id}/visualization/?cadence=...&date=...` | TiTiler tile URL for the map |

## Frontend env

```bash
VITE_PROJECT_SLUG=e-safari
```

See [e-safari-ui/.env.example](../e-safari-ui/.env.example).
