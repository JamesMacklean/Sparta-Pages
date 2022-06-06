from ast import If
import csv
import unicodecsv

from datetime import datetime, timedelta, date
from os import path
from uuid import uuid4

from boto import s3
from boto.s3.key import Key

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from lms.djangoapps.certificates.models import certificate_status_for_student

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment

##### For Self-Enrollment #####
from django.contrib.auth.models import User
from email.message import EmailMessage
from sparta_pages.models import SpartaEnrollment
############################

from ..analytics import OverallAnalytics, PathwayAnalytics, CourseAnalytics
from ..forms import (
    SpartaProfileForm, EducationProfileForm, EmploymentProfileForm,
    TrainingProfileForm, PathwayApplicationForm,
    EducationProfileFormset, EmploymentProfileFormset, TrainingProfileFormset,
    ExportAppsForm, FilterForm, ExportProfilesForm,
    ExtendedSpartaProfileForm, ExportAnalyticsForm, ExportPathwayAnalyticsForm,
    EditSpartaProfileForm
)
from ..models import (
    Pathway, SpartaCourse, SpartaProfile, ExtendedSpartaProfile,
    EducationProfile, EmploymentProfile, SpartaReEnrollment, TrainingProfile,
    PathwayApplication, Event,
    SpartaCoupon, StudentCouponRecord,MicroPathway,MicroCourse,MicroGroup
)
from ..local_settings import LOCAL_MAX_APPLIED


def main(request):
    """"""
    template_name = "sparta_main.html"
    context = {}

    profile = None
    if request.user.is_authenticated:
        try:
            profile = SpartaProfile.objects.get(user=request.user)
        except SpartaProfile.DoesNotExist:
            pass

    pathways = Pathway.objects.filter(is_active=True)
    micropathways = MicroPathway.objects.filter(is_active=True)

    context['pathways'] = pathways
    context['profile'] = profile
    context['micropathways'] = micropathways
    return render(request, template_name, context)


def micropathway(request, slug):
    """"""
    template_name = "sparta_micropathway.html"
    context = {}

    micropathway = get_object_or_404(MicroPathway, slug=slug)
    micropathway_courses = MicroCourse.objects.filter(is_active=True).filter(micropathway=micropathway)

    micro_courses = []
    elective_courses = []
    for group in micropathway.groups.all().filter(is_active=True):
        micropathway_courses = micropathway_courses.filter(group=group)
        courses = []
        for micropathway_course in micropathway_courses:
            course = {'micropathway_course': micropathway_course}
            course_key = CourseKey.from_string(micropathway_course.course_id)
            courseoverview = CourseOverview.get_from_id(course_key)
            course['courseoverview'] = courseoverview
            courses.append(course)
        data = {
            'courses': courses,
            'complete_at_least': group.complete_at_least
        }
        if group.type == "EL":
            elective_courses.append(data)
        else:
            micro_courses.append(data)

    context['micro_courses'] = micro_courses
    context['elective_courses'] = elective_courses
    context['micropathway'] = micropathway
    return render(request, template_name, context)

def pathway(request, slug):
    """"""
    template_name = "sparta_pathway.html"
    context = {}

    pathway = get_object_or_404(Pathway, slug=slug)
    sparta_courses = SpartaCourse.objects.filter(is_active=True).filter(pathway=pathway)

    core_courses = []
    elective_courses = []
    graduate_course = []
    for group in pathway.groups.all().filter(is_active=True):
        pathway_courses = sparta_courses.filter(group=group)
        courses = []
        for pathway_course in pathway_courses:
            course = {'pathway_course': pathway_course}
            course_key = CourseKey.from_string(pathway_course.course_id)
            courseoverview = CourseOverview.get_from_id(course_key)
            course['courseoverview'] = courseoverview
            courses.append(course)
        data = {
            'courses': courses,
            'complete_at_least': group.complete_at_least
        }
        if group.type == "EL":
            elective_courses.append(data)
        else:
            core_courses.append(data)

    if slug == "functional-analyst":
        try:
            cap_course_key = CourseKey.from_string("course-v1:DAP+SPCapstone001+2021_Q2")
            cap_course_overview = CourseOverview.get_from_id(cap_course_key)
            context['graduate_course'] = {'courseoverview': cap_course_overview}
        except CourseOverview.DoesNotExist:
            context['graduate_course'] = None
    elif slug == "data-associate":
        try:
            cap_course_key = CourseKey.from_string("course-v1:DAP+SPCapstone003+2021_Q4")
            cap_course_overview = CourseOverview.get_from_id(cap_course_key)
            context['graduate_course'] = {'courseoverview': cap_course_overview}
        except CourseOverview.DoesNotExist:
            context['graduate_course'] = None
    elif slug == "data-steward":
        try:
            cap_course_key = CourseKey.from_string("course-v1:DAP+SPCapstone005+2021_Q3")
            cap_course_overview = CourseOverview.get_from_id(cap_course_key)
            context['graduate_course'] = {'courseoverview': cap_course_overview}
        except CourseOverview.DoesNotExist:
            context['graduate_course'] = None
    elif slug == "data-engineer":
        try:
            cap_course_key = CourseKey.from_string("course-v1:DAP+SPCapstone004+2022_Q1")
            cap_course_overview = CourseOverview.get_from_id(cap_course_key)
            context['graduate_course'] = {'courseoverview': cap_course_overview}
        except CourseOverview.DoesNotExist:
            context['graduate_course'] = None
    elif slug == "data-scientist":
        context['graduate_course'] = None
    elif slug == "analytics-manager":
        try:
            cap_course_key = CourseKey.from_string("course-v1:DAP+SPCapstone006+2021_Q3")
            cap_course_overview = CourseOverview.get_from_id(cap_course_key)
            context['graduate_course'] = {'courseoverview': cap_course_overview}
        except CourseOverview.DoesNotExist:
            context['graduate_course'] = None

    context['core_courses'] = core_courses
    context['elective_courses'] = elective_courses
    context['pathway'] = pathway
    return render(request, template_name, context)


