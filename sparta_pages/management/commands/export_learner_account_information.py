import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand, CommandError

from sparta_pages.utils import export_learner_account_information


class Command(BaseCommand):
    help = 'Exports list of courses with number of completed learners.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-e',
            '--email',
            type=str,
            help='set email to send to',
        )
        parser.add_argument(
            '-c',
            '--course',
            type=str,
            help='set filter for course_id',
        )

    def handle(self, *args, **options):
        course_id = options.get('course', None)
        email_address = options.get('email', None)

        if course_id is None:
            raise CommandError("--course -c arg required ")

        try:
            export_learner_account_information(course_id, email_address=email_address)
        except Exception as e:
            raise CommandError("Error in exporting learner account information: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully exported learner account information."))
