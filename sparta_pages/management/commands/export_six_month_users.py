import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand, CommandError

from sparta_pages.utils import export_six_month_users


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
            export_six_month_users(course_id, email_address=email_address)
        except Exception as e:
            raise CommandError("Error in exporting six month users: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully exported six month users."))