class RegistrationPageView(View):
    """
    """
    sparta_profile_form_class = SpartaProfileForm
    template_name = "sparta_register.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(RegistrationPageView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if SpartaProfile.objects.filter(user=request.user):
            return redirect('sparta-profile')
        sparta_profile_form = self.sparta_profile_form_class()
        return render(request, self.template_name, {'sparta_profile_form': sparta_profile_form})

    def post(self, request, *args, **kwargs):
        sparta_profile_form = self.sparta_profile_form_class(request.POST, request.FILES)
        if sparta_profile_form.is_valid():
            proof_of_education_file = sparta_profile_form.cleaned_data['proof_of_education_file']
            # proof_of_agreement_file = sparta_profile_form.cleaned_data['proof_of_agreement_file']
            tos_yes = sparta_profile_form.cleaned_data['tos_yes']
            discovery = sparta_profile_form.cleaned_data['discovery']
            org = sparta_profile_form.cleaned_data['org']
            ccap_sub = sparta_profile_form.cleaned_data['ccap_sub']
            lgu_sub = sparta_profile_form.cleaned_data['lgu_sub']

            if not tos_yes:
                return render(request, self.template_name, {'sparta_profile_form': sparta_profile_form})

            # s3_response = upload_to_s3(request.user, proof_of_education_file, proof_of_agreement_file)
            s3_response = upload_to_s3(request.user, proof_of_education_file)

            # proof_of_agreement_url = s3_response.get('proof_of_agreement_url', "")
            proof_of_education_url = s3_response.get('proof_of_education_url', "")

            try:
                sprofile = SpartaProfile.objects.get(user=request.user)
            except SpartaProfile.DoesNotExist:
                sprofile = SpartaProfile(user=request.user)
            # sprofile.proof_of_agreement = proof_of_agreement_url
            sprofile.proof_of_education = proof_of_education_url
            sprofile.discovery = discovery
            sprofile.org = org
            sprofile.ccap_sub = ccap_sub
            sprofile.lgu_sub = lgu_sub
            sprofile.save()

            return redirect(reverse('sparta-register-extended'))
        return render(request, self.template_name, {'sparta_profile_form': sparta_profile_form})


class ExtendedRegistrationPageView(View):
    """
    """
    sparta_profile_form_class = ExtendedSpartaProfileForm
    template_name = "sparta_register_extended.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ExtendedRegistrationPageView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not SpartaProfile.objects.filter(user=request.user).exists():
            return redirect('sparta-register')
        if ExtendedSpartaProfile.objects.filter(user=request.user).exists():
            return redirect('sparta-profile')
        sparta_profile_form = self.sparta_profile_form_class()
        return render(request, self.template_name, {'sparta_profile_form': sparta_profile_form})

    def post(self, request, *args, **kwargs):
        sparta_profile_form = self.sparta_profile_form_class(request.POST)
        if sparta_profile_form.is_valid():
            address = sparta_profile_form.cleaned_data['address']
            municipality = sparta_profile_form.cleaned_data['municipality']
            affiliation = sparta_profile_form.cleaned_data['affiliation']
            attainment = sparta_profile_form.cleaned_data['attainment']
            other_attain = sparta_profile_form.cleaned_data['other_attain']
            is_employed = sparta_profile_form.cleaned_data['is_employed']
            grad_degree = sparta_profile_form.cleaned_data['grad_degree']

            try:
                ext_profile = ExtendedSpartaProfile.objects.get(user=request.user)
            except ExtendedSpartaProfile.DoesNotExist:
                ext_profile = ExtendedSpartaProfile(user=request.user)

            ext_profile.address = address
            ext_profile.municipality = municipality
            ext_profile.affiliation = affiliation
            ext_profile.attainment = attainment
            ext_profile.is_employed = is_employed
            ext_profile.grad_degree = grad_degree
            if other_attain:
                ext_profile.other_attain = other_attain
            ext_profile.save()

            return redirect(reverse('sparta-register-education'))
        return render(request, self.template_name, {'sparta_profile_form': sparta_profile_form})


