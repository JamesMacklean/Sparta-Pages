from django.core.management.base import BaseCommand, CommandError

from sparta_pages.utils import email_sparta_overall_reports


class Command(BaseCommand):
    """
    1. Total no. of registered SPARTA learners
    2. Total no. of verified SPARTA enrollees
    """
    help = 'Manages PathwayApplications'

    def handle(self, *args, **options):
        try:
            email_sparta_overall_reports()
        except Exception as e:
            raise CommandError("Error in getting overall reports: {}".format(str(e)))

        self.stdout.write(self.style.SUCCESS("Successful in getting analytics for report."))
