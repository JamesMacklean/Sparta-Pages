import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand, CommandError

from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment

from sparta_pages.helpers.helpers import email_list_of_users_problem_status


class Command(BaseCommand):
    help = 'Gets list of learners who have answered a problem and send email.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-c',
            '--course',
            type=str,
            help='set course id',
        )
        parser.add_argument(
            '-l',
            '--location',
            type=str,
            help='set course block location',
        )

    def handle(self, *args, **options):
        course_id = options.get('course', None)
        location = options.get('location', None)

        if course_id is None or location is None:
            raise CommandError("Arguments course_id -c --course and location -l --location are required.")

        try:
            email_list_of_users_problem_status(course_id, location)
        except Exception as e:
            raise CommandError("Error in emailing user problem status: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully emailed learners problem stati."))
