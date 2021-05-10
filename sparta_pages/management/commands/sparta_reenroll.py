import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

import datetime
from django.utils import timezone
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment, UserProfile
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail, EmailMessage
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

from sparta_pages.models import SpartaReEnrollment


class Command(BaseCommand):
    help = 'Reenroll user from course and send email notification.'

    def add_arguments(self, parser):

        parser.add_argument(
            '-c', '--course',
            type=str,
            required=False,
            help='course ID to unenroll the user from'
            )
        parser.add_argument(
            '-u', '--user',
            type=str,
            required=False,
            help='Username for user'
        )
        parser.add_argument(
            '-m', '--mode',
            type=str,
            help='course enrollment mode to enroll user in'
        )
        parser.add_argument(
            '--csv-file',
            action='store',
            dest='csv_file',
            default=None,
            help='Path of the file to read users from.',
            type=str,
            required=False
        )

    def handle(self, *args, **options):
        course_id = options.get('course', None)
        user = options.get('user', None)
        mode = options.get('mode', None)
        csv_file = options.get('csv_file')

        if course_id is None:
            raise CommandError("Arguments course_id -c --course is required.")

        try:
            course_key = CourseKey.from_string(course_id)
            self.stdout.write("course_key: {}".format(course_key))
        except Exception as e:
            raise CommandError("Course does not exist: {}".format(str(e)))

        courseoverview = CourseOverview.get_from_id(course_key)
        course_name = courseoverview.display_name

        if user is not None:
            try:
                uname = User.objects.get(username=user)
                reenrolled_user = self._reenroll_user(username=uname, email_address=uname.email, course_key=course_key, course_name=course_name, mode=mode)

                msg = 'Successfully reenrolled user: {}.'.format(reenrolled_user)
                log.info(msg)
                self.stdout.write(msg)

            except Exception as e:
                raise CommandError("Error in appending user to list: {}".format(str(e)))

        elif csv_file:
            if not os.path.exists(csv_file):
                raise CommandError(u'Pass the correct absolute path to file as --csv-file argument.')

            total_users, failed_users = self._reenroll_users_from_file(csv_file, course_key=course_key, course_name=course_name, mode=mode)

            if failed_users:
                msg = u'Completed reenrolling the users. {} of {} failed.'.format(
                    len(failed_users),
                    total_users
                )
                log.error(msg)
                self.stdout.write(msg)
                msg = 'Failed users:{}'.format(pformat(failed_users))
                log.error(msg)
                self.stdout.write(msg)
            else:
                msg = 'Successfully reenrolled {} users.'.format(total_users)
                log.info(msg)
                self.stdout.write(msg)

    def _reenroll_users_from_file(self, reenroll_file, course_key=None, mode=None):
        """
        Reenroll all the users provided in the users file.

        file format, example file:
            username,email
            <string:username>,<string:email>

        Arguments:
            coupons_file (str): path of the file containing the list of users to be reenrolled.

        Returns:
            (total_users, failed_users): a tuple containing count of users processed and a list containing users that could not be processed.
        """
        failed_users= []

        with open(reenroll_file, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            line_count = 0
            for row in csv_reader:
                if line_count == 0:
                    line_count += 1
                username=row['username']
                email_address=row['email']
                result = self._reenroll_user(username=username, email_address=email_address, course_key=course_key, course_name=course_name, mode=mode)
                if not result:
                    failed_users.append(row)
                    err_msg = u'Tried to process {}, but failed'
                    log.error(err_msg.format(row))
                line_count += 1
        return line_count-1, failed_users

    def _reenroll_user(self, username=None, email_address=None, course_key=None, course_name=None, mode=None):
        """ reenroll a user """
        try:
            tnow = timezone.now()
            uname = User.objects.get(username=username)
            enrollment = CourseEnrollment.enroll(uname, course_key, mode=mode, check_access=False)
            reenrollment = SpartaReEnrollment.objects.create(enrollment=enrollment,reenroll_date=tnow)
            email = EmailMessage(
                'Course Access Reenrollment',
                'This is a confirmation that you have been re-enrolled in {}.'.format(course_name),
                'learn@coursebank.ph',
                [email_address],
            )
            email.send()
        except Exception as e:
            log.info("Error in reenrolling learner: {}".format(str(e)))
            return False
        else:
            log.info("Successfully reenrolled learner: {}.".format(username))
            return True
