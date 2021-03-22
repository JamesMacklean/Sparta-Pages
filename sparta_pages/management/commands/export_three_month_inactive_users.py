import csv
import os
from pprint import pformat
from datetime import datetime, timedelta
from django.utils import timezone

import logging
log = logging.getLogger(__name__)

from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment, UserProfile
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail, EmailMessage
from lms.djangoapps.certificates.api import get_certificate_for_user
from sparta_pages.models import (
    Pathway, SpartaCourse, SpartaProfile, ExtendedSpartaProfile,
    EducationProfile, EmploymentProfile, TrainingProfile,
    PathwayApplication, Event,
    SpartaCoupon, StudentCouponRecord, SpartaReEnrollment
)

class Command(BaseCommand):
    help = 'Exports list of users exceeding three months of inactivity to a course.'

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
            enrollments = CourseEnrollment.objects.filter(
                course_id=course_key,
                is_active=True,
                created__lt=date_filter,
            ).select_related('sparta_profile').prefetch_related('sparta_profile__applications')
            sec = 92*24*60*60

            tnow = timezone.now()
            date_filter = tnow - timedelta(seconds=sec)
            self.stdout.write("date_filter: {}".format(date_filter))

            user_list = []
            for e in enrollments:
                self.stdout.write("user length: {}".format(len(user_list)))
                self.stdout.write("current user being processed: {}".format(e.user.username))
                cert = get_certificate_for_user(e.user.username, course_key)
                if cert is not None:
                    continue
                    self.stdout.write("user with cert: {}".format(e.user.username))

                try:
                    profile = e.sparta_profile

                except SpartaProfile.DoesNotExist:
                    self.stdout.write("user with no sparta profile: {}".format(e.user.username))
                    continue

                applications = profile.applications.filter(status="AP")

                if applications.exists():
                    application = applications.order_by('-created_at').last()
                    pathway = application.pathway.name
                else:
                    pathway = ""

                check_date = e.user.last_login

                tdelta = tnow - check_date
                self.stdout.write("check date: {}".format(check_date))
                self.stdout.write("tdelta: {}".format(tdelta))

                if tdelta.seconds >= sec and cert is None:
                    self.stdout.write("user with more than 3 months and no cert: {}".format(e.user.username))
                    user_list.append({
                        "name": e.user.profile.name,
                        "email": e.user.email,
                        "username": e.user.username,
                        "pathway": pathway,
                        "last login": e.user.last_login.strftime("%Y-%m-%d"),
                    })

            file_name = '/home/ubuntu/tempfiles/export_three_month_inactive_users_{}.csv'.format(tnow)
            with open(file_name, mode='w') as csv_file:
                writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
                writer.writerow([
                    'Name',
                    'Email',
                    'Username',
                    'Pathway',
                    'Last Login Date'
                    ])

                for u in user_list:
                    writer.writerow([
                        u['name'],
                        u['email'],
                        u['username'],
                        u['pathway'],
                        u['last login'],
                    ])

            if email_address:
                email = EmailMessage(
                    'Coursebank - Three Month Inactive List',
                    'Attached file of Three Month Inactive List for {} (as of {})'.format(course_key,tnow),
                    'no-reply-sparta-user-logins@coursebank.ph',
                    [email_address,],
                )
                email.attach_file(file_name)
                email.send()

        except Exception as e:
            raise CommandError("Error in exporting three month inactive users: {}".format(str(e)))
        else:
            self.stdout.write(self.style.SUCCESS("Successfully exported three month inactive users."))
