import csv
import unicodecsv

from datetime import datetime, timedelta, date
from os import path
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from lms.djangoapps.certificates.models import certificate_status_for_student

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment

from ..analytics import OverallAnalytics, PathwayAnalytics, CourseAnalytics
from ..forms import (
    ExportAppsForm, FilterForm, ExportProfilesForm,
    ExportAnalyticsForm, ExportPathwayAnalyticsForm
)
from ..local_settings import LOCAL_TEST
from ..models import (
    Pathway, SpartaCourse, SpartaProfile, ExtendedSpartaProfile,
    EducationProfile, EmploymentProfile, TrainingProfile,
    PathwayApplication, APIToken
)


class DeveloperProfileView(TemplateView):
    """
    path: /sparta/dev/profile/
    """
    template_name = 'sparta_developer_profile.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(DeveloperProfileView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        try:
            token = APIToken.objects.get(user=request.user)
        except APIToken.DoesNotExist:
            token = None

        context['token'] = token

        return render(request, self.template_name, context)


@login_required
def admin_main_view(request):
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_admin_main.html"
    context = {}

    return render(request, template_name, context)


@login_required
def admin_applications_view(request):
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_admin_applications.html"
    context = {}

    date_from = timezone.now().date() - timedelta(days=1)
    date_to = timezone.now()

    date_from_year = request.GET.get('date_from_year', None)
    date_from_month = request.GET.get('date_from_month', None)
    date_from_day = request.GET.get('date_from_day', None)
    if None not in [date_from_year, date_from_month, date_from_day]:
        date_from_str = "{}-{}-{}".format(date_from_year, date_from_month, date_from_day)
        date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()

    date_to_year = request.GET.get('date_to_year', None)
    date_to_month = request.GET.get('date_to_month', None)
    date_to_day = request.GET.get('date_to_day', None)
    if None not in [date_to_year, date_to_month, date_to_day]:
        date_to_str = "{}-{}-{}".format(date_to_year, date_to_month, date_to_day)
        date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()

    applications = PathwayApplication.objects.all().filter(created_at__gte=date_from).filter(created_at__lte=date_to)

    pending_applications = applications.filter(status='PE')
    withdrawn_applications = applications.filter(status='WE')
    denied_applications = applications.filter(status='DE')
    approved_applications = applications.filter(status='AP')

    context['pending_applications'] = pending_applications
    context['approved_applications'] = approved_applications
    context['withdrawn_applications'] = withdrawn_applications
    context['denied_applications'] = denied_applications

    context['form'] = ExportAppsForm()
    context['filter_form'] = FilterForm(request.GET or None)

    if request.method == "POST":
        form = ExportAppsForm(request.POST)
        if form.is_valid():
            selection = form.cleaned_data['selection']
            if selection == "pending":
                apps_to_export = pending_applications
            elif selection == "approved":
                apps_to_export = approved_applications
            elif selection == "withdrawn":
                apps_to_export = withdrawn_applications
            elif selection == "denied":
                apps_to_export = denied_applications
            else:
                apps_to_export = applications
            return export_pathway_applications_to_csv(apps_to_export)

    return render(request, template_name, context)

def export_pathway_applications_to_csv(apps):
    tnow = timezone.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
    filename = "sparta-pathway-applications-{}.csv".format(tnow)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

    writer = unicodecsv.writer(response, encoding='utf-8')
    writer.writerow(['username', 'email', 'pathway', 'status', 'created_at'])
    for a in apps:
        username = a.profile.user.username
        email = a.profile.user.email
        pathway = a.pathway.name
        status = a.status
        created_at = str(a.created_at)
        writer.writerow([username, email, pathway, status, created_at])

    return response


@require_POST
def admin_approve_application_view(request, id):
    if not request.user.is_staff:
        raise HttpResponse(status=500)

    try:
        app = PathwayApplication.objects.get(id=id)
    except PathwayApplication.DoesNotExist:
        raise HttpResponse(status=500)
    else:
        app.approve()

    return redirect('sparta-admin-applications')


