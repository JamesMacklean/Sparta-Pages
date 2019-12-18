from django.core.management.base import BaseCommand, CommandError

from sparta_pages.models import Pathway, SpartaCourse, PathwayApplication
from sparta_pages.utils import manage_sparta_enrollments

class Command(BaseCommand):
    help = 'Manages PathwayApplications'

    def handle(self, *args, **options):
        try:
            manage_sparta_enrollments()
        except Exception as e:
            raise CommandError("Error in managing Sparta enrollments: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully managed Sparta enrollments."))
