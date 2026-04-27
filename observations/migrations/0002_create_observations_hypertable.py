from django.db import migrations
from pathlib import Path


def load_sql():
    sql_path = Path(__file__).resolve().parent.parent / "sql" / "hypertable.sql"
    return sql_path.read_text()


class Migration(migrations.Migration):

    dependencies = [
        ("observations", "0001_initial"),
        ("stations", "0001_initial"),
        ("sources", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=load_sql(),
            reverse_sql="DROP TABLE IF EXISTS observations CASCADE;",
        ),
    ]