def export_profiles_to_csv(profiles):
    tnow = timezone.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
    filename = "sparta-scholar-credentials-{}.csv".format(tnow)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

    writer = unicodecsv.writer(response, encoding='utf-8')
    writer.writerow(['Username', 'Email Address', 'Full Name', 'Approved Pathways', 'Is Active'])
    for profile in profiles:
        username = profile['username']
        email = profile['email']
        full_name = profile['full_name']
        # full_name = profile['full_name'].decode('utf-8').replace(u"\xf1", "n").replace(u"\xd1", "N")
        approved_pathways_str = ""
        for p in profile['approved_pathways']:
            approved_pathways_str = "{}{} | ".format(approved_pathways_str, p.pathway.name)
        is_active_str = "True" if profile['is_active'] else "False"

        writer.writerow([username, email, full_name, approved_pathways_str[:-3], is_active_str])

    return response


@login_required
def admin_profiles_view(request):
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_admin_profiles.html"
    context = {}

    date_from = timezone.now().date() - timedelta(days=1)
    date_to = timezone.now()

    date_from_year = request.GET.get('date_from_year', None)
    date_from_month = request.GET.get('date_from_month', None)
    date_from_day = request.GET.get('date_from_day', None)
    if None not in [date_from_year, date_from_month, date_from_day]:
        date_from_str = "{}-{}-{}".format(date_from_year, date_from_month, date_from_day)
        date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()

    date_to_year = request.GET.get('date_to_year', None)
    date_to_month = request.GET.get('date_to_month', None)
    date_to_day = request.GET.get('date_to_day', None)
    if None not in [date_to_year, date_to_month, date_to_day]:
        date_to_str = "{}-{}-{}".format(date_to_year, date_to_month, date_to_day)
        date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()

    profiles = []
    for profile in SpartaProfile.objects.filter(created_at__gte=date_from).filter(created_at__lte=date_to):
        data = {
            'id': profile.id,
            'username': profile.user.username,
            'email': profile.user.email,
            'full_name': profile.user.profile.name,
            'approved_pathways': profile.applications.all().filter(status='AP'),
            'is_active': profile.is_active
        }
        profiles.append(data)
    if request.method == "POST":
        form = ExportProfilesForm(request.POST)
        if form.is_valid():
            return export_profiles_to_csv(profiles)

    context['form'] = ExportProfilesForm()
    context['profiles'] = profiles
    context['filter_form'] = FilterForm(request.GET or None)

    return render(request, template_name, context)


@login_required
def admin_credentials_view(request, id):
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_admin_credentials.html"
    context = {}

    profile = get_object_or_404(SpartaProfile, id=id)
    context['profile'] = profile
    context['education_profiles'] = profile.education_profiles.all()
    context['employment_profiles'] = profile.employment_profiles.all()
    context['training_profiles'] = profile.training_profiles.all()
    return render(request, template_name, context)


