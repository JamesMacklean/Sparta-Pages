import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand

from sparta_pages.models import Pathway
from sparta_pages.utils import email_sparta_student_coupon_records


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
            '--pathway',
            type=int,
            help='set pathway id to limit coupons to get',
        )

    def handle(self, *args, **options):
        email = options.get('email', None)
        pathway = options.get('pathway', None)
        if pathway is not None:
            try:
                pathway = Pathway.objects.get(id=pathway)
            except Pathway.DoesNotExist:
                raise CommandError("Error in emailing Sparta student coupon records: Pathway with id {} not found.".format(pathway))

        try:
            email_sparta_student_coupon_records(email=email, pathway=pathway)
        except Exception as e:
            raise CommandError("Error in emailing Sparta student coupon records: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully emailing Sparta student coupon records."))
