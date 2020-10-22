from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment, UserProfile
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail, EmailMessage

from sparta_pages.models import SpartaReEnrollment


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

        if course_id is None:
            raise CommandError("Arguments course_id -c --course is required.")

        try:
            course_key = CourseKey.from_string(course_id)
        except Exception as e:
            raise CommandError("Course does not exist: {}".format(str(e)))

        tnow = datetime.datetime.now()
        date_filter = tnow - datetime.timedelta(months=6)

        enrollments = CourseEnrollment.objects.filter(
            course_id=course_key,
            is_active=True,
            created__gt=date_filter,
        )

        for e in enrollments:
            reenrollments = SpartaReEnrollment.objects.filter(enrollment=e)
            if reenrollments.exists()
                lastest_reenrollment = reenrollment.order_by('-created').first()
                check_date = lastest_reenrollment

            tdelta = tnow - check_date

            if tdelta.months >= 6
                CourseEnrollment.unenroll(e.user, course_id, skip_refund=True)
                email = EmailMessage(
                    'Course Six Month Access Unenrollment',
                    'You have been unenrolled',
                    'learn@coursebank.ph',
                    [e.user.email,],
                )
                email.send()