@login_required
def admin_overall_analytics_view(request):
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_admin_overall_analytics.html"

    date_from = timezone.now().date() - timedelta(days=1)
    date_to = timezone.now()

    date_from_year = request.GET.get('date_from_year', None)
    date_from_month = request.GET.get('date_from_month', None)
    date_from_day = request.GET.get('date_from_day', None)
    if None not in [date_from_year, date_from_month, date_from_day]:
        date_from_str = "{}-{}-{}".format(date_from_year, date_from_month, date_from_day)
        date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()

    date_to_year = request.GET.get('date_to_year', None)
    date_to_month = request.GET.get('date_to_month', None)
    date_to_day = request.GET.get('date_to_day', None)
    if None not in [date_to_year, date_to_month, date_to_day]:
        date_to_str = "{}-{}-{}".format(date_to_year, date_to_month, date_to_day)
        date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()

    # analytics = OverallAnalytics(date_from, date_to)
    analytics = OverallAnalytics()
    learners = analytics.queryset()

    overall_no_of_registered_sparta_learners = analytics.learners.count()
    overall_no_of_enrollees = analytics.overall_no_of_enrollees()
    overall_no_of_learners_in_progress = analytics.overall_no_of_learners_in_progress()
    percent_of_learners_in_progress = analytics.percent_of_learners_in_progress()
    overall_no_of_active_learners = analytics.overall_no_of_active_learners()
    percent_of_active_learners = analytics.percent_of_active_learners()
    overall_no_of_inactive_learners = analytics.overall_no_of_inactive_learners()
    percent_of_inactive_learners = analytics.percent_of_inactive_learners()
    overall_no_of_dropped_out_learners = analytics.overall_no_of_dropped_out_learners()
    overall_dropout_rate = analytics.overall_dropout_rate()
    overall_no_of_graduates = analytics.overall_no_of_graduates()
    overall_graduation_rate = analytics.overall_graduation_rate()
    context = {
        'analytics': analytics,
        'learners': learners,
        'overall_no_of_registered_sparta_learners': overall_no_of_registered_sparta_learners,
        'overall_no_of_enrollees': overall_no_of_enrollees,
        'overall_no_of_learners_in_progress': overall_no_of_learners_in_progress,
        'percent_of_learners_in_progress': percent_of_learners_in_progress,
        'overall_no_of_active_learners': overall_no_of_active_learners,
        'percent_of_active_learners': percent_of_active_learners,
        'overall_no_of_inactive_learners': overall_no_of_inactive_learners,
        'percent_of_inactive_learners': percent_of_inactive_learners,
        'overall_no_of_dropped_out_learners': overall_no_of_dropped_out_learners,
        'overall_dropout_rate': overall_dropout_rate,
        'overall_no_of_graduates': overall_no_of_graduates,
        'overall_graduation_rate': overall_graduation_rate,
        'local_test': LOCAL_TEST
    }

    if request.method == "POST":
        form = ExportProfilesForm(request.POST)
        if form.is_valid():
            tnow = timezone.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
            filename = "sparta-overall-analytics-{}.csv".format(tnow)
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

            writer = unicodecsv.writer(response, encoding='utf-8')
            writer.writerow([
                'Timestamp',
                'Overall Number of Registered SPARTA Learners',
                'Overall Number of Enrollees',
                'Overall Number of Learners in Progress',
                'Percent of Learners in Progress',
                'Overall Number of Active Learners',
                'Percent of Active Learners',
                'Overall Number of Inactive Learners',
                'Percent of Inactive Learners',
                'Overall Number of Dropped Out Learners',
                'Overall Dropout Rate',
                'Overall Number of Graduates',
                'Overall Graduation Rate'
                ])
            writer.writerow([
                tnow,
                overall_no_of_registered_sparta_learners,
                overall_no_of_enrollees,
                overall_no_of_learners_in_progress,
                percent_of_learners_in_progress,
                overall_no_of_active_learners,
                percent_of_active_learners,
                overall_no_of_inactive_learners,
                percent_of_inactive_learners,
                overall_no_of_dropped_out_learners,
                overall_dropout_rate,
                overall_no_of_graduates,
                overall_graduation_rate
                ])
            return response

    context['form'] = ExportAnalyticsForm()
    context['filter_form'] = FilterForm(request.GET or None)

    pathways = []
    for pathway in Pathway.objects.filter(is_active=True):
        courses = []
        for course in pathway.courses.all().filter(is_active=True):
            course_key = CourseKey.from_string(course.course_id)
            courseoverview = CourseOverview.get_from_id(course_key)
            courses.append({'courseoverview': courseoverview, 'sparta_course': course})
        pathways.append({
            'pathway': pathway,
            'courses': courses
        })
    context['pathways'] = pathways

    return render(request, template_name, context)


