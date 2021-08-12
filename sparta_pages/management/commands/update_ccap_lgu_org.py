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
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

from sparta_pages.models import SpartaProfile

class Command(BaseCommand):
    help = 'Unenroll user from course and send email notification.'

    def add_arguments(self, parser):
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
        csv_file = options.get('csv_file')

        if csv_file:
            if not os.path.exists(csv_file):
                raise CommandError(u'Pass the correct absolute path to file as --csv-file argument.')

            total_users, failed_users = self._update_spartausers_from_file(csv_file)

            if failed_users:
                msg = u'Completed updating spartausers. {} of {} failed.'.format(
                    len(failed_users),
                    total_users
                )
                log.error(msg)
                self.stdout.write(msg)
                msg = 'Failed users:{}'.format(pformat(failed_users))
                log.error(msg)
                self.stdout.write(msg)
            else:
                msg = 'Successfully updated {} spartausers.'.format(total_users)
                log.info(msg)
                self.stdout.write(msg)

    def _update_spartausers_from_file(self, unenroll_file):
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
                profile_id=row['id']
                username=row['username']
                ccap=row['ccap']
                org=row['org']
                lgu=row['lgu']
                result = self._update_spartauser(username=username, ccap=ccap, org=org, lgu=lgu)
                if not result:
                    failed_users.append(row)
                    err_msg = u'Tried to process {}, but failed'
                    log.error(err_msg.format(row))
                line_count += 1
        return line_count-1, failed_users

    def _update_spartauser(self, username=None, ccap=None, org=None, lgu=None):
        """ update lgu,ccap,org fields of spartauser """
        try:
            sparta_profile=SpartaProfile.objects.get(user=profile_id)

        except Exception as e:
            log.info("Sparta Learner Not Found: {}".format(str(e)))
            return False
        else:
            if sparta_profile.ccap_sub != ccap:
                sparta_profile.ccap_sub = ccap
            if sparta_profile.lgu_sub != lgu:
                sparta_profile.lgu_sub = lgu
            if sparta_profile.org != org:
                sparta_profile.org = org
            sparta_profile.save()            
            log.info("Successfully updated Sparta learner: {}.".format(username))
            return True
