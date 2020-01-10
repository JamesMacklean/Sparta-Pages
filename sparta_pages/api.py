import base64
import json
from decimal import Decimal

from django.utils import timezone
from django.contrib.auth import get_user_model
USER_MODEL = get_user_model()

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from courseware.models import StudentModule
from lms.djangoapps.certificates.models import certificate_status_for_student
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment

from .models import (
    Pathway, SpartaCourse, SpartaProfile, PathwayApplication,
    EducationProfile, EmploymentProfile, TrainingProfile,
    APIToken
)


def get_header_token(request):
    """
    function to get access token from request header
    """
    header = request.META
    if 'HTTP_AUTHORIZATION' in header:
        htoken = header['HTTP_AUTHORIZATION']
    elif 'AUTHORIZATION' in header:
        htoken = header['AUTHORIZATION']
    else:
        raise Exception("No authorization header token found.")

    token_split = htoken.split(' ')
    return token_split[1]


def authenticate(request):
    token = get_header_token(request)
    token_decoded = token.base64.b64decode(token)
    token_key = token_decoded.strip(':')
    if not APIToken.objects.filter(is_active=True, key=token_key).exists():
        return False
    return True


def get_average_completion_rate(course_id):
    course_key = CourseKey.from_string(course_id)

    enrollments = CourseEnrollment.objects.filter(
        course_id=course_key,
        is_active=True,
        mode="verified"
    )
    modules = StudentModule.objects.filter(course_id=course_key)

    total_seconds_list = []
    for e in enrollments:
        user = e.user

        cert_status = certificate_status_for_student(user, course_key)
        if cert_status and cert_status['mode'] == 'verified' and cert_status['status'] not in  ['unavailable', 'notpassing', 'restricted', 'unverified']:
            pass
        else:
            continue

        student_modules = modules.filter(student=user)

        course_module = student_modules.filter(module_type='course').order_by('created_date').first()
        if course_module:
            started_course_at = course_module.created_date
        else:
            continue

        latest_student_module = student_modules.order_by('-modified_date').first()
        if latest_student_module:
            ended_course_at = latest_student_module.modified_date
        else:
            continue

        finish_duration = Decimal(ended_course_at - started_course_at)
        total_seconds_list.append(finish_duration.total_seconds())

    if total_seconds_list:
        return str(sum(total_seconds_list) / len(total_seconds_list))
    else:
        return "unavailable"


