import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand, CommandError

from sparta_pages.utils import assign_coupons_to_students


class Command(BaseCommand):
    help = 'Manages List of Sparta Scholars that need to be enrolled.'


    def handle(self, *args, **options):
        # try:
        #     assign_coupons_to_students()
        # except Exception as e:
        #     raise CommandError("Error in assigning Sparta coupons to students: {}".format(str(e)))
        # else:
        #     self.stdout.write(self.style.SUCCESS("Successfully assigned Sparta coupons to students."))
        assign_coupons_to_students()
