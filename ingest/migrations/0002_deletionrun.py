# Generated manually for DeletionRun model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ingest", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeletionRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dataset_id", models.CharField(db_index=True, max_length=80)),
                ("cadence", models.CharField(max_length=10)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("accepted", "Accepted"),
                            ("processing", "Processing"),
                            ("failed", "Failed"),
                            ("completed", "Completed"),
                        ],
                        default="accepted",
                        max_length=20,
                    ),
                ),
                ("payload", models.JSONField(blank=True, default=dict)),
                (
                    "delete_object",
                    models.BooleanField(
                        default=False,
                        help_text="When true, also delete the MinIO object referenced by the STAC asset.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("error_message", models.TextField(blank=True)),
            ],
        ),
    ]
