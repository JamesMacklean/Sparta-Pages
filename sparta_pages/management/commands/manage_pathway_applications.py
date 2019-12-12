from django.core.management.base import BaseCommand, CommandError

from sparta_pages.models import Pathway, SpartaCourse, PathwayApplication
from sparta_pages.utils import manage_pathway_applications

class Command(BaseCommand):
    help = 'Manages PathwayApplications'

    def handle(self, *args, **options):
        try:
            manage_pathway_applications()
        except Exception as e:
            raise CommandError("Error in managing PathwayApplications: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully managed PathwayApplications.")
