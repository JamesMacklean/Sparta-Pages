from datetime import datetime, date, timedelta
from django.utils import timezone

from django.core.management.base import BaseCommand, CommandError

from sparta_pages.models import Pathway, SpartaCourse, PathwayApplication
from sparta_pages.utils import manage_sparta_enrollments


class Command(BaseCommand):
    help = 'Manages List of Sparta Scholars that need to be enrolled.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-f',
            '--fromdate',
            type=str,
            help='set from date (format: Y-M-D)',
        )
        parser.add_argument(
            '-t',
            '--todate',
            type=str,
            help='set to date (format: Y-M-D)',
        )

    def handle(self, *args, **options):
        fromdate = options.get('fromdate', None)
        todate = options.get('todate', None)

        if fromdate is not None:
            date_from = datetime.strptime(fromdate, "%Y-%m-%d").date()
        else:
            date_from = timezone.now().date() - timedelta(days=1)

        if todate is not None:
            date_to = datetime.strptime(todate, "%Y-%m-%d").date()
        else:
            date_to = timezone.now().date()

        try:
            manage_sparta_enrollments(date_from=date_from, date_to=date_to)
        except Exception as e:
            raise CommandError("Error in managing Sparta enrollments: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully managed Sparta enrollments."))