@api_view(['GET'])
def pathway_list_view(request, format=None):
    try:
        auth = authenticate(request)
    except Exception as e:
        return Response(str(e), status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        return Response("Request unauthorized", status=status.HTTP_401_UNAUTHORIZED)

    data = []
    queryset = Pathway.objects.all()

    name = self.request.query_params.get('name', None)
    if name is not None:
        queryset = queryset.filter(name=name)

    offset = request.query_params.get('offset', None)
    if offset is not None and offset != '':
        of = int(offset)
        queryset = queryset[of:]
    limit = request.query_params.get('limit', None)
    if limit is not None and limit != '':
        lim = int(limit)
        queryset = queryset[:lim]

    for pathway in queryset:
        pathway_data = {
            'id': pathway.id,
            'name': pathway.name,
            'num_courses': pathway.courses.filter(is_active=True).count()
        }
        data.append(pathway_data)

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def pathway_detail_view(request, id, format=None):
    try:
        auth = authenticate(request)
    except Exception as e:
        return Response(str(e), status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        return Response("Request unauthorized", status=status.HTTP_401_UNAUTHORIZED)

    try:
        pathway = Pathway.objects.get(id=id)
    except Pathway.DoesNotExist:
        return Response("Pathway with id {} does not exist.".format(id), status=status.HTTP_404_NOT_FOUND)

    courses = []
    for pathway_course in pathway.courses.all():
        course_id = pathway_course.course_id
        course_key = CourseKey.from_string(course_id)
        courseoverview = CourseOverview.get_from_id(course_key)
        course = {
            'course_id': course_id,
            'name': courseoverview.display_name,
            'partner': courseoverview.org,
            'start': courseoverview.start,
            'end': courseoverview.end,
            'lowest_passing_grade': courseoverview.lowest_passing_grade,
            'enrollment_start': courseoverview.enrollment_start,
            'enrollment_end': courseoverview.enrollment_end,
            'short_description': courseoverview.short_description,
            'num_of_enrollees': CourseEnrollment.objects.filter(
                course_id=course_key,
                is_active=True
            ).count(),
            'num_of_verified_enrollees': CourseEnrollment.objects.filter(
                course_id=course_key,
                is_active=True,
                mode="verified"
            ).count(),
            'average_completion_rate': get_average_completion_rate(course_id)
        }
        courses.append(course)
    data = {
        'id': pathway.id,
        'name': pathway.name,
        'courses': courses
    }

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def course_list_view(request, format=None):
    try:
        auth = authenticate(request)
    except Exception as e:
        return Response(str(e), status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        return Response("Request unauthorized", status=status.HTTP_401_UNAUTHORIZED)

    data = []
    queryset = SpartaCourse.objects.all()

    course_id = self.request.query_params.get('course_id', None)
    pathway = self.request.query_params.get('pathway', None)

    if course_id is not None:
        queryset = queryset.filter(course_id=course_id)
    if pathway is not None:
        queryset = queryset.filter(pathway__name=pathway)

    offset = request.query_params.get('offset', None)
    if offset is not None and offset != '':
        of = int(offset)
        queryset = queryset[of:]
    limit = request.query_params.get('limit', None)
    if limit is not None and limit != '':
        lim = int(limit)
        queryset = queryset[:lim]

    for sparta_course in queryset:
        course_key = CourseKey.from_string(sparta_course.course_id)
        courseoverview = CourseOverview.get_from_id(course_key)
        course = {
            'course_id': sparta_course.course_id,
            'name': courseoverview.display_name,
            'partner': courseoverview.org,
            'start': courseoverview.start,
            'end': courseoverview.end,
            'lowest_passing_grade': courseoverview.lowest_passing_grade,
            'enrollment_start': courseoverview.enrollment_start,
            'enrollment_end': courseoverview.enrollment_end,
            'short_description': courseoverview.short_description,
            'num_of_enrollees': CourseEnrollment.objects.filter(
                course_id=course_key,
                is_active=True
            ).count(),
            'num_of_verified_enrollees': CourseEnrollment.objects.filter(
                course_id=course_key,
                is_active=True,
                mode="verified"
            ).count(),
            'average_completion_rate': get_average_completion_rate(course_id)
        }
        data.append(course)

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def course_detail_view(request, id, format=None):
    try:
        auth = authenticate(request)
    except Exception as e:
        return Response(str(e), status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        return Response("Request unauthorized", status=status.HTTP_401_UNAUTHORIZED)

    try:
        course = SpartaCourse.objects.get(id=id)
    except SpartaCourse.DoesNotExist:
        return Response("Sparta Course with id {} not found.".format(id), status=status.HTTP_404_NOT_FOUND)

    course_key = CourseKey.from_string(course.course_id)
    courseoverview = CourseOverview.get_from_id(course_key)
    data = {
        'course_id': course.course_id,
        'name': courseoverview.display_name,
        'partner': courseoverview.org,
        'start': courseoverview.start,
        'end': courseoverview.end,
        'lowest_passing_grade': courseoverview.lowest_passing_grade,
        'enrollment_start': courseoverview.enrollment_start,
        'enrollment_end': courseoverview.enrollment_end,
        'short_description': courseoverview.short_description,
        'num_of_enrollees': CourseEnrollment.objects.filter(
            course_id=course_key,
            is_active=True
        ).count(),
        'num_of_verified_enrollees': CourseEnrollment.objects.filter(
            course_id=course_key,
            is_active=True,
            mode="verified"
        ).count(),
        'average_completion_rate': get_average_completion_rate(course_id)
    }

    return Response(data, status=status.HTTP_200_OK)


def get_student_enrollment_status(student, course_key):
    cert_status = certificate_status_for_student(student.user, course_key)
    if cert_status and cert_status['mode'] == 'verified' and cert_status['status'] not in  ['unavailable', 'notpassing', 'restricted', 'unverified']:
        return "completed"

    modules = StudentModule.objects.filter(course_id=course_key, student=student.user)
    if modules.exists():
        latest_student_module = student_modules.order_by('-modified_date').first()
        diff_time =  timezome.now() - latest_student_module.modified_date
        diff_time_secs = diff_time.total_seconds()
        if diff_time_secs > 604800:
            return "inactive"
        else:
            return "in_progress"
    else:
        return "unenrolled"


def get_average_grade_percent(student, courses_enrolled_in):
    grades_list = []
    for course in courses_enrolled_in:
        course_key = CourseKey.from_string(course.course_id)
        grade = CourseGradeFactory().read(student.user, course_key=course_key)
        grades_list.append(Decimal(grade.percent))
    return str(sum(grades_list) / len(grades_list))


@api_view(['GET'])
def student_list_view(request, format=None):
    try:
        auth = authenticate(request)
    except Exception as e:
        return Response(str(e), status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        return Response("Request unauthorized", status=status.HTTP_401_UNAUTHORIZED)

    queryset = SpartaProfile.objects.all()

    pathway = self.request.query_params.get('pathway', None)
    course_id = self.request.query_params.get('course_id', None)

    if pathway is not None:
        queryset = queryset.filter(applications__pathway__name=pathway)
    if course_id is not None:
        queryset = queryset.filter(applications__pathway__courses__course_id=course_id)

    offset = request.query_params.get('offset', None)
    if offset is not None and offset != '':
        of = int(offset)
        queryset = queryset[of:]
    limit = request.query_params.get('limit', None)
    if limit is not None and limit != '':
        lim = int(limit)
        queryset = queryset[:lim]

    data = []
    for student in queryset:
        pathway_courses = SpartaCourse.objects.none()
        pathway_list = []
        for a in student.applications.all().filter(status="AP"):
            this_pathway_courses = a.pathway.courses.all().filter(is_active=True)

            completed_count = 0
            for course in this_pathway_courses:
                course_key = CourseKey.from_string(course.course_id)
                cert_status = certificate_status_for_student(student.user, course_key)
                if cert_status and cert_status['mode'] == 'verified' and cert_status['status'] not in  ['unavailable', 'notpassing', 'restricted', 'unverified']:
                    completed_count += 1

            pathway_list.append({
                'name': a.pathway.name,
                'completed': completed_count == this_pathway_courses.count()
            })
            pathway_courses |=  this_pathway_courses


        courses_enrolled_in = []
        for course in pathway_courses:
            course_key = CourseKey.from_string(course.course_id)
            courseoverview = CourseOverview.get_from_id(course_key)
            if CourseEnrollment.objects.filter(course_id=course_key, is_active=True, mode="verified"):
                courses_enrolled_in.append({
                    'name': courseoverview.display_name,
                    'course_id': course.course_id,
                    'status': get_student_enrollment_status(student, course_key)
                })

        student_data = {
            'id': student.id,
            'pathways': pathway_list,
            'courses_enrolled_in': courses_enrolled_in,
            'registered_at': student.created_at,
            'last_login': student.last_login,
            'average_grade_percent': get_average_grade_percent(student, courses_enrolled_in)
        }
        data.append(student_data)

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def student_detail_view(request, id, format=None):
    try:
        auth = authenticate(request)
    except Exception as e:
        return Response(str(e), status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        return Response("Request unauthorized", status=status.HTTP_401_UNAUTHORIZED)

    try:
        student = SpartaProfile.objects.get(id=id)
    except SpartaProfile.DoesNotExist:
        return Response("Student profile with id {} not found.".format(id), status=status.HTTP_404_NOT_FOUND)

    pathway_courses = SpartaCourse.objects.none()
    pathway_list = []
    for a in student.applications.all().filter(status="AP"):
        this_pathway_courses = a.pathway.courses.all().filter(is_active=True)

        completed_count = 0
        for course in this_pathway_courses:
            course_key = CourseKey.from_string(course.course_id)
            cert_status = certificate_status_for_student(student.user, course_key)
            if cert_status and cert_status['mode'] == 'verified' and cert_status['status'] not in  ['unavailable', 'notpassing', 'restricted', 'unverified']:
                completed_count += 1

        pathway_list.append({
            'name': a.pathway.name,
            'completed': completed_count == this_pathway_courses.count()
        })
        pathway_courses |=  this_pathway_courses


    courses_enrolled_in = []
    for course in pathway_courses:
        course_key = CourseKey.from_string(course.course_id)
        courseoverview = CourseOverview.get_from_id(course_key)
        if CourseEnrollment.objects.filter(course_id=course_key, is_active=True, mode="verified"):
            courses_enrolled_in.append({
                'name': courseoverview.display_name,
                'course_id': course.course_id,
                'status': get_student_enrollment_status(student, course_key)
            })

    data = {
        'id': student.id,
        'pathways': pathway_list,
        'courses_enrolled_in': courses_enrolled_in,
        'registered_at': student.created_at,
        'last_login': student.last_login,
        'average_grade_percent': get_average_grade_percent(student, courses_enrolled_in)
    }

    return Response(data, status=status.HTTP_200_OK)