class RegisterEducationProfileView(View):
    """
    """
    educ_formset_class = EducationProfileFormset
    template_name = "sparta_register_education.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(RegisterEducationProfileView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not SpartaProfile.objects.filter(user=request.user).exists():
            return redirect('sparta-register')
        educationFormset = self.educ_formset_class(request.GET or None)
        return render(request, self.template_name, {'educationFormset': educationFormset})

    def post(self, request, *args, **kwargs):
        try:
            sprofile = SpartaProfile.objects.get(user=request.user)
        except SpartaProfile.DoesNotExist:
            return redirect('sparta-register')

        educationFormset = self.educ_formset_class(request.POST)
        if educationFormset.is_valid():
            for f in educationFormset:
                degree = f.cleaned_data.get('degree')
                course = f.cleaned_data.get('course', None)
                school = f.cleaned_data.get('school', None)
                address = f.cleaned_data.get('address', None)
                started_at = f.cleaned_data.get('started_at', None)
                graduated_at = f.cleaned_data.get('graduated_at', None)
                if None not in [course, school, address, started_at, graduated_at]:
                    edprofile = EducationProfile.objects.create(
                        profile=sprofile,
                        degree=degree,
                        course=course,
                        school=school,
                        address=address,
                        started_at=started_at,
                        graduated_at=graduated_at
                    )
            return redirect(reverse('sparta-register-employment'))
        return render(request, self.template_name, {'educationFormset': educationFormset})


class RegisterEmploymentProfileView(View):
    """
    """
    employ_formset_class = EmploymentProfileFormset
    template_name = "sparta_register_employment.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(RegisterEmploymentProfileView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not SpartaProfile.objects.filter(user=request.user).exists():
            return redirect('sparta-register')

        employmentFormset = self.employ_formset_class(request.GET or None)
        return render(request, self.template_name, {'employmentFormset': employmentFormset})

    def post(self, request, *args, **kwargs):
        try:
            sprofile = SpartaProfile.objects.get(user=request.user)
        except SpartaProfile.DoesNotExist:
            return redirect('sparta-register')

        employmentFormset = self.employ_formset_class(request.POST)
        if employmentFormset.is_valid():
            for f in employmentFormset:
                affiliation = f.cleaned_data.get('affiliation')
                occupation = f.cleaned_data.get('occupation', None)
                designation = f.cleaned_data.get('designation', None)
                employer = f.cleaned_data.get('employer', None)
                address = f.cleaned_data.get('address', None)
                started_at = f.cleaned_data.get('started_at', None)
                ended_at = f.cleaned_data.get('ended_at', None)
                if None not in [occupation, designation, employer, address, started_at]:
                    emprofile = EmploymentProfile.objects.create(
                        profile=sprofile,
                        affiliation=affiliation,
                        occupation=occupation,
                        designation=designation,
                        employer=employer,
                        address=address,
                        started_at=started_at,
                        ended_at=ended_at
                    )
            return redirect(reverse('sparta-register-training'))
        return render(request, self.template_name, {'employmentFormset': employmentFormset})


class RegisterTrainingProfileView(View):
    """
    """
    train_formset_class = TrainingProfileFormset
    template_name = "sparta_register_training.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(RegisterTrainingProfileView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not SpartaProfile.objects.filter(user=request.user).exists():
            return redirect('sparta-register')
        trainingFormset = self.train_formset_class(request.GET or None)
        return render(request, self.template_name, {'trainingFormset': trainingFormset})

    def post(self, request, *args, **kwargs):
        try:
            sprofile = SpartaProfile.objects.get(user=request.user)
        except SpartaProfile.DoesNotExist:
            return redirect('sparta-register')

        trainingFormset = self.train_formset_class(request.POST)
        if trainingFormset.is_valid():
            for f in trainingFormset:
                title = f.cleaned_data.get('title', None)
                organizer = f.cleaned_data.get('organizer', None)
                address = f.cleaned_data.get('address', None)
                started_at = f.cleaned_data.get('started_at', None)
                ended_at = f.cleaned_data.get('ended_at', None)
                if None not in [title, organizer, address, started_at, ended_at]:
                    tprofile = TrainingProfile.objects.create(
                        profile=sprofile,
                        title=title,
                        organizer=organizer,
                        address=address,
                        started_at=started_at,
                        ended_at=ended_at
                    )
            return redirect(reverse('sparta-register-success'))
        return render(request, self.template_name, {'trainingFormset': trainingFormset})


def upload_to_s3(user, proof_of_education_file, proof_of_agreement_file=None):
    """"""
    BUCKET_NAME = "openedx-coursebank-sparta-eligibility-documents-tmtg"
    c = s3.connection.S3Connection(
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY
    )
    nonexistent = c.lookup(BUCKET_NAME)
    if nonexistent is None:
        raise Exception("No valid S3 Bucket set for image uploading.")

    b = c.get_bucket(BUCKET_NAME, validate=False) # substitute your bucket name here
    blocation = str(b.get_location())

    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    educ_key = Key(b)
    educ_key.key = 'proof_of_education/{}_{}'.format(user.username, tnow)
    educ_key.set_contents_from_file(proof_of_education_file)
    educ_url = "https://{}.s3-{}.amazonaws.com/{}".format(settings.FILE_UPLOAD_STORAGE_BUCKET_NAME, blocation, educ_key.key)

    # agree_key = Key(b)
    # agree_key.key = 'proof_of_agreement/{}_{}'.format(user.username, tnow)
    # agree_key.set_contents_from_file(proof_of_agreement_file)
    # agree_url = "https://{}.{}.amazonaws.com/{}".format(settings.FILE_UPLOAD_STORAGE_BUCKET_NAME, blocation, agree_key.key)

    # return {'proof_of_education_url': educ_url, 'proof_of_agreement_url': agree_url}
    return {'proof_of_education_url': educ_url}


