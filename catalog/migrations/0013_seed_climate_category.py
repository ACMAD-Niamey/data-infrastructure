from django.db import migrations


def seed(apps, schema_editor):
    HazardCategory = apps.get_model("catalog", "HazardCategory")
    HazardCategory.objects.get_or_create(
        key="climate",
        defaults={"label": "Climate", "order": 8},
    )


def unseed(apps, schema_editor):
    apps.get_model("catalog", "HazardCategory").objects.filter(key="climate").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0012_layer_details_fields"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
