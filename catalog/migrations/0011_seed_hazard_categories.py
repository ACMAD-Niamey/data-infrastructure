from django.db import migrations

DEFAULTS = [
    ("weather",     "Weather",         0),
    ("drought",     "Drought",         1),
    ("flood",       "Flood",           2),
    ("heat",        "Heat",            3),
    ("agriculture", "Agriculture",     4),
    ("exposure",    "Exposure",        5),
    ("impact",      "Impact",          6),
    ("boundary",    "Boundary Layers", 7),
]


def seed_hazard_categories(apps, schema_editor):
    HazardCategory = apps.get_model("catalog", "HazardCategory")
    for key, label, order in DEFAULTS:
        HazardCategory.objects.get_or_create(key=key, defaults={"label": label, "order": order})


def unseed_hazard_categories(apps, schema_editor):
    # Only removes rows that still match the original defaults — safe to reverse
    HazardCategory = apps.get_model("catalog", "HazardCategory")
    HazardCategory.objects.filter(key__in=[r[0] for r in DEFAULTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0010_hazardcategory_datasetpage_hazard_category"),
    ]

    operations = [
        migrations.RunPython(seed_hazard_categories, unseed_hazard_categories),
    ]