def register_success_page(request):
    """ /sparta/register/success/ """
    template_name = "sparta_register_success.html"
    context = {}

    return render(request, template_name, context)


class ProfilePageView(TemplateView):
    template_name = 'sparta_profile.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ProfilePageView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ProfilePageView, self).get_context_data(**kwargs)
        profile = self.request.user.sparta_profile

        ##################### MICROPATHWAYS #####################
        
        get_micropathways = MicroPathway.objects.filter(is_active=True)

        micropathways = []
        for micropathway in get_micropathways:
            
            micro_courses = MicroCourse.objects.filter(is_active=True).filter(micropathway=micropathway)
        courses = []
        
        for group in micropathway.groups.all().filter(is_active=True):
            micropathway_courses = micro_courses.filter(group=group)
            
            counter=0
            for micropathway_course in micropathway_courses:
                counter = counter+1
                course = {
                    'unique_id': counter,
                    'micropathway_course': micropathway_course,
                    'group': group.type
                }
                course_key = CourseKey.from_string(micropathway_course.course_id)
                courseoverview = CourseOverview.get_from_id(course_key)
                course['courseoverview'] = courseoverview

                # To check if user is enrolled
                enrollment = CourseEnrollment.is_enrolled(self.request.user, course_key)
                if enrollment is True:
                    course['enrollment_status'] = "enrolled"
                else:
                    course['enrollment_status'] = "not enrolled"

                courses.append(course)
                micropathways.append(micropathway)

        try:
            extended_profile = ExtendedSpartaProfile.objects.get(user=self.request.user)
        except ExtendedSpartaProfile.DoesNotExist:
            extended_profile = None

        applications = PathwayApplication.objects.all().filter(profile=profile).exclude(status='WE')

        display_applications = []

        if applications.exists():
            display_applications.append(applications.order_by('created_at')[0])

        context['profile'] = profile
        context['discovery'] = profile.get_discovery_display()
        context['org'] = profile.get_org_display()
        context['extended_profile'] = extended_profile
        context['applications'] = display_applications
        context['micropathways'] = micropathways
        context['courses'] = courses
        context['has_approved_application'] = PathwayApplication.objects.filter(profile=profile).filter(status='AP').exists()
        context['pathway_is_approved'] = applications
        context['uname'] = profile.user.username

        context['education_profiles'] = EducationProfile.objects.all().filter(profile=profile)
        context['employment_profiles'] = EmploymentProfile.objects.all().filter(profile=profile)
        context['training_profiles'] = TrainingProfile.objects.all().filter(profile=profile)

        max_applied = LOCAL_MAX_APPLIED or Pathway.objects.all().count()
        if applications.count() >= max_applied:
            context['max_applied'] = True
        return context

    def get(self, request, *args, **kwargs):
        try:
            profile = SpartaProfile.objects.get(user=request.user)
        except SpartaProfile.DoesNotExist:
            return redirect('sparta-main')
        context = self.get_context_data()
        return render(request, self.template_name, context)


class PathwayApplicationView(TemplateView):
    # form_class = PathwayApplicationForm
    template_name = 'sparta_apply.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(PathwayApplicationView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PathwayApplicationView, self).get_context_data(**kwargs)
        get_pathways = Pathway.objects.filter(is_active=True)
        pathways = []
        sparta_profile = self.request.user.sparta_profile
        for p in get_pathways:
            apps = p.applications.all().filter(profile=sparta_profile).exclude(status='WE')
            if not apps.exists():
                pathways.append(p)
        context['pathways'] = pathways
        context['has_approved_application'] = PathwayApplication.objects.filter(profile=sparta_profile).filter(status='AP').exists()
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        if not request.user.sparta_profile.is_active:
            return redirect('sparta-profile')
        return render(request, self.template_name, context)

@require_POST
def apply(request, id):
    """"""
    try:
        pathway = Pathway.objects.get(id=id)
    except Pathway.DoesNotExist:
        raise HttpResponse(status=500)

    profiles = SpartaProfile.objects.filter(is_active=True)
    try:
        sparta_profile = profiles.get(user=request.user)
    except SpartaProfile.DoesNotExist:
        raise HttpResponse(status=403)

    app, created = PathwayApplication.objects.get_or_create(profile=sparta_profile, pathway=pathway)
    app.pend()

    return redirect('sparta-profile')

@require_POST
def widthraw(request, id):
    """"""
    if not request.user.sparta_profile.is_active:
        return redirect('sparta-profile')
    app = get_object_or_404(PathwayApplication, id=id)
    if request.user != app.profile.user:
        return HttpResponse(status=403)
    app.withdraw()
    Event.objects.create(
        event="Withdraw Application",
        description="User {} has withdrawn application for learning pathway {}.".format(app.profile.user.username, app.pathway.name),
        profile=app.profile
    )
    return redirect('sparta-profile')