@login_required
def admin_pathway_analytics_view(request, slug):
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_admin_pathway_analytics.html"

    try:
        pathway = Pathway.objects.get(slug=slug)
    except Pathway.DoesNotExist:
        raise Http404

    date_from = timezone.now().date() - timedelta(days=1)
    date_to = timezone.now()

    date_from_year = request.GET.get('date_from_year', None)
    date_from_month = request.GET.get('date_from_month', None)
    date_from_day = request.GET.get('date_from_day', None)
    if None not in [date_from_year, date_from_month, date_from_day]:
        date_from_str = "{}-{}-{}".format(date_from_year, date_from_month, date_from_day)
        date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()

    date_to_year = request.GET.get('date_to_year', None)
    date_to_month = request.GET.get('date_to_month', None)
    date_to_day = request.GET.get('date_to_day', None)
    if None not in [date_to_year, date_to_month, date_to_day]:
        date_to_str = "{}-{}-{}".format(date_to_year, date_to_month, date_to_day)
        date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()

    analytics = PathwayAnalytics(pathway, start=date_from, end=date_to)

    learners = analytics.queryset()

    no_of_pathway_enrollees = analytics.no_of_pathway_enrollees()
    no_of_pathway_learners_in_progress = analytics.no_of_pathway_learners_in_progress()
    percent_of_pathway_learners_in_progress = analytics.percent_of_pathway_learners_in_progress()
    no_of_active_pathway_learners = analytics.no_of_active_pathway_learners()
    percent_of_active_pathway_learners = analytics.percent_of_active_pathway_learners()
    no_of_inactive_pathway_learners = analytics.no_of_inactive_pathway_learners()
    percent_of_inactive_pathway_learners = analytics.percent_of_inactive_pathway_learners()
    no_of_dropped_out_pathway_learners = analytics.no_of_dropped_out_pathway_learners()
    pathway_dropout_rate = analytics.pathway_dropout_rate()
    no_of_pathway_graduates = analytics.no_of_pathway_graduates()
    pathway_graduation_rate = analytics.pathway_graduation_rate()

    if request.method == "POST":
        form = ExportPathwayAnalyticsForm(request.POST)
        if form.is_valid():
            choice = form.cleaned_data['choice']
            if choice == 'Totals':
                data = {
                        'pathway': pathway,
                        'no_of_pathway_enrollees': no_of_pathway_enrollees,
                        'no_of_pathway_learners_in_progress': no_of_pathway_learners_in_progress,
                        'percent_of_pathway_learners_in_progress': percent_of_pathway_learners_in_progress,
                        'no_of_active_pathway_learners': no_of_active_pathway_learners,
                        'percent_of_active_pathway_learners': percent_of_active_pathway_learners,
                        'no_of_inactive_pathway_learners': no_of_inactive_pathway_learners,
                        'percent_of_inactive_pathway_learners': percent_of_inactive_pathway_learners,
                        'no_of_dropped_out_pathway_learners': no_of_dropped_out_pathway_learners,
                        'pathway_dropout_rate': pathway_dropout_rate,
                        'no_of_pathway_graduates': no_of_pathway_graduates,
                        'pathway_graduation_rate': pathway_graduation_rate
                    }
                return export_pathway_analytics_to_csv(pathway, data)
            elif choice == 'Learners':
                return export_pathway_learners_data_to_csv(pathway, learners)

    context = {
        'pathway': pathway,
        'no_of_pathway_enrollees': no_of_pathway_enrollees,
        'no_of_pathway_learners_in_progress': no_of_pathway_learners_in_progress,
        'percent_of_pathway_learners_in_progress': percent_of_pathway_learners_in_progress,
        'no_of_active_pathway_learners': no_of_active_pathway_learners,
        'percent_of_active_pathway_learners': percent_of_active_pathway_learners,
        'no_of_inactive_pathway_learners': no_of_inactive_pathway_learners,
        'percent_of_inactive_pathway_learners': percent_of_inactive_pathway_learners,
        'no_of_dropped_out_pathway_learners': no_of_dropped_out_pathway_learners,
        'pathway_dropout_rate': pathway_dropout_rate,
        'no_of_pathway_graduates': no_of_pathway_graduates,
        'pathway_graduation_rate': pathway_graduation_rate
    }
    context['form'] = ExportPathwayAnalyticsForm()
    context['filter_form'] = FilterForm(request.GET or None)

    return render(request, template_name, context)


def export_pathway_analytics_to_csv(pathway, data):
    tnow = timezone.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
    filename = "sparta-pathway-{}-analytics-{}.csv".format(str(pathway.slug), tnow)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

    writer = unicodecsv.writer(response, encoding='utf-8')
    writer.writerow([
        'Timestamp',
        'Pathway',
        'Number of Pathway Enrollees',
        'Number of Pathway Learners in Progress',
        'Percent of Pathway Learners in Progress',
        'Number of Active Pathway Learners',
        'Percent of Active Pathway Learners',
        'Number of Inactive Pathway Learners',
        'Percent of Inactive Pathway Learners',
        'Number of Dropped Out Pathway Learners',
        'Pathway Dropout Rate',
        'Number of Pathway Graduates',
        'Pathway Graduation Rate'
        ])
    writer.writerow([
        tnow,
        str(pathway.slug),
        data.get('no_of_pathway_enrollees', ""),
        data.get('no_of_pathway_learners_in_progress', ""),
        data.get('percent_of_pathway_learners_in_progress', ""),
        data.get('no_of_active_pathway_learners', ""),
        data.get('percent_of_active_pathway_learners', ""),
        data.get('no_of_inactive_pathway_learners', ""),
        data.get('percent_of_inactive_pathway_learners', ""),
        data.get('no_of_dropped_out_pathway_learners', ""),
        data.get('pathway_dropout_rate', ""),
        data.get('no_of_pathway_graduates', ""),
        data.get('pathway_graduation_rate', "")
        ])
    return response

