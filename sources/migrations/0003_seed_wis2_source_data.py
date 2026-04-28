from django.db import migrations


def seed_wis2_source(apps, schema_editor):
    Policy = apps.get_model("sources", "Policy")
    DataSource = apps.get_model("sources", "DataSource")
    Dataset = apps.get_model("sources", "Dataset")

    policy, _ = Policy.objects.get_or_create(
        name="Internal Only",
        defaults={
            "owner_org": "Internal",
            "public_api_allowed": False,
            "dashboard_allowed": False,
            "internal_allowed": True,
            "partner_allowed": False,
            "raw_download_allowed": False,
            "aggregate_allowed": True,
            "station_visible": True,
        },
    )

    source, _ = DataSource.objects.get_or_create(
        source_code="wis2-global-broker",
        defaults={
            "source_name": "WIS2 Global Broker",
            "source_type": "wis2",
            "protocol": "mqtt",
            "is_active": True,
        },
    )

    Dataset.objects.get_or_create(
        dataset_code="wis2_text_notifications",
        defaults={
            "source": source,
            "policy": policy,
            "dataset_name": "WIS2 Text Notifications",
            "variable_family": "surface_observations",
            "temporal_resolution": "irregular",
            "is_active": True,
        },
    )

    Dataset.objects.get_or_create(
        dataset_code="wis2_json_observations",
        defaults={
            "source": source,
            "policy": policy,
            "dataset_name": "WIS2 JSON Observations",
            "variable_family": "surface_observations",
            "temporal_resolution": "irregular",
            "is_active": True,
        },
    )

    Dataset.objects.get_or_create(
        dataset_code="wis2_bufr_observations",
        defaults={
            "source": source,
            "policy": policy,
            "dataset_name": "WIS2 BUFR Observations",
            "variable_family": "surface_observations",
            "temporal_resolution": "irregular",
            "is_active": True,
        },
    )


def unseed(apps, schema_editor):
    Dataset = apps.get_model("sources", "Dataset")
    Dataset.objects.filter(
        dataset_code__in=[
            "wis2_text_notifications",
            "wis2_json_observations",
            "wis2_bufr_observations",
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("sources", "0002_alter_dataset_id_alter_datasource_id_alter_policy_id"),
    ]

    operations = [
        migrations.RunPython(seed_wis2_source, unseed),
    ]
