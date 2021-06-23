import csv
import os
from pprint import pformat
from datetime import datetime, date, timedelta
from django.utils import timezone

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand, CommandError

from sparta_pages.utils import export_learner_pathway_progress


class Command(BaseCommand):
    help = 'Exports list of graduating learner candidates for a specific pathway.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-e',
            '--email',
            type=str,
            help='set email to send to',
        )
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
        parser.add_argument(
            '-p',
            '--pathway',
            type=int,
            help='set pathway number',
        )

    def handle(self, *args, **options):
        email_address = options.get('email', None)
        fromdate = options.get('fromdate', None)
        todate = options.get('todate', None)
        path_way = options.get('pathway', None)

        if fromdate is not None:
            date_from = datetime.strptime(fromdate, "%Y-%m-%d")
        else:
            date_from = datetime.now().date() - timedelta(days=1)

        if todate is not None:
            date_to = datetime.strptime(todate, "%Y-%m-%d")
        else:
            date_to = datetime.now()

        try:
            export_learner_pathway_progress(path_way=path_way, email_address=email_address, date_from=date_from, date_to=date_to)
        except Exception as e:
            raise CommandError("export_learner_pathway_progress.ERROR: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully exported SPARTA learner pathway progress."))
