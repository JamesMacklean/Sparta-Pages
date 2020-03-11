import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand, CommandError

from sparta_pages.utils import export_sparta_profiles, export_sparta_education_credentials, export_sparta_employment_credentials, export_sparta_training_credentials


class Command(BaseCommand):
    help = 'Manages List of Sparta Scholars that need to be enrolled.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-e',
            '--email',
            type=str,
            help='set email of student to limit coupons to get',
        )
        parser.add_argument(
            '-p',
            '--profiles',
            action='store_true',
            help='Include SpartaProfiles and ExtendedSpartaProfiles'
        )
        parser.add_argument(
            '-d',
            '--education',
            action='store_true',
            help='Include EducationProfiles'
        )
        parser.add_argument(
            '-m',
            '--employment',
            action='store_true',
            help='Include EmploymentProfiles'
        )
        parser.add_argument(
            '-t',
            '--training',
            action='store_true',
            help='Include TrainingProfiles'
        )

    def handle(self, *args, **options):
        email = options.get('email', None)
        profiles = options.get('profiles')
        education = options.get('education')
        employment = options.get('employment')
        training = options.get('training')

        try:
            if profiles:
                export_sparta_profiles(email=email)
            if education:
                export_sparta_education_credentials(email=email)
            if employment:
                export_sparta_employment_credentials(email=email)
            if training:
                export_sparta_training_credentials(email=email)
        except Exception as e:
            raise CommandError("Error in exporting Sparta profiles: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully exported Sparta profiles."))
