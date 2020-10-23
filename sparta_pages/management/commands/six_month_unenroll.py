import datetime
from django.utils import timezone

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
            type=str,
            required=True,
            help='course ID to unenroll the user from'
            )
        parser.add_argument(
            '-u', '--user',
            type=str,
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
            self.stdout.write("course_key: {}".format(courer_key))
        except Exception as e:
            raise CommandError("Course does not exist: {}".format(str(e)))

        tnow = timezone.now()
        date_filter = tnow - datetime.timedelta(days=183)
        self.stdout.write("date_filter: {}".format(date_filter))

        if user is None:
            enrollments = CourseEnrollment.objects.filter(
                course_id=course_key,
                is_active=True,
                created__lt=date_filter,
            )
        else:
            enrollments = CourseEnrollment.objects.filter(
                course_id=course_key,
                is_active=True,
                created__lt=date_filter,
                user__username=user
            )

        for e in enrollments:
            reenrollments = SpartaReEnrollment.objects.filter(enrollment=e)
            self.stdout.write("e.user.username: {}".format(e.user.username))
            if reenrollments.exists():
                lastest_reenrollment = reenrollments.order_by('-reenroll_date').first()
                check_date = lastest_reenrollment.reenroll_date
            else:
                check_date = e.created

            tdelta = tnow - check_date
            self.stdout.write("tdelta: {}".format(tdelta))

            try:
                if tdelta.days >= 183:
                    CourseEnrollment.unenroll(e.user, course_id, skip_refund=True)
                    email = EmailMessage(
                        'Course Six Month Access Unenrollment',
                        'You have been unenrolled',
                        'learn@coursebank.ph',
                        [e.user.email,],
                    )
                    email.send()
            except Exception as e:
                raise CommandError("Error in unenrolling learner: {}".format(str(e)))
            else:
                self.stdout.write(self.style.SUCCESS("Successfully unenrolled learner."))
