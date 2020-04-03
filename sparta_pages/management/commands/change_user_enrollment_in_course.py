"""
Management command for enrolling a user into a course via the enrollment api
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from enrollment.data import CourseEnrollmentExistsError
from enrollment.api import update_enrollment


class Command(BaseCommand):
    """
    Enroll a user into a course
    """
    help = """
    This enrolls a user into a given course with the default mode (e.g., 'honor', 'audit', etc).

    User email and course ID are required.

    example:
        # Enroll a user test@example.com into the demo course
        manage.py ... change_user_enrollment_in_course -u testexample -c edX/Open_DemoX/edx_demo_course

        This command can be run multiple times on the same user+course (i.e. it is idempotent).
    """

    def add_arguments(self, parser):

        parser.add_argument(
            '-u', '--username',
            nargs=1,
            required=True,
            help='Username for user'
        )
        parser.add_argument(
            '-c', '--course',
            nargs=1,
            required=True,
            help='course ID to enroll the user in')
        parser.add_argument(
            '-m', '--mode',
            nargs=1,
            required=True,
            help='course enrollment mode to enroll user in')

    def handle(self, *args, **options):
        """
        Get and enroll a user in the given course. Mode is optional and defers to the enrollment API for defaults.
        """
        username = options['username'][0]
        course = options['course'][0]
        mode = options['mode'][0]

        user = User.objects.get(username=username)
        try:
            update_enrollment(user.username, course, mode=mode, is_active=True)
        except Exception as e:
            raise CommandError(str(e))
