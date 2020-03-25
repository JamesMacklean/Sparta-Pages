import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand, CommandError

from sparta_pages.models import SpartaProfile


class Command(BaseCommand):
    """
    This method deactivates SpartaProfiles for each line of a file
    Example usage:
    $ ./manage.py deactivate_sparta_profiles --user <username> --file <absolute path of file with usernames (one per line after first line of columns labels)>
    file format, example file:
        username
        coursebank_learner
    """
    help = 'Indicate file or username'

    def add_arguments(self, parser):
        parser.add_argument(
            '-f',
            '--file',
            action='store',
            dest='file',
            default=None,
            help='Path of the file to read usernames from.',
            type=str
        )
        parser.add_argument(
            '-u',
            '--user',
            dest='user',
            help='set username',
            type=str,
        )

    def handle(self, *args, **kwargs):
        users_file = kwargs.get('file', None)
        username = kwargs.get('user', None)

        if users_file is None and username is None:
            raise CommandError(u'At least one of --file or --user args required.')

        if users_file:
            if not os.path.exists(users_file):
                raise CommandError(u'Pass the correct absolute path to file as --file argument.')

            total_users, failed_users = self._update_users_from_file(users_file)

            if failed_users:
                msg = u'Deactivation of users. {} of {} failed.'.format(
                    len(failed_users),
                    total_users
                )
                log.error(msg)
                self.stdout.write(msg)
                msg = 'Failed users:{}'.format(pformat(failed_users))
                log.error(msg)
                self.stdout.write(msg)
            else:
                msg = 'Successfully deactivated {} users.'.format(total_users)
                log.info(msg)
                self.stdout.write(msg)
        elif username:
            is_success = self._deactivate_single_profile(username)
            if is_success:
                msg = 'Successfully deactivated user {}.'.format(username)
                log.info(msg)
                self.stdout.write(msg)
            else:
                msg = u'Deactivation of user {} failed.'.format(username)
                log.error(msg)
                self.stdout.write(msg)

    def _update_users_from_file(self, users_file):
        """
        file format, example file:
            username
            <string:username>

        Arguments:
            users_file (str): path of the file containing usernames.

        Returns:
            (total_users, failed_users): a tuple containing count of users processed and a list containing users that could not be processed.
        """
        failed_users= []

        with open(users_file, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            line_count = 0
            for row in csv_reader:
                if line_count == 0:
                    line_count += 1
                username=row['username']
                result = self._deactivate_single_profile(username)
                if not result:
                    failed_users.append(row)
                    err_msg = u'Tried to process {}, but failed'
                    log.error(err_msg.format(row))
                line_count += 1
        return line_count-1, failed_users


    def _deactivate_single_profile(self, username):
        """ deactivate SPARTA profile """
        try:
            profile = SpartaProfile.objects.get(user__username=username)
        except SpartaProfile.DoesNotExist:
            log.info("SpartaProfile for {} does not exist!".format(username))
            return False
        else:
            profile.deactivate()
            log.info("Finished deactivating SpartaProfile for user {}!".format(username))
            return True
