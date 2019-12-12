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
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from opaque_keys.edx.keys import CourseKey

from .forms import SpartaProfileForm, EducationProfileForm, EmploymentProfileForm, TrainingProfileForm, PathwayApplicationForm
from .models import Pathway, SpartaCourse, SpartaProfile, EducationProfile, EmploymentProfile, TrainingProfile, PathwayApplication


#################
# Learner Pages #
################

def main(request):
    """"""
    template_name = "sparta_main.html"
    context = {}

    pathways = Pathway.objects.filter(is_active=True)

    context['pathways'] = pathways

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


def demo_registration_page(request):
    """ /sparta/register/demo/ """
    template_name = "sparta_register_demo.html"
    context = {
        'AWS_S3_BUCKET_URL': "https://{}.s3.amazonaws.com/".format(settings.FILE_UPLOAD_STORAGE_BUCKET_NAME),
        'AWS_ACCESS_KEY_ID': settings.AWS_ACCESS_KEY_ID
    }
    return render(request, template_name, context)


class RegistrationPageView(View):
    """
    """
    form_class = SpartaProfileForm
    template_name = "sparta_register.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(RegistrationPageView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            proof_of_education_file = form.cleaned_data['proof_of_education_file']
            proof_of_agreement_file = form.cleaned_data['proof_of_agreement_file']
            first_timer = form.cleaned_data['first_timer']

            s3_response = upload_to_s3(request.user, proof_of_education_file, proof_of_agreement_file)

            proof_of_education_url = s3_response.get('proof_of_education_file')
            proof_of_agreement_url = s3_response.get('proof_of_agreement_file')

            try:
                sprofile = SpartaProfile.objects.get(user=request.user)
            except SpartaProfile.DoestNotExist:
                sprofile = SpartaProfile(user=request.user)
            sprofile.proof_of_education = proof_of_education_url
            sprofile.proof_of_agreement = proof_of_agreement_url
            sprofile.first_timer = first_timer
            sprofile.save()

            return redirect(reverse('sparta-register-success'))
        return render(request, self.template_name, {'form': form})


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


def sparta_profile_page(request, profile_id):
    """ /sparta/profile/{profile_id}/ """
    template_name = "sparta_profile.html"
    context = {}

    return render(request, template_name, context)


def application_page(request, profile_id):
    """ /sparta/profile/{profile_id}/apply/ """
    template_name = "sparta_apply.html"
    context = {}

    if request.method == 'POST':
        form = PathwayApplicationForm(request.POST)
        if form.is_valid():

            return redirect('sparta-profile', profile_id=profile_id)
    else:
        form = PathwayApplicationForm()

    return render(request, template_name, context)


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
