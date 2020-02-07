import csv
import hmac
import sha

from base64 import b64encode
from datetime import datetime, timedelta, date
from json import dumps
from mimetypes import guess_type
from os import path
from uuid import uuid4

import boto
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

from .analytics import OverallAnalytics, PathwayAnalytics, CourseAnalytics
from .forms import (
    SpartaProfileForm, EducationProfileForm, EmploymentProfileForm,
    TrainingProfileForm, PathwayApplicationForm,
    EducationProfileFormset, EmploymentProfileFormset, TrainingProfileFormset,
    ExportAppsForm, FilterForm, ExportProfilesForm,
    ExtendedSpartaProfileForm, ExportAnalyticsForm
)
from .models import (
    Pathway, SpartaCourse, SpartaProfile, ExtendedSpartaProfile,
    EducationProfile, EmploymentProfile, TrainingProfile,
    PathwayApplication, Event, APIToken,
    SpartaCoupon, StudentCouponRecord
)


#################
# Learner Pages #
################

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

    context['pathways'] = pathways
    context['profile'] = profile
    return render(request, template_name, context)


def pathway(request, slug):
    """"""
    template_name = "sparta_pathway.html"
    context = {}

    pathway = get_object_or_404(Pathway, slug=slug)
    sparta_courses = SpartaCourse.objects.filter(is_active=True).filter(pathway=pathway)

    core_courses = []
    elective_courses = []
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
            affiliation = sparta_profile_form.cleaned_data['affiliation']
            attainment = sparta_profile_form.cleaned_data['attainment']
            other_attain = sparta_profile_form.cleaned_data['other_attain']
            is_employed = sparta_profile_form.cleaned_data['is_employed']
            grad_degree = sparta_profile_form.cleaned_data['grad_degree']

            try:
                ext_profile = ExtendedSpartaProfile.objects.get(user=request.user)
            except ExtendedSpartaProfile.DoesNotExist:
                ext_profile = ExtendedSpartaProfile(user=request.user)

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
    BUCKET_NAME = "openedx-coursebank-sparta-eligibility-documents"
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

        try:
            extended_profile = ExtendedSpartaProfile.objects.get(user=self.request.user)
        except ExtendedSpartaProfile.DoesNotExist:
            extended_profile = None

        applications = PathwayApplication.objects.all().filter(profile=profile).exclude(status='WE')
        context['profile'] = profile
        context['extended_profile'] = extended_profile
        context['applications'] = applications
        context['education_profiles'] = EducationProfile.objects.all().filter(profile=profile)
        context['employment_profiles'] = EmploymentProfile.objects.all().filter(profile=profile)
        context['training_profiles'] = TrainingProfile.objects.all().filter(profile=profile)
        if applications.count() == Pathway.objects.all().count():
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
        for p in get_pathways:
            apps = p.applications.all().filter(profile=self.request.user.sparta_profile).exclude(status='WE')
            if not apps.exists():
                pathways.append(p)
        context['pathways'] = pathways
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
            if cert_status and cert_status['mode'] == 'verified' and cert_status['status'] not in  ['unavailable', 'notpassing', 'restricted', 'unverified']:
                course['completed'] = True
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
            affiliation = sparta_profile_form.cleaned_data['affiliation']
            attainment = sparta_profile_form.cleaned_data['attainment']
            other_attain = sparta_profile_form.cleaned_data['other_attain']
            is_employed = sparta_profile_form.cleaned_data['is_employed']
            grad_degree = sparta_profile_form.cleaned_data['grad_degree']

            try:
                ext_profile = ExtendedSpartaProfile.objects.get(user=request.user)
            except ExtendedSpartaProfile.DoesNotExist:
                ext_profile = ExtendedSpartaProfile(user=request.user)

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
    template_name = 'sparta_pathway_coupons.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(StudentCouponRecordsView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(StudentCouponRecordsView, self).get_context_data(**kwargs)
        pathway = get_object_or_404(Pathway, id=self.kwargs['pathway_id'])

        profile = self.request.user.sparta_profile
        student_records = StudentCouponRecord.objects.filter(profile=profile)

        coupons = []
        for c in pathway.courses.all().filter(is_active=True):
            course_screcord = student_records.filter(coupon__course_id=c.course_id)
            if course_screcord.exists():
                course_key = CourseKey.from_string(c.course_id)
                courseoverview = CourseOverview.get_from_id(course_key)
                coupon_data = {
                    'course_id': c.course_id,
                    'courseoverview': courseoverview,
                    'coupon_code': course_screcord[0].coupon.code
                }
                coupons.append(coupon_data)

        context['pathway'] = pathway
        context['coupons'] = coupons

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


