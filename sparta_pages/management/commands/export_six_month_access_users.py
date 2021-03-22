import csv
import os
from pprint import pformat
from datetime import datetime, timedelta

import logging
log = logging.getLogger(__name__)

from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment, UserProfile
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail, EmailMessage

from sparta_pages.models import SpartaReEnrollment


class Command(BaseCommand):
    help = 'Exports list of users exceeding six months of access to a course.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-e',
            '--email',
            type=str,
            help='set email to send to',
        )
        parser.add_argument(
            '-c',
            '--course',
            type=str,
            help='set filter for course_id',
        )

    def handle(self, *args, **options):
        course_id = options.get('course', None)
        email_address = options.get('email', None)

        if course_id is None:
            raise CommandError("--course -c arg required ")

        try:
            tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
            course_key = CourseKey.from_string(course_id)
            self.stdout.write("course_key: {}".format(course_key))
            users = User.objects.filter(courseenrollment__course__id=course_key).select_related('sparta_profile').prefetch_related('sparta_profile__applications')
            sec = 183*24*60*60

            tnow = timezone.now()
            date_filter = tnow - timedelta(seconds=sec)
            self.stdout.write("date_filter: {}".format(date_filter))

            user_list = []
            for u in users:
                cert = get_certificate_for_user(u.username, course_key)
                if cert is not None:
                    continue

                enrollments = CourseEnrollment.objects.filter(
                    course_id=course_key,
                    is_active=True,
                    created__lt=date_filter,
                )
                try:
                    profile = u.sparta_profile

                except SpartaProfile.DoesNotExist:
                    continue

                applications = profile.applications.filter(status="AP")

                if applications.exists():
                    application = applications.order_by('-created_at').last()
                    pathway = application.pathway.name
                    self.stdout.write("pathway: {}".format(pathway))

                for e in enrollments:
                    reenrollments = SpartaReEnrollment.objects.filter(enrollment=e)
                    self.stdout.write("e.user.username: {}".format(e.user.username))
                    if reenrollments.exists():
                        lastest_reenrollment = reenrollments.order_by('-reenroll_date').first()
                        check_date = lastest_reenrollment.reenroll_date
                    else:
                        check_date = e.created

                    tdelta = tnow - check_date
                    self.stdout.write("check date: {}".format(check_date))
                    self.stdout.write("tdelta: {}".format(tdelta))

                    if tdelta.seconds >= sec and cert is None:
                        user_list.append({
                            "name": e.user.name,
                            "email": e.user.email,
                            "username": e.user.username,
                            "pathway": pathway,
                            "access date": check_date.strftime("%Y-%m-%d"),
                        })

            file_name = '/home/ubuntu/tempfiles/export_six_month_access_users_{}.csv'.format(tnow)
            with open(file_name, mode='w') as csv_file:
                writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
                writer.writerow([
                    'Name',
                    'Email',
                    'Username',
                    'Pathway',
                    'Initial Access Date'
                    ])

                for u in user_list:
                    writer.writerow([
                        u['name'],
                        u['email'],
                        u['username'],
                        u['pathway'],
                        u['access date'],
                    ])

            if email_address:
                email = EmailMessage(
                    'Coursebank - Six Month Access List',
                    'Attached file of Six Month Access List for {} (as of {})'.format(course_key,tnow),
                    'no-reply-sparta-user-logins@coursebank.ph',
                    [email_address,],
                )
                email.attach_file(file_name)
                email.send()

        except Exception as e:
            raise CommandError("Error in exporting six month access users: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully exported six month access users."))
