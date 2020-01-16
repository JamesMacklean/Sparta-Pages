import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand

from sparta_pages.utils import get_courses_that_need_new_coupons_list


class Command(BaseCommand):
    help = 'Manages the coupons available to be assigned to students.'


    def handle(self, *args, **options):
        try:
            courses_list = get_courses_that_need_new_coupons_list()
        except Exception as e:
            raise CommandError("Error in getting Sparta courses for new coupons: {}".format(str(e)))
        if courses_list:
            self.stdout.write(self.style.WARNING("WARNING: The following courses need new coupons for migration:"))
            for course in courses_list:
                self.stdout.write(self.style.WARNING(course))
        else:
            self.stdout.write(self.style.SUCCESS("No new coupons need to be migrated. B-)"))
