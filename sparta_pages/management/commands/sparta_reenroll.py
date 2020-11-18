import datetime
from django.utils import timezone

from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment, UserProfile
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail, EmailMessage

from sparta_pages.models import SpartaReEnrollment


class Command(BaseCommand):
    help = 'Reenroll user from course.'

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

        parser.add_argument(
            '-m', '--mode',
            type=str,
            help='course enrollment mode to enroll user in'
        )

    def handle(self, *args, **options):
        course_id = options.get('course', None)
        user = options.get('user', None)
        mode = options.get('mode', None)

        if course_id is None:
            raise CommandError("Arguments course_id -c --course is required.")

        if user is None:
            raise CommandError("Arguments course_id -u --user is required.")

        try:
            course_key = CourseKey.from_string(course_id)
        except Exception as e:
            raise CommandError("Course does not exist: {}".format(str(e)))

        tnow = timezone.now()

        enrollments = CourseEnrollment.objects.filter(
            course_id=course_key,
            is_active=False,
            user__username=user
        )

        if enrollments.exists() == False:
            self.stdout.write("No enrollments found. course id: {}. user__username: {}".format(course_key,user))

        for e in enrollments:
            if mode is None:
                use_mode = e.mode
            else:
                use_mode = mode

            if e.is_active == False:
                try:
                    CourseEnrollment.enroll(e.user, course_key, mode=use_mode, check_access=False, can_upgrade=False)
                    reenrollments = SpartaReEnrollment.objects.create(reenroll_date=tnow)
                except Exception as e:
                    raise CommandError("Error in reenrolling learner: {}".format(str(e)))
                else:
                    self.stdout.write(self.style.SUCCESS("Successfully reenrolled learner."))
            else:
                self.stdout.write(self.style.WARNING("User {} still has an active enrollment for this course.".format(e.user.username)))
