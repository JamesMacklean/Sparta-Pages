import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand, CommandError

from sparta_pages.utils import export_learner_pathway_progress


class Command(BaseCommand):
    help = 'Exports list of learners with number of completed courses in their pathways.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-e',
            '--email',
            type=str,
            help='set email to send to',
        )

    def handle(self, *args, **options):
        email_address = options.get('email', None)

        try:
            export_learner_pathway_progress(email_address=email_address)
        except Exception as e:
            raise CommandError("export_learner_pathway_progress.ERROR: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully exported SPARTA learner pathway progress."))
