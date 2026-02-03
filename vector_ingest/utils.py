import re
from slugify import slugify

SAFE_IDENT = re.compile(r"^[a-z][a-z0-9_]{0,62}$")

def normalize_table_name(name: str) -> str:
    n = slugify(name).replace("-", "_").lower().strip("_")
    if not n:
        n = "dataset"
    if not SAFE_IDENT.match(n):
        n = re.sub(r"[^a-z0-9_]", "_", n)
        n = re.sub(r"_+", "_", n).strip("_")
        if not n or not SAFE_IDENT.match(n):
            n = "dataset"
    return n[:63]