def export_pathway_learners_data_to_csv(pathway, learners):
    tnow = timezone.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
    filename = "sparta-{}-pathway-learners-data-{}.csv".format(pathway.slug, tnow)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

    writer = unicodecsv.writer(response, encoding='utf-8')
    writer.writerow([
        '#',
        'Affiliation',
        'Highest Educational Attainment',
        'Gender',
        'Area of Residence'
        ])

    count = 0
    for learner in learners:
        count += 1
        if learner.extended_profile:
            affiliation = learner.extended_profile.get_affiliation_display()
            attainment = learner.extended_profile.get_attainment_display()
        else:
            affiliation = ""
            attainment = learner.user.profile.get_level_of_education_display() or ""

        writer.writerow([
            count,
            affiliation,
            attainment,
            learner.user.profile.get_gender_display(),
            learner.user.profile.city
            ])
    return response


@login_required
def admin_course_analytics_view(request, course_id):
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_admin_course_analytics.html"

    courses = SpartaCourse.objects.filter(is_active=True).filter(course_id=course_id)
    if courses.exists():
        course = courses[0]
    else:
        raise Http404

    date_from = timezone.now().date() - timedelta(days=1)
    date_to = timezone.now()

    date_from_year = request.GET.get('date_from_year', None)
    date_from_month = request.GET.get('date_from_month', None)
    date_from_day = request.GET.get('date_from_day', None)
    if None not in [date_from_year, date_from_month, date_from_day]:
        date_from_str = "{}-{}-{}".format(date_from_year, date_from_month, date_from_day)
        date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()

    date_to_year = request.GET.get('date_to_year', None)
    date_to_month = request.GET.get('date_to_month', None)
    date_to_day = request.GET.get('date_to_day', None)
    if None not in [date_to_year, date_to_month, date_to_day]:
        date_to_str = "{}-{}-{}".format(date_to_year, date_to_month, date_to_day)
        date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()

    analytics = CourseAnalytics(course, start=date_from, end=date_to)

    no_of_course_enrollees = analytics.no_of_course_enrollees()
    no_of_learners_in_progress = analytics.no_of_learners_in_progress()
    percent_of_learners_in_progress = analytics.percent_of_learners_in_progress()
    no_of_active_learners = analytics.no_of_active_learners()
    percent_of_active_learners = analytics.percent_of_active_learners()
    no_of_inactive_learners = analytics.no_of_inactive_learners()
    percent_of_inactive_learners = analytics.percent_of_inactive_learners()
    no_of_dropped_out_learners = analytics.no_of_dropped_out_learners()
    dropout_rate = analytics.dropout_rate()
    no_of_completed_learners = analytics.no_of_completed_learners()
    completion_rate = analytics.completion_rate()

    context = {
        'course': course,
        'courseoverview': CourseOverview.get_from_id(CourseKey.from_string(course.course_id)),
        'no_of_course_enrollees': no_of_course_enrollees,
        'no_of_learners_in_progress': no_of_learners_in_progress,
        'percent_of_learners_in_progress': percent_of_learners_in_progress,
        'no_of_active_learners': no_of_active_learners,
        'percent_of_active_learners': percent_of_active_learners,
        'no_of_inactive_learners': no_of_inactive_learners,
        'percent_of_inactive_learners': percent_of_inactive_learners,
        'no_of_dropped_out_learners': no_of_dropped_out_learners,
        'dropout_rate': dropout_rate,
        'no_of_completed_learners': no_of_completed_learners,
        'completion_rate': completion_rate
    }

    if request.method == "POST":
        form = ExportAnalyticsForm(request.POST)
        if form.is_valid():
            tnow = timezone.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
            filename = "sparta-pathway-{}-analytics-{}.csv".format(course_id, tnow)
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

            writer = unicodecsv.writer(response, encoding='utf-8')
            writer.writerow([
                'Timestamp',
                'Course_id',
                'Number of Course Enrollees',
                'Number of Learners in Progress',
                'Percent of Learners in Progress',
                'Number of Active Learners',
                'Percent of Active Learners',
                'Number of Inactive Learners',
                'Percent of Inactive Learners',
                'Number of Dropped Out Learners',
                'Dropout Rate',
                'Number of Completed Learners',
                'Completion Rate'
                ])
            writer.writerow([
                tnow,
                course_id,
                no_of_course_enrollees,
                no_of_learners_in_progress,
                percent_of_learners_in_progress,
                no_of_active_learners,
                percent_of_active_learners,
                no_of_inactive_learners,
                percent_of_inactive_learners,
                no_of_dropped_out_learners,
                dropout_rate,
                no_of_completed_learners,
                completion_rate
                ])
            return response

    context['form'] = ExportAnalyticsForm()
    context['filter_form'] = FilterForm(request.GET or None)

    return render(request, template_name, context)


