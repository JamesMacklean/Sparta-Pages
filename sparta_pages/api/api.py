import base64
import coreapi
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
USER_MODEL = get_user_model()

from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from rest_framework import status, renderers
from rest_framework.decorators import api_view, permission_classes, authentication_classes, renderer_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_yaml.renderers import YAMLRenderer
from rest_framework_swagger.renderers import OpenAPIRenderer

from courseware.models import StudentModule
from lms.djangoapps.certificates.models import certificate_status_for_student
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment

from ..analytics import (
    get_average_completion_rate, get_student_enrollment_status,
    get_average_grade_percent,
)
from ..models import (
    Pathway, SpartaCourse, SpartaProfile, PathwayApplication,
    EducationProfile, EmploymentProfile, TrainingProfile,
    APIToken
)
from .utils import (
    get_applications_count_per_pathway,
    get_applications_count_per_status,
    get_applications_count_per_week,
    get_weekly_enrollments_count_by_pathway,
    get_sparta_course_id_list,
    get_course_weekly_enrollments,
    get_course_completion_rates,
    get_course_learner_activity,
    get_sparta_enrollees_by_age,
    get_sparta_enrollees_by_gender,
    get_sparta_enrollees_by_affiliation,
    get_sparta_enrollees_by_attainment,
    get_sparta_enrollees_by_location
)


