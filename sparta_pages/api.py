import base64
import json
from decimal import Decimal

from django.utils import timezone
from django.contrib.auth import get_user_model
USER_MODEL = get_user_model()
from django.views.generic import TemplateView

from rest_framework import status, renderers, response
from rest_framework.decorators import api_view, permission_classes, authentication_classes, renderer_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
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
from .local_settings import LOCAL_REDOC_SCHEMA_URL


@api_view()
@renderer_classes([renderers.OpenAPIRenderer])
def schema_view(request):
    schema = coreapi.Document(
        title='SPARTA Analytics API',
        url=LOCAL_REDOC_SCHEMA_URL,
        content={
            'pathways': coreapi.Link(
                url='/sparta/api/v0/pathways/',
                action='get',
                fields=[
                    coreapi.Field(
                        name='offset',
                        required=False,
                        location='query',
                        description='Offset or from what index list will start.'
                    ),
                    coreapi.Field(
                        name='limit',
                        required=False,
                        location='query',
                        description='Limit or up to how many object will be retrieved.'
                    ),
                    coreapi.Field(
                        name='name',
                        required=False,
                        location='query',
                        description='Name of Learning Pathway to filter list.'
                    )
                ],
                description='Return list of Learning Pathways.'
            ),
            'pathway detail': coreapi.Link(
                url='/sparta/api/v0/pathways/{id}',
                action='get',
                fields=[
                    coreapi.Field(
                        name='id',
                        required=True,
                        location='path',
                        description='Id for this Learning Pathway.'
                    ),
                ],
                description='Return detail of specified Learning Pathway.'
            ),
            'courses': coreapi.Link(
                url='/sparta/api/v0/courses/',
                action='get',
                fields=[
                    coreapi.Field(
                        name='offset',
                        required=False,
                        location='query',
                        description='Offset or from what index list will start.'
                    ),
                    coreapi.Field(
                        name='limit',
                        required=False,
                        location='query',
                        description='Limit or up to how many objects will be retrieved.'
                    ),
                    coreapi.Field(
                        name='pathway',
                        required=False,
                        location='query',
                        description='Name of Learning Pathway to filter list.'
                    ),
                    coreapi.Field(
                        name='course_id',
                        required=False,
                        location='query',
                        description='Unique course_id of a course to filter list.'
                    )
                ],
                description='Return list of SPARTA Courses.'
            ),
            'course detail': coreapi.Link(
                url='/sparta/api/v0/courses/{id}',
                action='get',
                fields=[
                    coreapi.Field(
                        name='id',
                        required=True,
                        location='path',
                        description='sparta_id for this SPARTA Course (different from course_id).'
                    ),
                ],
                description='Return detail of specified SPARTA Course.'
            ),
            'students': coreapi.Link(
                url='/sparta/api/v0/students/',
                action='get',
                fields=[
                    coreapi.Field(
                        name='offset',
                        required=False,
                        location='query',
                        description='Offset or from what index list will start.'
                    ),
                    coreapi.Field(
                        name='limit',
                        required=False,
                        location='query',
                        description='Limit or up to how many objects will be retrieved.'
                    ),
                    coreapi.Field(
                        name='pathway',
                        required=False,
                        location='query',
                        description='Name of Learning Pathway to filter list.'
                    ),
                    coreapi.Field(
                        name='course_id',
                        required=False,
                        location='query',
                        description='Unique course_id of a course enrolled in to filter list.'
                    )
                ],
                description='Return list of Students/SPARTA Learners.'
            ),
            'student detail': coreapi.Link(
                url='/sparta/api/v0/students/{id}',
                action='get',
                fields=[
                    coreapi.Field(
                        name='id',
                        required=True,
                        location='path',
                        description='Id for this Student/SPARTA Learner.'
                    ),
                ],
                description='Return detail of specified Student/SPARTA Learner.'
            )
        }
    )
    return response.Response(schema)


class RedocView(TemplateView):
    """"""
    template_name = 'sparta_redoc.html'

    def get_context_data(self, **kwargs):
        context = super(RedocView, self).get_context_data(**kwargs)
        context['schema_url'] = reverse('sparta-schema')
        return context


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
    if len(token_split) < 2:
        raise Exception("No authorization header token found.")

    return token_split[1]


