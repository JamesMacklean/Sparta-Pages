import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from sparta_pages.models import Pathway, SpartaProfile, PathwayApplication

User = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class Command(BaseCommand):
    """
    This method resets the applications for each line of a file
    Example usage:
    $ ./manage.py change_learning_pathway_applications --csv-file <absolute path of file with users (one per line after first line of columns labels)>
    file format, example file:
        username, email, pathway_id
        testuser, testuser@domain.com, 2
    """
    help = 'Resets applications of users for each line of a file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            action='store',
            dest='csv_file',
            default=None,
            help='Path of the file to read users from.',
            type=str,
            required=True
        )

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        if csv_file:
            if not os.path.exists(csv_file):
                raise CommandError(u'Pass the correct absolute path to file as --csv-file argument.')

        total_users, failed_users = self._reset_user_applications_from_file(csv_file)

        if failed_users:
            msg = u'Completed resetting of applications of users. {} of {} failed.'.format(
                len(failed_users),
                total_users
            )
            log.error(msg)
            self.stdout.write(msg)
            msg = 'Failed users:{}'.format(pformat(failed_users))
            log.error(msg)
            self.stdout.write(msg)
        else:
            msg = 'Successfully reset applications of {} users.'.format(total_users)
            log.info(msg)
            self.stdout.write(msg)

    def _reset_user_applications_from_file(self, csv_file):
        """
        Reset applications of users provided in the users file.

        file format, example file:
            username, email, pathway_id
            testuser, testuser@domain.com, 2

        Arguments:
            csv_file (str): path of the file containing users.

        Returns:
            (total_users, failed_users): a tuple containing count of users processed and a list containing users that could not be processed.
        """
        failed_users= []

        with open(csv_file, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            line_count = 0
            for row in csv_reader:
                if line_count == 0:
                    line_count += 1
                username=row['username']
                email_address=row['email']
                pathway_id=row['pathway_id']
                result = self._change_learning_pathway_applications(pathway_id, username=username, email_address=email_address)
                if not result:
                    failed_users.append(row)
                    err_msg = u'Tried to process {}, but failed'
                    log.error(err_msg.format(row))
                line_count += 1
        return line_count-1, failed_users


    def _change_learning_pathway_applications(self, pathway_id, username=None, email_address=None):
        """ update coupon """
        if username is not None:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                log.error("Error in resetting applications: User {} does not exist".format(username)
                return False
        elif email_address is not None:
            try:
                user = User.objects.get(email=email_address)
            except User.DoesNotExist:
                log.error("Error in resetting applications: User {} does not exist".format(email_address)
                return False
        else:
            return False

        try:
            pathway = Pathway.objects.get(id=pathway_id)
        except Pathway.DoesNotExist:
            log.error("Error in resetting applications: Pathway {} does not exist".format(pathway_id)
            return False

        try:
            for app in applications = PathwayApplication.objects.filter(profile__user=user):
                app.withdraw()
        except Exception as e:
            logger.error("Error in resetting applications: {}".format(str(e)))
            return False

        try:
            sparta_profile = SpartaProfile.objects.filter(is_active=True).get(user=user)
        except SpartaProfile.DoesNotExist:
            log.error("Error in resetting applications: SPARTA Profile for user {} does not exist".format(user.username)
            return False

        app, created = PathwayApplication.objects.get_or_create(profile=sparta_profile, pathway=pathway)
        app.approve()



        return True
