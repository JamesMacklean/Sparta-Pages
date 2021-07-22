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
from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

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
            '-a', '--aaction',
            type=str,
            required=False,
            help='additional action'
            )
        parser.add_argument(
            '-m', '--umode',
            type=str,
            required=False,
            help='unenrollment mode'
            )
        parser.add_argument(
            '-u', '--user',
            type=str,
            required=False,
            help='Username for user'
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
        aaction = options.get('aaction', None)
        umode = options.get('umode', None)
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
                unenrolled_user = self._unenroll_user(username=uname, email_address=uname.email, course_key=course_key, course_name=course_name, aaction=aaction)

                msg = 'Successfully unenrolled user: {}.'.format(unenrolled_user)
                log.info(msg)
                self.stdout.write(msg)

            except Exception as e:
                raise CommandError("Error in appending user to list: {}".format(str(e)))

        elif csv_file:
            if not os.path.exists(csv_file):
                raise CommandError(u'Pass the correct absolute path to file as --csv-file argument.')

            total_users, failed_users = self._unenroll_users_from_file(csv_file, umode=umode, course_key=course_key, course_name=course_name)

            if failed_users:
                msg = u'Completed unenrolling the users. {} of {} failed.'.format(
                    len(failed_users),
                    total_users
                )
                log.error(msg)
                self.stdout.write(msg)
                msg = 'Failed users:{}'.format(pformat(failed_users))
                log.error(msg)
                self.stdout.write(msg)
            else:
                msg = 'Successfully unenrolled {} users.'.format(total_users)
                log.info(msg)
                self.stdout.write(msg)

    def _unenroll_users_from_file(self, unenroll_file, umode=None, course_key=None, course_name=None):
        """
        Unenroll all the users provided in the users file.

        file format, example file:
            username,email
            <string:username>,<string:email>

        Arguments:
            coupons_file (str): path of the file containing the list of users to be unenrolled.

        Returns:
            (total_users, failed_users): a tuple containing count of users processed and a list containing users that could not be processed.
        """
        failed_users= []

        with open(unenroll_file, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            line_count = 0
            for row in csv_reader:
                if line_count == 0:
                    line_count += 1
                username=row['username']
                email_address=row['email']
                result = self._unenroll_user(username=username, umode=umode, email_address=email_address, course_key=course_key, course_name=course_name)
                if not result:
                    failed_users.append(row)
                    err_msg = u'Tried to process {}, but failed'
                    log.error(err_msg.format(row))
                line_count += 1
        return line_count-1, failed_users

    def _unenroll_user(self, username=None, umode=None, email_address=None, course_key=None, course_name=None, aaction=None):
        """ unenroll a user """
        try:
            uname = User.objects.get(username=username)
            CourseEnrollment.unenroll(uname, course_key, skip_refund=True)
            if aaction == "freeze":
                email = EmailMessage(
                    'Course Access Unenrollment',
                    'Your course access has been temporarily disabled due to certain concerns regarding the plagiarism concern raised by the SME: [WARNING] Adherence to Coursebank Honor Code, and you are now unenrolled in {}.\n\nPlease send your signed statement in PDF to the following email address:\n\nEmail : learn@coursebank.ph.\nRecipient : ALAN S. CAJES, PhD (Senior Executive Fellow and SPARTA Project Lead, Development Academy of the Philippines).\n\nPlease disregard this message if you already sent a statement regarding this issue.'.format(course_name),
                    'learn@coursebank.ph',
                    [email_address],
                )
            elif umode == "six_month" or umode == "three_month":
                message_body = """\
                    <html>
                        <head></head>
                        <body>
                            <P>Your course access has expired due to failure to complete it in 6 months OR you’ve been inactive for 3 months. You are now unenrolled from %s</p>
                            <p><b>How long can I complete a Project SPARTA course?</b><br>Upon enrollment, you have 6 months to finish a SPARTA course. Failure to complete the course in 6 months and/or inactivity for 3 months will result in course access revocation.</p>
                            <p>Please reply to this email OR fill out the <a href="https://forms.gle/wDLR6qgNukbTi5nC9">Learner Request Form</a> within five (5) business days should you wish to re-enroll in this course.</p>
                            <p>The CourseBank Team</p>
                        </body>
                    </html>
                    """ % (course_name)
                subject, from_email, to = 'Course Access Unenrollment', 'from@example.com', [email_address]
                text_content = 'Your course access has been temporarily disabled due to certain concerns regarding the plagiarism concern raised by the SME: [WARNING] Adherence to Coursebank Honor Code, and you are now unenrolled in {}.\n\nPlease send your signed statement in PDF to the following email address:\n\nEmail : learn@coursebank.ph.\nRecipient : ALAN S. CAJES, PhD (Senior Executive Fellow and SPARTA Project Lead, Development Academy of the Philippines).\n\nPlease disregard this message if you already sent a statement regarding this issue.'.format(course_name)
                email = EmailMultiAlternatives(subject, from email, text_content, [to])
                email.attach_alternative(message_body, "text/html")
            else:
                email = EmailMessage(
                    'Course Access Unenrollment',
                    'Your course access has expired, and you are now unenrolled in {}.\n\nThis is an auto-generated email. Please disregard this message if you requested for a re-enrollment.'.format(course_name),
                    'learn@coursebank.ph',
                    [email_address],
            )
            email.send()
        except Exception as e:
            log.info("Error in unenrolling learner: {}".format(str(e)))
            return False
        else:
            log.info("Successfully unenrolled learner: {}.".format(username))
            return True
