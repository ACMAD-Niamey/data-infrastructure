from .base import *

DEBUG = False

# Use WhiteNoise's manifest storage in production: hashes filenames for cache-busting,
# compresses assets, and does not raise ValueError for missing manifest entries
# (unlike Django's ManifestStaticFilesStorage with manifest_strict=True).
STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedManifestStaticFilesStorage"


try:
    from .local import *
except ImportError:
    pass
