import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand, CommandError

from sparta_pages.models import SpartaProfile
from sparta_pages.utils import assign_coupons_to_single_student

class Command(BaseCommand):
    help = 'Manages coupons of learner.'

    parser.add_argument(
        '-u',
        '--username',
        type=str,
        help='set username',
    )

    def handle(self, *args, **options):
        username = options.get('username', None)
        if username is None:
            raise CommandError("Arg -u --username is required.")

        try:
            student = SpartaProfile.objects.get(user__username=username)
        except SpartaProfile.DoesNotExist:
            raise CommandError("User does not exist: {}".format(username)

        try:
            assign_coupons_to_single_student(student)
        except Exception as e:
            raise CommandError("Error in assigning Sparta coupons to students: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully assigned Sparta coupons to student."))
