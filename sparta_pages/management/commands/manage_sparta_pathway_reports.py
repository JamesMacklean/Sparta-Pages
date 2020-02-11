from django.core.management.base import BaseCommand, CommandError

from sparta_pages.utils import email_sparta_pathway_reports


class Command(BaseCommand):
    """
    3. Total no. of verified enrollees vs learning pathways
    3.1.  Affiliations/employment: industry, public sector, faculty, etc.
    3.3. Highest educational attainment
    3.2. Gender - Optional
    3.4. Area of residence (region, city/municipality) - Optional
    """
    help = 'Manages PathwayApplications'

    def add_arguments(self, parser):
        parser.add_argument(
            '-s',
            '--slug',
            type=str,
            help='Pathway slug',
        )

    def handle(self, *args, **options):
        slug = options.get('slug', None)

        if slug is None:
            raise CommandError("Error in getting pathway reports: -s/--slug arg is required")

        try:
            email_sparta_pathway_reports(slug)
        except Exception as e:
            raise CommandError("Error in getting pathway reports: {}".format(str(e)))

        self.stdout.write(self.style.SUCCESS("Successful in getting SPARTA Pathway Report."))
