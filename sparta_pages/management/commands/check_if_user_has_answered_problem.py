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
    help = 'Gets list of learners who have answered a problem.'

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

        enrollments = CourseEnrollment.objects.all()
        course_key = CourseKey.from_string(course_id)
        try:
            course = CourseOverview.get_from_id(course_key)
        except CourseOverview.DoesNotExist:
            raise CommandError("Course does not exist: {}".format(course_id))

        try:
            for enrollment in enrollments.filter(course=course):
                check_if_user_has_answered_this_problem(course_id, enrollment.user.username, location)
        except Exception as e:
            raise CommandError("Error in checking user problem status: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully checked learners problem stati."))
