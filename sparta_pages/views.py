from base64 import b64encode
from datetime import datetime, timedelta
from json import dumps
from mimetypes import guess_type
from os import path
from uuid import uuid4
import hmac
import sha

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from opaque_keys.edx.keys import CourseKey

from .forms import SpartaProfileForm, EducationProfileForm, EmploymentProfileForm, TrainingProfileForm, PathwayApplicationForm
from .models import Pathway, SpartaCourse


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


def registration_page(request):
    """ /sparta/register/ """
    template_name = "sparta_register.html"
    context = {
    'AWS_S3_BUCKET_URL': "http://{}.s3.amazonaws.com/".format(settings.FILE_UPLOAD_STORAGE_BUCKET_NAME),
    'AWS_ACCESS_KEY_ID': settings.AWS_ACCESS_KEY_ID
    }
    return render(request, template_name, context)


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