class PathwayProgressView(TemplateView):
    """
    path: /sparta/pathway/<pathway_id>/progress/
    """
    template_name = 'sparta_progress.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(PathwayProgressView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not request.user.sparta_profile.is_active:
            return redirect('sparta-profile')

        context = self.get_context_data()

        pathway = get_object_or_404(Pathway, id=self.kwargs['pathway_id'])
        context['pathway'] = pathway

        try:
            app = PathwayApplication.objects.get(profile=request.user.sparta_profile, pathway=pathway, status="AP")
        except PathwayApplication.DoesNotExist:
            raise Http404

        courses = []
        for pathway_course in pathway.courses.all().filter(is_active=True):
            course = {'pathway_course': pathway_course}
            course_key = CourseKey.from_string(pathway_course.course_id)
            courseoverview = CourseOverview.get_from_id(course_key)
            course['courseoverview'] = courseoverview

            cert_status = certificate_status_for_student(app.profile.user, course_key)
            if cert_status:
                if cert_status['mode'] == 'verified' or cert_status['mode'] == 'honor':
                    if cert_status['status'] not in  ['unavailable', 'notpassing', 'restricted', 'unverified']:
                        course['completed'] = True
                    else:
                        course['completed'] = False
                else:
                    course['completed'] = False
            else:
                course['completed'] = False

            courses.append(course)
        context['courses'] = courses

        return render(request, self.template_name, context)
