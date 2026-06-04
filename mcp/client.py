import httpx
from config import DJANGO_API_URL, STAC_API_URL, TITILER_URL

_django  = httpx.AsyncClient(base_url=DJANGO_API_URL, timeout=15.0)
_stac    = httpx.AsyncClient(base_url=STAC_API_URL,   timeout=15.0)
_titiler = httpx.AsyncClient(base_url=TITILER_URL,    timeout=30.0)


async def api_get(path: str, **params) -> dict | list:
    r = await _django.get(path, params={k: v for k, v in params.items() if v is not None})
    r.raise_for_status()
    return r.json()


async def stac_get(path: str, **params) -> dict | list:
    r = await _stac.get(path, params={k: v for k, v in params.items() if v is not None})
    r.raise_for_status()
    return r.json()


async def stac_post(path: str, body: dict) -> dict:
    r = await _stac.post(path, json=body)
    r.raise_for_status()
    return r.json()


async def titiler_post(path: str, params: dict, geojson_body: dict) -> dict:
    r = await _titiler.post(path, params=params, json=geojson_body)
    r.raise_for_status()
    return r.json()
