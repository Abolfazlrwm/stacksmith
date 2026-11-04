"""Enable the pgvector extension."""
from django.db import migrations


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    atomic = False

    operations = [
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;",
        ),
    ]