@api_view()
@renderer_classes([OpenAPIRenderer])
def schema_view(request):
    schema = coreapi.Document(
        title='SPARTA Analytics API',
        url=LOCAL_REDOC_SCHEMA_URL,
        content={
            'pathways': {
                'list': coreapi.Link(
                    title='Pathway List',
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
                'detail': coreapi.Link(
                    title='Pathway Detail',
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
            },
            'courses': {
                'list': coreapi.Link(
                    title='Course List',
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
                'detail': coreapi.Link(
                    title='Course Detail',
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
            },
            'students': {
                'list': coreapi.Link(
                    title='Student List',
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
                'detail': coreapi.Link(
                    title='Student Detail',
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
            },
        }
    )
    return Response(schema)


class RedocView(TemplateView):
    """"""
    template_name = 'sparta_redoc.html'

    def get_context_data(self, **kwargs):
        context = super(RedocView, self).get_context_data(**kwargs)
        context['schema_url'] = 'sparta-schema'
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

def basic_auth(request):
    token = get_header_token(request)
    token_decoded = base64.b64decode(token)
    token_key = token_decoded.strip(':')
    if token_key != SECRET_TOKEN:
        return False
    return True


@api_view(['GET'])
@authentication_classes([])
def pathway_applications_count_view(request, format=None):
    try:
        auth = basic_auth(request)
    except Exception as e:
        data = {"error": "unauthorized", "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        data = {"error": "unauthorized", "error_description": "Request unauthorized"}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    queryset = PathwayApplication.objects.all()

    data = {
        "total_count": queryset.count(),
        "pathways": get_applications_count_per_pathway(applications=queryset),
        "statuses": get_applications_count_per_status(applications=queryset),
        "weekly": get_applications_count_per_week(applications=queryset)
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def enrollments_count_view(request, format=None):
    try:
        auth = basic_auth(request)
    except Exception as e:
        data = {"error": "unauthorized", "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        data = {"error": "unauthorized", "error_description": "Request unauthorized"}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    course_enrollments = CourseEnrollment.objects.filter(is_active=True)

    query_params = request.query_params
    courses = query_params.get('courses', None)
    course_list = []
    if courses is not None:
        for course_id in courses.split(','):
            course_list.append(course_id)
    else:
        course_list = get_sparta_course_id_list()

    data = []
    for course_id in course_list:
        try:
            course_data = {
                "course_id": course_id,
                "weeks": get_course_weekly_enrollments(course_id, course_enrollments=course_enrollments)
            }
        except Exception as e:
            course_data = {
                "course_id": course_id,
                "weeks": None,
                "error": {
                    "detail": str(e)
                }
            }

        data.append(course_data)

    for i in range(0, len(data)):
        y = 3
        z = i % y
        if z == 0:
            data[i]['color'] = "#caf270"
        elif z == 1:
            data[i]['color'] = "#45c490"
        else:
            data[i]['color'] = "#008d93"

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def completion_rates_view(request, format=None):
    try:
        auth = basic_auth(request)
    except Exception as e:
        data = {"error": "unauthorized", "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        data = {"error": "unauthorized", "error_description": "Request unauthorized"}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    course_enrollments = CourseEnrollment.objects.filter(is_active=True)

    query_params = request.query_params
    courses = query_params.get('courses', None)
    course_list = []
    if courses is not None:
        for course_id in courses.split(','):
            course_list.append(course_id)
    else:
        course_list = get_sparta_course_id_list()

    data = []
    for course_id in course_list:
        try:
            this_course_enrollments = course_enrollments.filter(course=CourseOverview.get_from_id(CourseKey.from_string(course_id)))
            course_data = {
                "course_id": course_id,
                "completion_rates": get_course_completion_rates(course_id, course_enrollments=this_course_enrollments)
            }
        except Exception as e:
            course_data = {
                "course_id": course_id,
                "completion_rates": None,
                "error": {
                    "detail": str(e)
                }
            }
        data.append(course_data)

    for i in range(0, len(data)):
        y = 3
        z = i % y
        if z == 0:
            data[i]['color'] = "#caf270"
        elif z == 1:
            data[i]['color'] = "#45c490"
        else:
            data[i]['color'] = "#008d93"

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def learner_activity_view(request, format=None):
    try:
        auth = basic_auth(request)
    except Exception as e:
        data = {"error": "unauthorized", "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        data = {"error": "unauthorized", "error_description": "Request unauthorized"}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    course_enrollments = CourseEnrollment.objects.filter(is_active=True)

    query_params = request.query_params
    courses = query_params.get('courses', None)
    course_list = []
    if courses is not None:
        for course_id in courses.split(','):
            course_list.append(course_id)
    else:
        course_list = get_sparta_course_id_list()

    data = []
    for course_id in course_list:
        try:
            course_key = CourseKey.from_string(course_id)
            this_course_enrollments = course_enrollments.filter(course=CourseOverview.get_from_id(course_key))
            this_course_modules = StudentModule.objects.filter(course_id=course_key)
            course_data = {
                "course_id": course_id,
                "learner_activity": get_course_learner_activity(course_id, course_enrollments=this_course_enrollments, modules=this_course_modules)
            }
        except Exception as e:
            course_data = {
                "course_id": course_id,
                "learner_activity": None,
                "error": {
                    "detail": str(e)
                }
            }

        data.append(course_data)

    for i in range(0, len(data)):
        y = 3
        z = i % y
        if z == 0:
            data[i]['color'] = "#caf270"
        elif z == 1:
            data[i]['color'] = "#45c490"
        else:
            data[i]['color'] = "#008d93"

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def ages_count_view(request, format=None):
    try:
        auth = basic_auth(request)
    except Exception as e:
        data = {"error": "unauthorized", "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        data = {"error": "unauthorized", "error_description": "Request unauthorized"}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    data = get_sparta_enrollees_by_age()
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def gender_count_view(request, format=None):
    try:
        auth = basic_auth(request)
    except Exception as e:
        data = {"error": "unauthorized", "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        data = {"error": "unauthorized", "error_description": "Request unauthorized"}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    data = get_sparta_enrollees_by_gender()
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def affiliation_count_view(request, format=None):
    try:
        auth = basic_auth(request)
    except Exception as e:
        data = {"error": "unauthorized", "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        data = {"error": "unauthorized", "error_description": "Request unauthorized"}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    data = get_sparta_enrollees_by_affiliation()
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def attainment_count_view(request, format=None):
    try:
        auth = basic_auth(request)
    except Exception as e:
        data = {"error": "unauthorized", "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        data = {"error": "unauthorized", "error_description": "Request unauthorized"}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    data = get_sparta_enrollees_by_attainment()
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def location_count_view(request, format=None):
    try:
        auth = basic_auth(request)
    except Exception as e:
        data = {"error": "unauthorized", "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)
    if not auth:
        data = {"error": "unauthorized", "error_description": "Request unauthorized"}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    data = get_sparta_enrollees_by_location()
    return Response(data, status=status.HTTP_200_OK)


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
