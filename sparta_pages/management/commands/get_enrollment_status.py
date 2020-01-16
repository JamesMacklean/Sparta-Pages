from django.core.management.base import BaseCommand, CommandError

from sparta_pages.utils import get_enrollment_status

class Command(BaseCommand):
    help = 'Manages PathwayApplications'

    def handle(self, *args, **options):
        try:
            get_enrollment_status()
        except Exception as e:
            raise CommandError("Error in getting enrollment statuses: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successful in getting enrollment statuses."))