class ExtendedSpartaProfileUpdateView(UpdateView):
    model = ExtendedSpartaProfile
    form_class = ExtendedSpartaProfileForm
    template_name_suffix = '_update_form'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ExtendedSpartaProfileUpdateView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        ep = get_object_or_404(ExtendedSpartaProfile, user=request.user)
        if ep.id != self.get_object().id:
            raise Http404
        return super(ExtendedSpartaProfileUpdateView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('sparta-profile')


class EducationProfileUpdateView(UpdateView):
    model = EducationProfile
    form_class = EducationProfileForm
    template_name_suffix = '_update_form'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(EducationProfileUpdateView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if self.get_object() not in EducationProfile.objects.filter(profile__user=request.user):
            raise Http404
        return super(EducationProfileUpdateView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('sparta-profile')


class EmploymentProfileUpdateView(UpdateView):
    model = EmploymentProfile
    form_class = EmploymentProfileForm
    template_name_suffix = '_update_form'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(EmploymentProfileUpdateView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if self.get_object() not in EmploymentProfile.objects.filter(profile__user=request.user):
            raise Http404
        return super(EmploymentProfileUpdateView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('sparta-profile')


class TrainingProfileUpdateView(UpdateView):
    model = TrainingProfile
    form_class = TrainingProfileForm
    template_name_suffix = '_update_form'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(TrainingProfileUpdateView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if self.get_object() not in TrainingProfile.objects.filter(profile__user=request.user):
            raise Http404
        return super(TrainingProfileUpdateView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('sparta-profile')


class ExtendedRegistrationCreateView(View):
    """
    """
    sparta_profile_form_class = ExtendedSpartaProfileForm
    template_name = "sparta_create_extended_profile.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ExtendedRegistrationCreateView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not SpartaProfile.objects.filter(is_active=True).filter(user=request.user).exists() or ExtendedSpartaProfile.objects.filter(user=request.user).exists():
            return redirect('sparta-register')
        sparta_profile_form = self.sparta_profile_form_class()
        return render(request, self.template_name, {'sparta_profile_form': sparta_profile_form})

    def post(self, request, *args, **kwargs):
        sparta_profile_form = self.sparta_profile_form_class(request.POST)
        if sparta_profile_form.is_valid():
            address = sparta_profile_form.cleaned_data['address']
            municipality = sparta_profile_form.cleaned_data['municipality']
            affiliation = sparta_profile_form.cleaned_data['affiliation']
            attainment = sparta_profile_form.cleaned_data['attainment']
            other_attain = sparta_profile_form.cleaned_data['other_attain']
            is_employed = sparta_profile_form.cleaned_data['is_employed']
            grad_degree = sparta_profile_form.cleaned_data['grad_degree']

            try:
                ext_profile = ExtendedSpartaProfile.objects.get(user=request.user)
            except ExtendedSpartaProfile.DoesNotExist:
                ext_profile = ExtendedSpartaProfile(user=request.user)

            ext_profile.address = address
            ext_profile.municipality = municipality
            ext_profile.affiliation = affiliation
            ext_profile.attainment = attainment
            ext_profile.is_employed = is_employed
            ext_profile.grad_degree = grad_degree
            if other_attain:
                ext_profile.other_attain = other_attain
            ext_profile.save()

            return redirect(reverse('sparta-profile'))
        return render(request, self.template_name, {'sparta_profile_form': sparta_profile_form})


class EducationProfileCreateView(CreateView):
    """
    """
    educ_formset_class = EducationProfileFormset
    template_name = "sparta_create_education.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(EducationProfileCreateView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not SpartaProfile.objects.filter(is_active=True).filter(user=request.user).exists():
            return redirect('sparta-register')
        educationFormset = self.educ_formset_class(request.GET or None)
        return render(request, self.template_name, {'educationFormset': educationFormset})

    def post(self, request, *args, **kwargs):
        try:
            sprofile = SpartaProfile.objects.get(user=request.user)
        except SpartaProfile.DoesNotExist:
            return redirect('sparta-register')

        educationFormset = self.educ_formset_class(request.POST)
        if educationFormset.is_valid():
            for f in educationFormset:
                degree = f.cleaned_data.get('degree')
                course = f.cleaned_data.get('course', None)
                school = f.cleaned_data.get('school', None)
                address = f.cleaned_data.get('address', None)
                started_at = f.cleaned_data.get('started_at', None)
                graduated_at = f.cleaned_data.get('graduated_at', None)
                if None not in [course, school, address, started_at, graduated_at]:
                    edprofile = EducationProfile.objects.create(
                        profile=sprofile,
                        degree=degree,
                        course=course,
                        school=school,
                        address=address,
                        started_at=started_at,
                        graduated_at=graduated_at
                    )
            return redirect(reverse('sparta-profile'))
        return render(request, self.template_name, {'educationFormset': educationFormset})


class EmploymentProfileCreateView(CreateView):
    """
    """
    employ_formset_class = EmploymentProfileFormset
    template_name = "sparta_create_employment.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(EmploymentProfileCreateView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not SpartaProfile.objects.filter(is_active=True).filter(user=request.user).exists():
            return redirect('sparta-register')

        employmentFormset = self.employ_formset_class(request.GET or None)
        return render(request, self.template_name, {'employmentFormset': employmentFormset})

    def post(self, request, *args, **kwargs):
        try:
            sprofile = SpartaProfile.objects.get(user=request.user)
        except SpartaProfile.DoesNotExist:
            return redirect('sparta-register')

        employmentFormset = self.employ_formset_class(request.POST)
        if employmentFormset.is_valid():
            for f in employmentFormset:
                affiliation = f.cleaned_data.get('affiliation')
                occupation = f.cleaned_data.get('occupation', None)
                designation = f.cleaned_data.get('designation', None)
                employer = f.cleaned_data.get('employer', None)
                address = f.cleaned_data.get('address', None)
                started_at = f.cleaned_data.get('started_at', None)
                ended_at = f.cleaned_data.get('ended_at', None)
                if None not in [occupation, designation, employer, address, started_at]:
                    emprofile = EmploymentProfile.objects.create(
                        profile=sprofile,
                        affiliation=affiliation,
                        occupation=occupation,
                        designation=designation,
                        employer=employer,
                        address=address,
                        started_at=started_at,
                        ended_at=ended_at
                    )
            return redirect(reverse('sparta-profile'))
        return render(request, self.template_name, {'employmentFormset': employmentFormset})


class TrainingProfileCreateView(CreateView):
    """
    """
    train_formset_class = TrainingProfileFormset
    template_name = "sparta_create_training.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(TrainingProfileCreateView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not SpartaProfile.objects.filter(is_active=True).filter(user=request.user).exists():
            return redirect('sparta-register')
        trainingFormset = self.train_formset_class(request.GET or None)
        return render(request, self.template_name, {'trainingFormset': trainingFormset})

    def post(self, request, *args, **kwargs):
        try:
            sprofile = SpartaProfile.objects.get(user=request.user)
        except SpartaProfile.DoesNotExist:
            return redirect('sparta-register')

        trainingFormset = self.train_formset_class(request.POST)
        if trainingFormset.is_valid():
            for f in trainingFormset:
                title = f.cleaned_data.get('title', None)
                organizer = f.cleaned_data.get('organizer', None)
                address = f.cleaned_data.get('address', None)
                started_at = f.cleaned_data.get('started_at', None)
                ended_at = f.cleaned_data.get('ended_at', None)
                if None not in [title, organizer, address, started_at, ended_at]:
                    tprofile = TrainingProfile.objects.create(
                        profile=sprofile,
                        title=title,
                        organizer=organizer,
                        address=address,
                        started_at=started_at,
                        ended_at=ended_at
                    )
            return redirect(reverse('sparta-profile'))
        return render(request, self.template_name, {'trainingFormset': trainingFormset})


@require_POST
def delete_education_profile(request, pk):
    profiles = SpartaProfile.objects.filter(is_active=True)
    try:
        sparta_profile = profiles.get(user=request.user)
    except SpartaProfile.DoesNotExist:
        raise HttpResponse(status=403)

    education_profile = get_object_or_404(EducationProfile, pk=pk)
    if education_profile.profile != sparta_profile:
        raise HttpResponse(status=403)
    else:
        education_profile.delete()

    return redirect('sparta-profile')


@require_POST
def delete_employment_profile(request, pk):
    profiles = SpartaProfile.objects.filter(is_active=True)
    try:
        sparta_profile = profiles.get(user=request.user)
    except SpartaProfile.DoesNotExist:
        raise HttpResponse(status=403)

    employment_profile = get_object_or_404(EmploymentProfile, pk=pk)
    if employment_profile.profile != sparta_profile:
        raise HttpResponse(status=403)
    else:
        employment_profile.delete()

    return redirect('sparta-profile')


@require_POST
def delete_training_profile(request, pk):
    profiles = SpartaProfile.objects.filter(is_active=True)
    try:
        sparta_profile = profiles.get(user=request.user)
    except SpartaProfile.DoesNotExist:
        raise HttpResponse(status=403)

    training_profile = get_object_or_404(TrainingProfile, pk=pk)
    if training_profile.profile != sparta_profile:
        raise HttpResponse(status=403)
    else:
        training_profile.delete()

    return redirect('sparta-profile')


class StudentCouponRecordsView(TemplateView):
    template_name = 'sparta_pathway_courses.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(StudentCouponRecordsView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        
            
        context = super(StudentCouponRecordsView, self).get_context_data(**kwargs)

        pathway = get_object_or_404(Pathway, id=self.kwargs['pathway_id'])
        profile = self.request.user.sparta_profile
     
        ###############################################################

        applications = PathwayApplication.objects.filter(profile=profile).filter(pathway__id=self.kwargs['pathway_id']).filter(status="AP")
        
        sparta_courses = SpartaCourse.objects.filter(is_active=True).filter(pathway=pathway)

        core_courses = []
        elective_courses = []
        graduate_course = []
        courses = []
        for group in pathway.groups.all().filter(is_active=True):
            pathway_courses = sparta_courses.filter(group=group)
            
            counter=0
            for pathway_course in pathway_courses:
                counter = counter+1
                
                course = {
                    
                    'unique_id': counter,
                    'pathway_course': pathway_course,
                    'group': group.type,

                }

                course_key = CourseKey.from_string(pathway_course.course_id)
                courseoverview = CourseOverview.get_from_id(course_key)       
                course['courseoverview'] = courseoverview  

                # To check if user is enrolled
                enrollment = CourseEnrollment.is_enrolled(self.request.user, course_key)
                if enrollment is True:
                    course['enrollment_status'] = "enrolled"
                else:
                    course['enrollment_status'] = "not enrolled"

                courses.append(course)

            data = {
                'courses': courses,
                'complete_at_least': group.complete_at_least
            }
            if group.type == "EL":
                elective_courses.append(data)
            else:
                core_courses.append(data)
        
        if pathway == "Data Analyst":
            try:
                cap_course_key = CourseKey.from_string("course-v1:DAP+SPCapstone001+2021_Q2")
                cap_course_overview = CourseOverview.get_from_id(cap_course_key)
                context['graduate_course'] = {'courseoverview': cap_course_overview}
            except CourseOverview.DoesNotExist:
                context['graduate_course'] = None
        
        elif pathway == "Data Associate":
            try:
                cap_course_key = CourseKey.from_string("course-v1:DAP+SPCapstone003+2021_Q4")
                cap_course_overview = CourseOverview.get_from_id(cap_course_key)
                context['graduate_course'] = {'courseoverview': cap_course_overview}
            except CourseOverview.DoesNotExist:
                context['graduate_course'] = None
        
        elif pathway == "Data Steward":
            try:
                cap_course_key = CourseKey.from_string("course-v1:DAP+SPCapstone005+2021_Q3")
                cap_course_overview = CourseOverview.get_from_id(cap_course_key)
                context['graduate_course'] = {'courseoverview': cap_course_overview}
            except CourseOverview.DoesNotExist:
                context['graduate_course'] = None
        
        elif pathway == "Data Engineer":
            try:
                cap_course_key = CourseKey.from_string("course-v1:DAP+SPCapstone004+2022_Q1")
                cap_course_overview = CourseOverview.get_from_id(cap_course_key)
                context['graduate_course'] = {'courseoverview': cap_course_overview}
            except CourseOverview.DoesNotExist:
                context['graduate_course'] = None
        
        elif pathway == "Data Scientist":
            context['graduate_course'] = None
        
        elif pathway == "Analytics Manager":
            try:
                cap_course_key = CourseKey.from_string("course-v1:DAP+SPCapstone006+2021_Q3")
                cap_course_overview = CourseOverview.get_from_id(cap_course_key)
                context['graduate_course'] = {'courseoverview': cap_course_overview}
            except CourseOverview.DoesNotExist:
                context['graduate_course'] = None

        context['core_courses'] = core_courses
        context['elective_courses'] = elective_courses
        context['courses'] = courses
        ###############################################################
        context['pathway_is_approved'] = applications
        context['uname'] = profile.user.username
        context['pathway'] = pathway

        return context

    def get(self, request, *args, **kwargs):
        try:
            profile = SpartaProfile.objects.get(user=request.user)
        except SpartaProfile.DoesNotExist:
            return redirect('sparta-main')

        try:
            applications = PathwayApplication.objects.filter(profile=profile).filter(pathway__id=self.kwargs['pathway_id']).filter(status="AP")
        except PathwayApplication.DoesNotExist:
            return redirect('sparta-profile')

        context = self.get_context_data()      
            
        return render(request, self.template_name, context)

@require_POST
def enrollment_approve_application(request, username, course_key):

    try:
        profile = SpartaProfile.objects.get(user=request.user)
    except SpartaProfile.DoesNotExist:
        return redirect('sparta-main')

    if not request.user.sparta_profile.is_active:
        return redirect('sparta-main')

    courseoverview = CourseOverview.get_from_id(course_key)
    course_name = courseoverview.display_name

    def _enroll_user(username=None, email_address=None, course_key=None, course_name=None, mode=None):
        """ enroll a user """
        try:
            tnow = timezone.now()
            usname = User.objects.get(username=username)
            course_id = CourseKey.from_string(course_key)
            enrollment = CourseEnrollment.enroll(usname, course_id, mode, check_access=False)
            enrollmentData = SpartaEnrollment.objects.create(enrollment=enrollment,enroll_date=tnow)
        except Exception as e:
            return False
            
    # ENROLL COMMAND
    if username is not None:
        uname = User.objects.get(username=username)
        _enroll_user(username=uname, email_address=uname.email, course_key=course_key, course_name=course_name, mode="verified")

    return redirect('sparta-profile')


class MicroPathwayRecordsView(TemplateView):
    template_name = 'sparta_micropathway_courses.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(MicroPathwayRecordsView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        
        context = super(MicroPathwayRecordsView, self).get_context_data(**kwargs)

        micropathway = get_object_or_404(MicroPathway, slug=self.kwargs['slug'])
        # micropathway = get_object_or_404(MicroPathway, id=self.kwargs['micropathway_id'])
        profile = self.request.user.sparta_profile
     
        ###############################################################

        applications = PathwayApplication.objects.filter(profile=profile).filter(status="AP")
        
        micro_courses = MicroCourse.objects.filter(is_active=True).filter(micropathway=micropathway)

        courses = []
        for group in micropathway.groups.all().filter(is_active=True):
            micropathway_courses = micro_courses.filter(group=group)
            
            counter=0
            for micropathway_course in micropathway_courses:
                counter = counter+1
                course = {
                    'unique_id': counter,
                    'micropathway_course': micropathway_course,
                    'group': group.type
                }
                course_key = CourseKey.from_string(micropathway_course.course_id)
                courseoverview = CourseOverview.get_from_id(course_key)
                course['courseoverview'] = courseoverview

                # To check if user is enrolled
                enrollment = CourseEnrollment.is_enrolled(self.request.user, course_key)
                if enrollment is True:
                    course['enrollment_status'] = "enrolled"
                else:
                    course['enrollment_status'] = "not enrolled"

                courses.append(course)
            # data = {
            #     'courses': courses,
            #     'complete_at_least': group.complete_at_least
            # }
            # if group.type == "EL":
            #     elective_courses.append(data)
            # else:
            #     core_courses.append(data)
        
        context['courses'] = courses
        context['pathway_is_approved'] = applications
        context['uname'] = profile.user.username
        context['micropathway'] = micropathway

        return context

    def get(self, request, *args, **kwargs):
        try:
            profile = SpartaProfile.objects.get(user=request.user)
        except SpartaProfile.DoesNotExist:
            return redirect('sparta-main')

        try:
            applications = PathwayApplication.objects.filter(profile=profile).filter(status="AP")
        except PathwayApplication.DoesNotExist:
            return redirect('sparta-profile')

        context = self.get_context_data()      
            
        return render(request, self.template_name, context)
class AdditionalEditPageView(View):
    """
    """
    sparta_profile_form_class = EditSpartaProfileForm
    extended_sparta_profile_form_class = ExtendedSpartaProfileForm
    template_name = "sparta_pages/extendedspartaprofile_update_form.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AdditionalEditPageView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            sprofile = SpartaProfile.objects.get(user=request.user)
            ext_profile = ExtendedSpartaProfile.objects.get(pk=kwargs['pk'])
        except SpartaProfile.DoesNotExist:
            raise Http404
        except ExtendedSpartaProfile.DoesNotExist:
            raise Http404
        sprofile_initial = {
            'discovery': sprofile.discovery,
            'org': sprofile.org,
            'ccap': sprofile.ccap_sub,
            'lgu': sprofile.lgu_sub,
        }
        sparta_profile_form = self.sparta_profile_form_class(initial=sprofile_initial)
        extended_sparta_profile_form = self.extended_sparta_profile_form_class(instance=ext_profile)
        return render(request, self.template_name, {'sparta_profile_form': sparta_profile_form, 'extended_sparta_profile_form': extended_sparta_profile_form, 'ext_profile': ext_profile})

    def post(self, request, *args, **kwargs):
        try:
            sprofile = SpartaProfile.objects.get(user=request.user)
            ext_profile = ExtendedSpartaProfile.objects.get(user=request.user)
        except SpartaProfile.DoesNotExist:
            raise Http404
        except ExtendedSpartaProfile.DoesNotExist:
            raise Http404

        sparta_profile_form = self.sparta_profile_form_class(request.POST)
        extended_sparta_profile_form = self.extended_sparta_profile_form_class(request.POST)
        if sparta_profile_form.is_valid() and extended_sparta_profile_form.is_valid():
            discovery = sparta_profile_form.cleaned_data['discovery']
            org = sparta_profile_form.cleaned_data['org']
            ccap_sub = sparta_profile_form.cleaned_data['ccap_sub']
            lgu_sub = sparta_profile_form.cleaned_data['lgu_sub']

            address = extended_sparta_profile_form.cleaned_data['address']
            municipality = extended_sparta_profile_form.cleaned_data['municipality']
            affiliation = extended_sparta_profile_form.cleaned_data['affiliation']
            attainment = extended_sparta_profile_form.cleaned_data['attainment']
            other_attain = extended_sparta_profile_form.cleaned_data['other_attain']
            is_employed = extended_sparta_profile_form.cleaned_data['is_employed']
            grad_degree = extended_sparta_profile_form.cleaned_data['grad_degree']

            sprofile.discovery = discovery
            sprofile.org = org
            sprofile.ccap_sub = ccap_sub
            sprofile.lgu_sub = lgu_sub
            sprofile.save()

            ext_profile.address = address
            ext_profile.municipality = municipality
            ext_profile.affiliation = affiliation
            ext_profile.attainment = attainment
            ext_profile.is_employed = is_employed
            ext_profile.grad_degree = grad_degree
            if other_attain:
                ext_profile.other_attain = other_attain
            ext_profile.save()

            return redirect(reverse('sparta-profile'))
        return render(request, self.template_name, {'sparta_profile_form': sparta_profile_form, 'extended_sparta_profile_form': extended_sparta_profile_form, 'ext_profile': ext_profile})