###################
# Data Dashboard #
#################

@login_required
def data_dashboard_main_view(request):
    """"""
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_data_dashboard_main.html"
    context = {}
    return render(request, template_name, context)


@login_required
def data_dashboard_profiles_view(request):
    """"""
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_data_dashboard_profiles.html"

    profiles = SpartaProfile.objects.all()

    search_term = request.GET.get('q', None)
    if search_term is not None:
        profiles = profiles.filter(Q(user__username__icontains=search_term) | Q(user__email__icontains=search_term)).distinct()

    student_list = []
    for profile in profiles:
        data = {}
        is_active = "True" if profile.is_active else "False"
        try:
            eprofile = ExtendedSpartaProfile.objects.get(user=profile.user)
        except ExtendedSpartaProfile.DoesNotExist:
            address = affiliation = attainment = other_attain = is_employed = grad_degree = ""
        else:
            address = eprofile.address
            municipality = eprofile.get_municipality_display()
            affiliation = eprofile.get_affiliation_display()
            attainment = eprofile.get_attainment_display()
            other_attain = eprofile.other_attain
            is_employed = eprofile.is_employed
            grad_degree = eprofile.get_grad_degree_display()
        student_list.append({
            "username": profile.user.username,
            "email": profile.user.email,
            "is_active": profile.is_active,
            "name": profile.user.profile.name,
            "gender": profile.user.profile.get_gender_display(),
            "address": address,
            "municipality": municipality,
            "affiliation": affiliation,
            "attainment": attainment,
            "other_attain": other_attain,
            "is_employed": is_employed,
            "grad_degree": grad_degree
        })

    paginator = Paginator(student_list, 100)
    page = request.GET.get('page')
    try:
        students = paginator.page(page)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)

    context = {
        "profiles": students,
    }
    return render(request, template_name, context)


@login_required
def data_dashboard_education_credentials_view(request):
    """"""
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_data_dashboard_education_credentials.html"

    education_profiles = EducationProfile.objects.all()

    search_term = request.GET.get('q', None)
    if search_term is not None:
        education_profiles = education_profiles.filter(Q(profile__user__username__icontains=search_term) | Q(profile__user__email__icontains=search_term)).distinct()

    credentials_list = []
    for profile in education_profiles:
        credentials_list.append({
            "username": profile.profile.user.username,
            "email": profile.profile.user.email,
            "name": profile.profile.user.profile.name,
            "degree": profile.get_degree_display(),
            "course": profile.course,
            "school": profile.school,
            "address": profile.address,
            "started": profile.started_at.strftime('%Y-%m-%d'),
            "graduated": profile.graduated_at.strftime('%Y-%m-%d')
        })

    paginator = Paginator(credentials_list, 100)
    page = request.GET.get('page')
    try:
        education_credentials = paginator.page(page)
    except PageNotAnInteger:
        education_credentials = paginator.page(1)
    except EmptyPage:
        education_credentials = paginator.page(paginator.num_pages)

    context = {
        "education_credentials": education_credentials,
    }
    return render(request, template_name, context)


