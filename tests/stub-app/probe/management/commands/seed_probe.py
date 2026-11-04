from django.core.management.base import BaseCommand

from probe.models import ProbeNote


class Command(BaseCommand):
    help = "Insert probe rows for the restore drill"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=100)

    def handle(self, *args, **options):
        rows = ProbeNote.objects.bulk_create(
            [ProbeNote(title=f"probe row {i}") for i in range(options["count"])]
        )
        self.stdout.write(f"seeded {len(rows)} probe rows")
