import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand, CommandError

from sparta_pages.utils import export_sparta_completed_courses


class Command(BaseCommand):
    help = 'Exports list of courses with number of completed learners.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-e',
            '--email',
            type=str,
            help='set email to send to',
        )
        def add_arguments(self, parser):
            parser.add_argument(
                '-c',
                '--course',
                type=str,
                help='set filter for course_id',
            )
        parser.add_argument(
            '-n',
            '--nonactive',
            action='store_true',
            help='set course filter for is_active'
        )

    def handle(self, *args, **options):
        email_address = options.get('email', None)
        course_id = options.get('course', None)
        is_active = not options.get('nonactive')

        try:
            export_sparta_completed_courses(email_address=email_address, course_id=course_id, is_active=is_active)
        except Exception as e:
            raise CommandError("Error in exporting SPARTA course completions: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully exported SPARTA course completions."))