@login_required
def data_dashboard_employment_credentials_view(request):
    """"""
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_data_dashboard_employment_credentials.html"

    employment_profiles = EmploymentProfile.objects.all()

    search_term = request.GET.get('q', None)
    if search_term is not None:
        employment_profiles = employment_profiles.filter(Q(profile__user__username__icontains=search_term) | Q(profile__user__email__icontains=search_term)).distinct()

    credentials_list = []
    for profile in employment_profiles:
        ended = profile.ended_at
        if ended is not None:
            ended = profile.ended_at.strftime('%Y-%m-%d')
        credentials_list.append({
            "username": profile.profile.user.username,
            "email": profile.profile.user.email,
            "name": profile.profile.user.profile.name,
            "affiliation": profile.get_affiliation_display(),
            "occupation": profile.occupation,
            "designation": profile.designation,
            "employer": profile.employer,
            "address": profile.address,
            "started": profile.started_at.strftime('%Y-%m-%d'),
            "ended": ended
        })

    paginator = Paginator(credentials_list, 100)
    page = request.GET.get('page')
    try:
        employment_credentials = paginator.page(page)
    except PageNotAnInteger:
        employment_credentials = paginator.page(1)
    except EmptyPage:
        employment_credentials = paginator.page(paginator.num_pages)

    context = {
        "employment_credentials": employment_credentials,
    }
    return render(request, template_name, context)


@login_required
def data_dashboard_training_credentials_view(request):
    """"""
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_data_dashboard_training_credentials.html"

    training_profiles = TrainingProfile.objects.all()

    search_term = request.GET.get('q', None)
    if search_term is not None:
        training_profiles = training_profiles.filter(Q(profile__user__username__icontains=search_term) | Q(profile__user__email__icontains=search_term)).distinct()

    credentials_list = []
    for profile in training_profiles:
        credentials_list.append({
            "username": profile.profile.user.username,
            "email": profile.profile.user.email,
            "name": profile.profile.user.profile.name,
            "title": profile.title,
            "organizer": profile.organizer,
            "address": profile.address,
            "started": profile.started_at.strftime('%Y-%m-%d'),
            "ended": profile.ended_at.strftime('%Y-%m-%d')
        })

    paginator = Paginator(credentials_list, 100)
    page = request.GET.get('page')
    try:
        training_credentials = paginator.page(page)
    except PageNotAnInteger:
        training_credentials = paginator.page(1)
    except EmptyPage:
        training_credentials = paginator.page(paginator.num_pages)

    context = {
        "training_credentials": training_credentials,
    }
    context = {}
    return render(request, template_name, context)


@login_required
def data_dashboard_courses_view(request):
    """"""
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_data_dashboard_courses.html"

    course_id_list = []
    for course in SpartaCourse.objects.filter(is_active=True):
        if course.course_id not in course_id_list:
            course_id_list.append(course.course_id)

    courses = []
    for course_id in course_id_list:
        data = {}
        data['course_id'] = course_id

        course_key = CourseKey.from_string(course_id)
        courseoverview = CourseOverview.get_from_id(course_key)
        data['name'] = courseoverview.display_name

        course_enrollments = CourseEnrollment.objects.filter(course=courseoverview).filter(is_active=True)
        enrollments = course_enrollments.filter(mode__in=['verified', 'honor'])

        cert_count = 0
        for student in enrollments:
            cert_status = certificate_status_for_student(student.user, course_key)
            if cert_status and cert_status['mode'] == 'verified' or cert_status and cert_status['mode'] == 'honor':
                if cert_status['status'] not in  ['unavailable', 'notpassing', 'restricted', 'unverified']:
                    cert_count += 1
        data['no_of_completed'] = cert_count
        total_enrollments_count = enrollments.count()
        data['percent_completed'] = str( 100*(cert_count / total_enrollments_count) ) if total_enrollments_count else "0"
        courses.append(data)

    context = {
        "courses": courses,
    }
    return render(request, template_name, context)


#########################
# TEST: Data Dashboard #
#######################

