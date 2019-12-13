from base64 import b64encode
from datetime import datetime, timedelta
from json import dumps
from mimetypes import guess_type
from os import path
from uuid import uuid4
import hmac
import sha

import boto
from boto import s3
from boto.s3.key import Key

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.forms import formset_factory
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from lms.djangoapps.certificates.models import certificate_status_for_student

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment

from .forms import (
    SpartaProfileForm, EducationProfileForm, EmploymentProfileForm,
    TrainingProfileForm, PathwayApplicationForm,
)
from .models import Pathway, SpartaCourse, SpartaProfile, EducationProfile, EmploymentProfile, TrainingProfile, PathwayApplication, Event


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

    pathway_courses = SpartaCourse.objects.filter(is_active=True).filter(pathway=pathway)
    courses = []
    for pathway_course in pathway_courses:
        course = {'pathway_course': pathway_course}
        course_key = CourseKey.from_string(pathway_course.course_id)
        courseoverview = CourseOverview.get_from_id(course_key)
        course['courseoverview'] = courseoverview
        courses.append(course)

    context['pathway'] = pathway
    context['courses'] = courses

    return render(request, template_name, context)


class RegistrationPageView(View):
    """
    """
    sparta_profile_form_class = SpartaProfileForm
    educ_formset_class = formset_factory(EducationProfileForm, extra=5)
    employ_formset_class = formset_factory(EmploymentProfileForm, extra=5)
    train_formset_class = formset_factory(TrainingProfileForm, extra=5)
    template_name = "sparta_register.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(RegistrationPageView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if SpartaProfile.objects.filter(user=request.user):
            return redirect('sparta-profile')
        sparta_profile_form = self.sparta_profile_form_class()
        educationFormset = self.educ_formset_class()
        employmentFormset = self.employ_formset_class()
        trainingFormset = self.train_formset_class()
        context = {
            'sparta_profile_form': sparta_profile_form,
            'educationFormset': educationFormset,
            'employmentFormset': employmentFormset,
            'trainingFormset': trainingFormset
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        sparta_profile_form = self.sparta_profile_form_class(request.POST, request.FILES)
        educationFormset = self.educ_formset_class(request.POST)
        employmentFormset = self.employ_formset_class(request.POST)
        trainingFormset = self.train_formset_class(request.POST)
        if sparta_profile_form.is_valid() and educationFormset.is_valid() and employmentFormset.is_valid() and trainingFormset.train_form():
            proof_of_education_file = sparta_profile_form.cleaned_data['proof_of_education_file']
            proof_of_agreement_file = sparta_profile_form.cleaned_data['proof_of_agreement_file']

            s3_response = upload_to_s3(request.user, proof_of_education_file, proof_of_agreement_file)

            proof_of_education_url = s3_response.get('proof_of_education_url', "")
            proof_of_agreement_url = s3_response.get('proof_of_agreement_url', "")

            try:
                sprofile = SpartaProfile.objects.get(user=request.user)
            except SpartaProfile.DoesNotExist:
                sprofile = SpartaProfile(user=request.user)
            sprofile.proof_of_education = proof_of_education_url
            sprofile.proof_of_agreement = proof_of_agreement_url
            sprofile.save()

            for f in educationFormset:
                degree = f.cleaned_data['degree']
                course = f.cleaned_data['course']
                school = f.cleaned_data['school']
                address = f.cleaned_data['address']
                started_at = f.cleaned_data['started_at']
                graduated_at = f.cleaned_data['graduated_at']
                edprofile = EducationProfile.objects.create(
                    profile=sprofile,
                    degree=degree,
                    course=course,
                    school=school,
                    address=address,
                    started_at=started_at,
                    graduated_at=graduated_at
                )

            for f in employmentFormset:
                affiliation = f.cleaned_data['affiliation']
                occupation = f.cleaned_data['occupation']
                designation = f.cleaned_data['designation']
                employer = f.cleaned_data['employer']
                address = f.cleaned_data['address']
                started_at = f.cleaned_data['started_at']
                ended_at = f.cleaned_data['ended_at']
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

            for f in trainingFormset:
                title = f.cleaned_data['title']
                organizer = f.cleaned_data['organizer']
                address = f.cleaned_data['address']
                started_at = f.cleaned_data['started_at']
                ended_at = f.cleaned_data['ended_at']
                tprofile = TrainingProfile.objects.create(
                    profile=sprofile,
                    organizer=organizer,
                    address=address,
                    started_at=started_at,
                    ended_at=ended_at
                )

            return redirect(reverse('sparta-register-success'))
        context = {
            'sparta_profile_form': sparta_profile_form,
            'educationFormset': educationFormset,
            'employmentFormset': employmentFormset,
            'trainingFormset': trainingFormset
        }
        return render(request, self.template_name, context)


def upload_to_s3(user, proof_of_education_file, proof_of_agreement_file):
    """"""
    c = s3.connection.S3Connection(
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY
    )
    nonexistent = c.lookup(settings.FILE_UPLOAD_STORAGE_BUCKET_NAME)
    if nonexistent is None:
        raise Exception("No valid S3 Bucket set for image uploading.")

    b = c.get_bucket(settings.FILE_UPLOAD_STORAGE_BUCKET_NAME, validate=False) # substitute your bucket name here
    blocation = str(b.get_location())

    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    educ_key = Key(b)
    educ_key.key = 'proof_of_education_{}_{}'.format(user.username, tnow)
    educ_key.set_contents_from_file(proof_of_education_file)
    educ_url = "https://{}.{}.amazonaws.com/sparta_uploads/{}".format(settings.FILE_UPLOAD_STORAGE_BUCKET_NAME, blocation, educ_key.key)

    agree_key = Key(b)
    agree_key.key = 'proof_of_agreement_{}_{}'.format(user.username, tnow)
    agree_key.set_contents_from_file(proof_of_agreement_file)
    agree_url = "https://{}.{}.amazonaws.com/sparta_uploads/{}".format(settings.FILE_UPLOAD_STORAGE_BUCKET_NAME, blocation, agree_key.key)

    return {'proof_of_education_url': educ_url, 'proof_of_agreement_url': agree_url}


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
        context['applications'] = PathwayApplication.objects.all().exclude(status='WE')
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        try:
            profile = SpartaProfile.objects.get(user=request.user)
        except SpartaProfile.DoesNotExist:
            return redirect('sparta-main')
        return render(request, self.template_name, context)


class PathwayApplicationView(TemplateView):
    # form_class = PathwayApplicationForm
    template_name = 'sparta_apply.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(PathwayApplicationView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PathwayApplicationView, self).get_context_data(**kwargs)
        context['pathways'] = Pathway.objects.filter(is_active=True)
        fail_app = kwargs.get('fail_app', None)
        if fail_app:
            context['fail_app'] = fail_app
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        # context['form'] = self.form_class()
        return render(request, self.template_name, context)

    # def post(self, request, *args, **kwargs):
    #     form = self.form_class(request.POST)
    #     if form.is_valid():
    #         pathway = form.cleaned_data['pathway']
    #         try:
    #             app = PathwayApplication.objects.get(profile=request.user.sparta_profile, pathway=pathway)
    #         except PathwayApplication.DoesNotExist:
    #             app = PathwayApplication.objects.create(profile=request.user.sparta_profile, pathway=pathway)
    #         if app.status in ["DE", "AP"]:
    #             context = get_context_data(**{'fail_app': True})
    #             return render(request, template_name, context)
    #         app.pend()
    #         Event.objects.create(
    #             event="Application Submitted",
    #             description="User {} has submitted an application for learning pathway {}.".format(app.profile.user.username, app.pathway.name),
    #             profile=app.profile
    #         )
    #         return redirect('sparta-profile')
    #     context = self.get_context_data()
    #     context['form'] = form
    #     return render(request, self.template_name, context)


@require_POST
def apply(request, id):
    """"""
    try:
        pathway = Pathway.objects.get(id=id)
    except Pathway.DoesNotExist:
        raise HttpResponse(status=500)

    try:
        sparta_profile = SpartaProfile.objects.get(user=request.user)
    except SpartaProfile.DoesNotExist:
        raise HttpResponse(status=403)

    app, created = PathwayApplication.objects.get_or_create(profile=sparta_profile, pathway=pathway)
    app.pend()

    return redirect('sparta-profile')


@require_POST
def widthraw(request, id):
    """"""
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
        context = self.get_context_data()

        pathway = get_object_or_404(Pathway, id=self.kwargs['pathway_id'])
        context['pathway'] = pathway

        courses = []
        for pathway_course in pathway.courses.all():
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

@login_required
def admin_main_view(request):
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_admin.html"
    context = {}

    return render(request, template_name, context)


@login_required
def admin_profiles_view(request):
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_admin_profiles.html"
    context = {}

    return render(request, template_name, context)


@login_required
def admin_applications_view(request):
    if not request.user.is_staff:
        raise Http404

    template_name = "sparta_admin_applications.html"
    context = {}

    return render(request, template_name, context)
