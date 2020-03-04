import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand, CommandError

from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment

from sparta_pages.models import Pathway
from .helpers import check_if_user_has_answered_this_problem


class Command(BaseCommand):
    help = 'Checks if user has completed a course.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-u',
            '--user',
            type=str,
            help='set username',
        )
        parser.add_argument(
            '-c',
            '--course',
            type=str,
            help='set course id',
        )


    def handle(self, *args, **options):
        course_id = options.get('course', None)
        username = options.get('user', None)

        if course_id is None or username is None:
            raise CommandError("Arguments course_id -c --course and username -u --user are required.")

        course_key = CourseKey.from_string(course_id)
        try:
            course = CourseOverview.get_from_id(course_key)
        except CourseOverview.DoesNotExist:
            raise CommandError("Course does not exist: {}".format(course_id))

        try:
            check_if_user_has_completed_course
        except Exception as e:
            raise CommandError("Error in checking user course completion status: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully checked learners course completion status."))