def authenticate(request):
    token = get_header_token(request)
    token_decoded = base64.b64decode(token)
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

        course_module = student_modules.filter(module_type='course').order_by('created').first()
        if course_module:
            started_course_at = course_module.created
        else:
            continue

        latest_student_module = student_modules.order_by('-modified').first()
        if latest_student_module:
            ended_course_at = latest_student_module.modified
        else:
            continue

        finish_duration = ended_course_at - started_course_at
        finish_duration_decimal = Decimal(finish_duration.total_seconds())
        total_seconds_list.append(finish_duration_decimal)

    if total_seconds_list:
        return str(sum(total_seconds_list) / len(total_seconds_list))
    else:
        return "unavailable"


@api_view(['GET'])
@authentication_classes([])
def pathway_list_view(request, format=None):
    try:
        auth = authenticate(request)
    except Exception as e:
        return Response("Request unauthorized: {}".format(str(e)), status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        return Response("Request unauthorized", status=status.HTTP_401_UNAUTHORIZED)

    data = []
    queryset = Pathway.objects.all()

    name = request.query_params.get('name', None)
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
@authentication_classes([])
def pathway_detail_view(request, id, format=None):
    try:
        auth = authenticate(request)
    except Exception as e:
        return Response("Request unauthorized: {}".format(str(e)), status=status.HTTP_401_UNAUTHORIZED)
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
            'id': pathway_course.id,
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
@authentication_classes([])
def course_list_view(request, format=None):
    try:
        auth = authenticate(request)
    except Exception as e:
        return Response("Request unauthorized: {}".format(str(e)), status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        return Response("Request unauthorized", status=status.HTTP_401_UNAUTHORIZED)

    data = []
    queryset = SpartaCourse.objects.all()

    course_id = request.query_params.get('course_id', None)
    pathway = request.query_params.get('pathway', None)

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
            'id': sparta_course.id,
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
            'average_completion_rate': get_average_completion_rate(sparta_course.course_id)
        }
        data.append(course)

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def course_detail_view(request, id, format=None):
    try:
        auth = authenticate(request)
    except Exception as e:
        return Response("Request unauthorized: {}".format(str(e)), status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        return Response("Request unauthorized", status=status.HTTP_401_UNAUTHORIZED)

    try:
        course = SpartaCourse.objects.get(id=id)
    except SpartaCourse.DoesNotExist:
        return Response("Sparta Course with id {} not found.".format(id), status=status.HTTP_404_NOT_FOUND)

    course_key = CourseKey.from_string(course.course_id)
    courseoverview = CourseOverview.get_from_id(course_key)
    data = {
        'id': course.id,
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
        'average_completion_rate': get_average_completion_rate(course.course_id)
    }

    return Response(data, status=status.HTTP_200_OK)


def get_student_enrollment_status(student, course_key):
    cert_status = certificate_status_for_student(student.user, course_key)
    if cert_status and cert_status['mode'] == 'verified' and cert_status['status'] not in  ['unavailable', 'notpassing', 'restricted', 'unverified']:
        return "completed"

    modules = StudentModule.objects.filter(course_id=course_key, student=student.user)
    if modules.exists():
        latest_student_module = modules.order_by('-modified').first()
        diff_time =  timezone.now() - latest_student_module.modified
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
        course_key = CourseKey.from_string(course['course_id'])
        grade = CourseGradeFactory().read(student.user, course_key=course_key)
        grades_list.append(Decimal(grade.percent))
    if grades_list:
        return str(round(sum(grades_list) / len(grades_list), 4))
    else:
        return "unavailable"


@api_view(['GET'])
@authentication_classes([])
def student_list_view(request, format=None):
    try:
        auth = authenticate(request)
    except Exception as e:
        return Response("Request unauthorized: {}".format(str(e)), status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        return Response("Request unauthorized", status=status.HTTP_401_UNAUTHORIZED)

    queryset = SpartaProfile.objects.all()

    pathway = request.query_params.get('pathway', None)
    course_id = request.query_params.get('course_id', None)

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
            'last_login': student.user.last_login,
            'average_grade_percent': get_average_grade_percent(student, courses_enrolled_in)
        }
        data.append(student_data)

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def student_detail_view(request, id, format=None):
    try:
        auth = authenticate(request)
    except Exception as e:
        return Response("Request unauthorized: {}".format(str(e)), status=status.HTTP_401_UNAUTHORIZED)
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
        'last_login': student.user.last_login,
        'average_grade_percent': get_average_grade_percent(student, courses_enrolled_in)
    }

    return Response(data, status=status.HTTP_200_OK)
