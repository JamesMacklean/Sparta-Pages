from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment, UserProfile
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail, EmailMessage

from sparta_pages.models import SixMonthAccess


class Command(BaseCommand):
    help = 'Unenroll user from course and send email notification.'

    def add_arguments(self, parser):

        parser.add_argument(
            '-c', '--course',
            nargs=1,
            required=True,
            help='course ID to unenroll the user from'
            )
        parser.add_argument(
            '-u', '--user',
            nargs=1,
            required=True,
            help='Username for user'
        )

    def handle(self, *args, **options):
        course_id = options.get('course', None)
        user = options.get('user', None)

        enrollments = CourseEnrollment.objects.filter(
            course_id=course_key,
            is_active=True,
            created=created
        )

        if course_id is None:
            raise CommandError("Arguments course_id -c --course is required.")

        try:
            course_key = CourseKey.from_string(course_id)
        except Exception as e:
            raise CommandError("Course does not exist: {}".format(str(e)))

        for e in enrollments:
            try:
                check_date = SixMonthAccess.objects.get(reenroll=reenroll)
            except SixMonthAccess.DoesNotExist:
                check_date = CourseEnrollment.objects.get(created=e.created)

            tnow = datetime.now()
            tdelta = check_date - tnow

            if CourseEnrollment.objects.get(is_active=e.is_active) == True and tdelta.months >= 6
                CourseEnrollment.unenroll(e.user, course_id, skip_refund=True)
                email = EmailMessage(
                    'Course Six Month Access Unenrollment',
                    'You have been unenrolled',
                    'learn@coursebank.ph',
                    [e.user.email,],
                )
                email.send()
