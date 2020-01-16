import csv
import os
from pprint import pformat

import logging
log = logging.getLogger(__name__)

from django.core.management.base import BaseCommand, CommandError

from sparta_pages.models import SpartaCoupon


class Command(BaseCommand):
    """
    This method creates single SpartaCoupon for each line of a file
    Example usage:
    $ ./manage.py migrate_sparta_coupons --coupons-file <absolute path of file with coupons (one per line after first line of columns labels)>
    file format, example file:
        code,course_id
        XXXXXXXXXXXX,course-v1:TestOrg+Test_4+2020_T1
    """
    help = 'Migrates coupons for each line of a file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--coupons-file',
            action='store',
            dest='coupons_file',
            default=None,
            help='Path of the file to read coupons from.',
            type=str,
            required=True
        )

    def handle(self, *args, **kwargs):
        coupons_file = kwargs['coupons_file']

        if coupons_file:
            if not os.path.exists(coupons_file):
                raise CommandError(u'Pass the correct absolute path to coupons file as --coupons-file argument.')

        total_coupons, failed_coupons = self._update_coupons_from_file(coupons_file)

        if failed_coupons:
            msg = u'Completed migration of coupons. {} of {} failed.'.format(
                len(failed_coupons),
                total_coupons
            )
            log.error(msg)
            self.stdout.write(msg)
            msg = 'Failed coupons:{}'.format(pformat(failed_coupons))
            log.error(msg)
            self.stdout.write(msg)
        else:
            msg = 'Successfully updated {} coupons.'.format(total_coupons)
            log.info(msg)
            self.stdout.write(msg)

    def _update_coupons_from_file(self, coupons_file):
        """
        Generate single coupons/vouchers for the coupon codes provided in the coupons file.

        file format, example file:
            code, course_id
            <string:XXXXXXXXXXXX>,<string:course_id>

        Arguments:
            coupons_file (str): path of the file containing coupon codes.

        Returns:
            (total_coupons, failed_coupons): a tuple containing count of coupons processed and a list containing coupons that could not be processed.
        """
        failed_coupons= []

        with open(coupons_file, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            line_count = 0
            for row in csv_reader:
                if line_count == 0:
                    line_count += 1
                code=row['code']
                course_id=row['course_id']
                result = self._create_single_coupon(code, course_id)
                if not result:
                    failed_coupons.append(row)
                    err_msg = u'Tried to process {}, but failed'
                    log.error(err_msg.format(row))
                line_count += 1
        return line_count-1, failed_coupons


    def _create_single_coupon(self, code, course_id):
        """ update coupon """
        try:
            coupon = SpartaCoupon.objects.get(code=code)
        except SpartaCoupon.DoesNotExist:
            coupon = SpartaCoupon.objects.create(
                code=code,
                course_id=course_id
            )
        else:
            log.info("coupon {} already exists!".format(code))
            return False

        log.info("Finished coupon creation for code {}!".format(code))
        return True
