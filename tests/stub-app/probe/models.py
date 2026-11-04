from django.db import models


class ProbeNote(models.Model):
    """Row used by the restore drill to verify data survives a backup."""

    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
