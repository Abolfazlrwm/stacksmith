"""Initial migration: Conversation + Message tables."""
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.CharField(db_index=True, max_length=128)),
                ("title", models.CharField(blank=True, max_length=256)),
            ],
            options={"ordering": ("-updated_at",)},
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("user", "User"), ("assistant", "Assistant")], max_length=16)),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("citations", models.JSONField(blank=True, default=list)),
                ("retrieved_count", models.PositiveIntegerField(default=0)),
                ("model", models.CharField(blank=True, max_length=64)),
                ("usage", models.JSONField(blank=True, default=dict)),
                ("conversation", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="messages", to="chat.conversation")),
            ],
            options={"ordering": ("conversation", "created_at")},
        ),
    ]
