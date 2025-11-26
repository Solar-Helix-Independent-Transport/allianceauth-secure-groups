from securegroups.tasks import run_smart_groups

from django.core.management.base import BaseCommand

class Commande(BaseCommand):
    help = "Runs the smart groups update task"

    def handle(self, *args, **options):
        self.stdout.write("Running smart group update")

        run_smart_groups()

        self.stdout.write("Update finished")