@login_required
def test_data_dashboard_profiles_view(request):
    """"""
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_data_dashboard_profiles.html"

    student_list = []
    for i in range(1, 26):
        student_list.append({
            "username": "username-{}".format(i),
            "email": "email{}@example.com".format(i),
            "is_active": "True/False",
            "name": "Name {}".format(i),
            "gender": "Male/Female",
            "address": "Address {}".format(i),
            "municipality": "NCR/OTHER",
            "affiliation": "PRIVATE/PUBLIC",
            "attainment": "ELEMENTARY/SECONDARY/TERIARY",
            "other_attain": "OTHER",
            "is_employed": "True/False",
            "grad_degree": "Doctorate/Master's/No"
        })

    paginator = Paginator(student_list, 10)
    page = request.GET.get('page')
    try:
        students = paginator.page(page)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)

    context = {
        "profiles": students,
    }
    return render(request, template_name, context)


@login_required
def test_data_dashboard_education_credentials_view(request):
    """"""
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_data_dashboard_education_credentials.html"

    credentials_list = []
    for i in range(1, 26):
        credentials_list.append({
            "username": "username-{}".format(i),
            "email": "email{}@example.com".format(i),
            "name": "Name {}".format(i),
            "degree": "SECONDARY/BACHELOR/MASTER/DOCTOR",
            "course": "BS/MS/PHD Course",
            "school": "School Name {}".format(i),
            "address": "Address {}".format(i),
            "started": timezone.now().date().strftime('%Y-%m-%d'),
            "graduated": timezone.now().date().strftime('%Y-%m-%d')
        })

    paginator = Paginator(credentials_list, 10)
    page = request.GET.get('page')
    try:
        education_credentials = paginator.page(page)
    except PageNotAnInteger:
        education_credentials = paginator.page(1)
    except EmptyPage:
        education_credentials = paginator.page(paginator.num_pages)

    context = {
        "education_credentials": education_credentials,
    }
    return render(request, template_name, context)


@login_required
def test_data_dashboard_employment_credentials_view(request):
    """"""
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_data_dashboard_employment_credentials.html"

    credentials_list = []
    for i in range(1, 26):
        credentials_list.append({
            "username": "username-{}".format(i),
            "email": "email{}@example.com".format(i),
            "name": "Name {}".format(i),
            "affiliation": "Academe/Private/Government",
            "occupation": "Occupation {}".format(i),
            "designation": "Designation {}".format(i),
            "employer": "Employer Name {}".format(i),
            "address": "Address {}".format(i),
            "started": timezone.now().date().strftime('%Y-%m-%d'),
            "ended": timezone.now().date().strftime('%Y-%m-%d')
        })

    paginator = Paginator(credentials_list, 10)
    page = request.GET.get('page')
    try:
        employment_credentials = paginator.page(page)
    except PageNotAnInteger:
        employment_credentials = paginator.page(1)
    except EmptyPage:
        employment_credentials = paginator.page(paginator.num_pages)

    context = {
        "employment_credentials": employment_credentials,
    }
    return render(request, template_name, context)


@login_required
def test_data_dashboard_training_credentials_view(request):
    """"""
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_data_dashboard_training_credentials.html"

    credentials_list = []
    for i in range(1, 26):
        credentials_list.append({
            "username": "username-{}".format(i),
            "email": "email{}@example.com".format(i),
            "name": "Name {}".format(i),
            "title": "Title {}".format(i),
            "organizer": "Organizer {}".format(i),
            "address": "Address {}".format(i),
            "started": timezone.now().date().strftime('%Y-%m-%d'),
            "ended": timezone.now().date().strftime('%Y-%m-%d')
        })

    paginator = Paginator(credentials_list, 10)
    page = request.GET.get('page')
    try:
        training_credentials = paginator.page(page)
    except PageNotAnInteger:
        training_credentials = paginator.page(1)
    except EmptyPage:
        training_credentials = paginator.page(paginator.num_pages)

    context = {
        "training_credentials": training_credentials,
    }
    return render(request, template_name, context)


@login_required
def test_data_dashboard_courses_view(request):
    """"""
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_data_dashboard_courses.html"

    courses = []
    for i in range(1, 31):
        data = {}
        data['course_id'] = "course-v1:DAP+SPXX{}+202X_QX".format(i)
        data['name'] = "SPARTA Course {}".format(i)
        data['no_of_completed'] = i*2
        data['percent_completed'] = "XXX"
        courses.append(data)

    context = {
        "courses": courses,
    }
    return render(request, template_name, context)
