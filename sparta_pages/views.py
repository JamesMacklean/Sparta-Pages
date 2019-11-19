from django.shortcuts import render,get_object_or_404
from django.http import Http404

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from opaque_keys.edx.keys import CourseKey


def main(request):
    """"""
    template_name = "sparta_main.html"
    context = {"pathways": Pathway.objects.filter(is_active=True)}
    return render(request, template_name, context)


def pathway(request, slug):
    """"""
    template_name = "sparta_pathway.html"
    context = {}

    pathway = get_object_or_404(Pathway, slug=slug)

    pathway_courses = SpartaCourse.objects.filter(is_active=True).filter(pathway=pathway)
    courses = []
    for pathway_course in pathway_courses:
        course_key = CourseKey.from_string(pathway_course.course_id)
        courseoverview = CourseOverview.get_from_id(course_key)
        courses.append(courseoverview)

    context['pathway'] = pathway
    context['courses'] = courses

    return render(request, template_name, context)