def get_upload_params_json(request):
    def make_policy():
        policy_object = {
            "expiration": (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            "conditions": [
                { "bucket": settings.FILE_UPLOAD_STORAGE_BUCKET_NAME },
                { "acl": "public-read" },
                ["starts-with", "$key", "sparta_uploads/"],
                { "success_action_status": "201" }
            ]
        }
        return b64encode(dumps(policy_object).replace('\n', '').replace('\r', ''))

    def sign_policy(policy):
        return b64encode(hmac.new(settings.AWS_SECRET_ACCESS_KEY, policy, sha).digest())

    policy = make_policy()
    return {
        "policy": policy,
        "signature": sign_policy(policy),
        "key": "sparta_uploads/" + uuid4().hex + ".bin",
        "success_action_redirect": "/"
    }

def get_upload_params(request):
    def make_policy():
        policy_object = {
            "expiration": (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            "conditions": [
                { "bucket": settings.FILE_UPLOAD_STORAGE_BUCKET_NAME },
                { "acl": "public-read" },
                ["starts-with", "$key", "sparta_uploads/"],
                { "success_action_status": "201" }
            ]
        }
        return b64encode(dumps(policy_object).replace('\n', '').replace('\r', ''))

    def sign_policy(policy):
        return b64encode(hmac.new(settings.AWS_SECRET_ACCESS_KEY, policy, sha).digest())

    policy = make_policy()
    return HttpResponse(dumps({
        "policy": policy,
        "signature": sign_policy(policy),
        "key": "sparta_uploads/" + uuid4().hex + ".bin",
        "success_action_redirect": "/"
    }), content_type="application/json")


###############
# Admin Pages #
###############


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

    writer = csv.writer(response)
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
    import unicodecsv
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

    analytics = OverallAnalytics()
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
        'overall_graduation_rate': overall_graduation_rate
    }

    if request.method == "POST":
        form = ExportProfilesForm(request.POST)
        if form.is_valid():
            tnow = timezone.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
            filename = "sparta-overall-analytics-{}.csv".format(tnow)
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

            writer = csv.writer(response)
            writer.writerow([
                'timestamp',
                'overall_no_of_enrollees',
                'overall_no_of_learners_in_progress',
                'percent_of_learners_in_progress',
                'overall_no_of_active_learners',
                'percent_of_active_learners',
                'overall_no_of_inactive_learners',
                'percent_of_inactive_learners',
                'overall_no_of_dropped_out_learners',
                'overall_dropout_rate',
                'overall_no_of_graduates',
                'overall_graduation_rate'
                ])
            writer.writerow([
                tnow,
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

    analytics = PathwayAnalytics(pathway)

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

    if request.method == "POST":
        form = ExportAnalyticsForm(request.POST)
        if form.is_valid():
            tnow = timezone.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
            filename = "sparta-pathway-{}-analytics-{}.csv".format(str(slug), tnow)
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

            writer = csv.writer(response)
            writer.writerow([
                'timestamp',
                'pathway',
                'no_of_pathway_enrollees',
                'no_of_pathway_learners_in_progress',
                'percent_of_pathway_learners_in_progress',
                'no_of_active_pathway_learners',
                'percent_of_active_pathway_learners',
                'no_of_inactive_pathway_learners',
                'percent_of_inactive_pathway_learners',
                'no_of_dropped_out_pathway_learners',
                'pathway_dropout_rate',
                'no_of_pathway_graduates',
                'pathway_graduation_rate'
                ])
            writer.writerow([
                tnow,
                str(slug),
                no_of_pathway_enrollees,
                no_of_pathway_learners_in_progress,
                percent_of_pathway_learners_in_progress,
                no_of_active_pathway_learners,
                percent_of_active_pathway_learners,
                no_of_inactive_pathway_learners,
                percent_of_inactive_pathway_learners,
                no_of_dropped_out_pathway_learners,
                pathway_dropout_rate,
                no_of_pathway_graduates,
                pathway_graduation_rate
                ])
            return response

    context['form'] = ExportAnalyticsForm()

    return render(request, template_name, context)


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

    analytics = CourseAnalytics(course)

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

            writer = csv.writer(response)
            writer.writerow([
                'timestamp',
                'course_id',
                'no_of_learners_in_progress',
                'percent_of_learners_in_progress',
                'no_of_active_learners',
                'percent_of_active_learners',
                'no_of_inactive_learners',
                'percent_of_inactive_learners',
                'no_of_dropped_out_learners',
                'dropout_rate',
                'no_of_completed_learners',
                'completion_rate'
                ])
            writer.writerow([
                tnow,
                course_id,
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

    return render(request, template_name, context)
