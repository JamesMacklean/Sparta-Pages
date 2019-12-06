from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.views.decorators.http import require_POST

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from opaque_keys.edx.keys import CourseKey

from .models import Pathway, SpartaCourse


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


def sparta_profile_page(request):
    template_name = "sparta_register.html"
    context = {}

    return render(request, template_name, context)


def registration_page(request):
    """"""
    template_name = "sparta_register.html"
    context = {}

    return render(request, template_name, context)


@require_POST()
def register(request):
    """"""

    return redirect('sparta-register-success')


def register_success_page(request):
    """"""
    template_name = "sparta_register_success.html"
    context = {}

    return render(request, template_name, context)


def application_page(request):
    """"""
    template_name = "sparta_apply.html"
    context = {}

    return render(request, template_name, context)


@require_POST()
def apply(request, pathway_id):
    """"""

    return redirect('sparta-pathway-apply')
