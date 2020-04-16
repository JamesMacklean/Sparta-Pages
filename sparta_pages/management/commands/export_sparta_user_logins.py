import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand, CommandError

from sparta_pages.utils import export_sparta_user_logins


class Command(BaseCommand):
    help = 'Exports list of courses with number of completed learners.'

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
            export_sparta_user_logins(email_address=email_address)
        except Exception as e:
            raise CommandError("Error in exporting SPARTA user logins: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully exported SPARTA user logins."))

        self.stdout.write(self.style.SUCCESS("Successfully exported SPARTA user logins."))
