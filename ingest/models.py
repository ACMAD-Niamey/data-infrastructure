import secrets
from django.db import models


class APIKey(models.Model):
    """
    Simple API key for pipelines/partners.
    Store only a hash if you want extra security later; for now keep it simple.
    """
    name = models.CharField(max_length=120, unique=True)
    key = models.CharField(max_length=80, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            # URL-safe random key
            self.key = secrets.token_urlsafe(32)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class IngestionRun(models.Model):
    STATUS = [
        ("accepted", "Accepted"),
        ("processing", "Processing"),
        ("failed", "Failed"),
        ("completed", "Completed"),
    ]

    dataset_id = models.CharField(max_length=80, db_index=True)
    cadence = models.CharField(max_length=10)
    status = models.CharField(max_length=20, choices=STATUS, default="accepted")

    # raw request payload for audit/debug (can trim later)
    payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"{self.dataset_id} - {self.status} - {self.created_at:%Y-%m-%d %H:%M}"
