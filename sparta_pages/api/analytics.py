import base64
import six

from django.contrib.auth import get_user_model
User = get_user_model()

from courseware.models import StudentModule
from lms.djangoapps.certificates.api import get_certificate_for_user
from lms.djangoapps.certificates.models import certificate_status_for_student
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment

from rest_framework import status, renderers
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response

from ..local_settings import LOCAL_SECRET_TOKEN as SECRET_TOKEN
from .serializers import (
    PathwaySerializer, SpartaCourseSerializer,
    SpartaProfileSerializer, ExtendedSpartaProfileSerializer,
    EmploymentProfileSerializer, EducationProfileSerializer,
    PathwayApplicationSerializer
)
from ..models import (
    Pathway, SpartaCourse, SpartaProfile, PathwayApplication,
    EducationProfile, EmploymentProfile
)

class UnauthorizedError(Exception):
    pass

class CustomAuth():
    def get_header_token(self, request):
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

    def basic_auth(self, request):
        token = self.get_header_token(request)
        token_decoded = base64.b64decode(token)
        token_key = token_decoded.decode('ascii').strip(':')
        if token_key != SECRET_TOKEN:
            return False
        return True

    def authenticate(self, request):
        try:
            auth = self.basic_auth(request)
        except Exception as e:
            raise UnauthorizedError(str(e))
        if not auth:
            raise UnauthorizedError("Invalid token.")

authenticate_request = CustomAuth().authenticate

def merge(d1, d2):
    return (d1.update(d2))

@api_view(['GET'])
@authentication_classes([])
def sparta_profiles_list(request, format=None):
    """
    /sparta/api/v1/profiles/
    """
    try:
        authenticate_request(request)
    except UnauthorizedError as e:
        data = {"error": "unauthorized",
                "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    queryset = SpartaProfile.objects.select_related(
        'user', 'user__profile'
    ).order_by(
        '-created_at'
    )

    offset = request.query_params.get('offset', None)
    if offset is not None and offset != '':
        of = int(offset)
        queryset = queryset[of:]
    limit = request.query_params.get('limit', None)
    if limit is not None and limit != '':
        lim = int(limit)
        queryset = queryset[:lim]

    result_data = []
    for p in queryset:
        sparta_profile_data = SpartaProfileSerializer(p).data
        # sparta_profile_data['username'] = p.user.username
        # sparta_profile_data['email'] = p.user.email
        try:
            esp = p.user.extended_sparta_profile
        except:
            ext_sparta_prof_data = {}
        else:
            ext_sparta_prof_data = ExtendedSpartaProfileSerializer(esp).data
        merge(sparta_profile_data, ext_sparta_prof_data)
        result_data.append(sparta_profile_data)

    data = {
        "count": queryset.count(),
        "results": result_data
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def sparta_profiles_detail(request, id, format=None):
    """
    /sparta/api/v1/profiles/:id
    """
    try:
        authenticate_request(request)
    except UnauthorizedError as e:
        data = {"error": "unauthorized",
                "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    try:
        sparta_profile = SpartaProfile.objects.get(id=id)
    except SpartaProfile.DoesNotExist:
        msg = "SpartaProfile with id {} not found.".format(id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)

    try:
        esp = p.user.extended_sparta_profile
    except:
        ext_sparta_prof_data = {}
    else:
        ext_sparta_prof_data = ExtendedSpartaProfileSerializer(esp).data
    sparta_profile_data = SpartaProfileSerializer(sparta_profile).data
    merge(sparta_profile_data, ext_sparta_prof_data)
    return Response(sparta_profile_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def education_credentials_list(request, id, format=None):
    """
    /sparta/api/v1/profiles/:id/educationcredentials
    """
    try:
        authenticate_request(request)
    except UnauthorizedError as e:
        data = {"error": "unauthorized",
                "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    try:
        sparta_profile = SpartaProfile.objects.get(id=id)
    except SpartaProfile.DoesNotExist:
        msg = "SpartaProfile with id {} not found.".format(id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)

    queryset = sparta_profile.education_profiles.all()

    offset = request.query_params.get('offset', None)
    if offset is not None and offset != '':
        of = int(offset)
        queryset = queryset[of:]
    limit = request.query_params.get('limit', None)
    if limit is not None and limit != '':
        lim = int(limit)
        queryset = queryset[:lim]

    data = {
        "count": queryset.count(),
        "results": EducationProfileSerializer(queryset, many=True).data
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def education_credentials_detail(request, id, format=None):
    """
    /sparta/api/v1/educationcredentials/:id
    """
    try:
        authenticate_request(request)
    except UnauthorizedError as e:
        data = {"error": "unauthorized",
                "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    try:
        e = EducationProfile.objects.get(id=id)
    except EducationProfile.DoesNotExist:
        msg = "EducationProfile with id {} not found.".format(id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)

    data = EducationProfileSerializer(e).data
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def employment_credentials_list(request, id, format=None):
    """
    /sparta/api/v1/profiles/:id/employmentcredentials
    """
    try:
        authenticate_request(request)
    except UnauthorizedError as e:
        data = {"error": "unauthorized",
                "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    try:
        sparta_profile = SpartaProfile.objects.get(id=id)
    except SpartaProfile.DoesNotExist:
        msg = "SpartaProfile with id {} not found.".format(id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)

    queryset = sparta_profile.employment_profiles.all()

    offset = request.query_params.get('offset', None)
    if offset is not None and offset != '':
        of = int(offset)
        queryset = queryset[of:]
    limit = request.query_params.get('limit', None)
    if limit is not None and limit != '':
        lim = int(limit)
        queryset = queryset[:lim]

    data = {
        "count": queryset.count(),
        "results": EmploymentProfileSerializer(queryset, many=True).data
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def employment_credentials_detail(request, id, format=None):
    """
    /sparta/api/v1/employmentcredentials/:id
    """
    try:
        authenticate_request(request)
    except UnauthorizedError as e:
        data = {"error": "unauthorized",
                "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    try:
        e = EmploymentProfile.objects.get(id=id)
    except EmploymentProfile.DoesNotExist:
        msg = "EmploymentProfile with id {} not found.".format(id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)

    data = EmploymentProfileSerializer(e).data
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def pathway_application_list(request, format=None):
    """
    /sparta/api/v1/pathwayapplications
    """
    try:
        authenticate_request(request)
    except UnauthorizedError as e:
        data = {"error": "unauthorized",
                "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    queryset = PathwayApplication.objects.all()

    offset = request.query_params.get('offset', None)
    if offset is not None and offset != '':
        of = int(offset)
        queryset = queryset[of:]
    limit = request.query_params.get('limit', None)
    if limit is not None and limit != '':
        lim = int(limit)
        queryset = queryset[:lim]

    data = {
        "count": queryset.count(),
        "results": PathwayApplicationSerializer(queryset, many=True).data
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def pathway_application_detail(request, id, format=None):
    try:
        authenticate_request(request)
    except UnauthorizedError as e:
        data = {"error": "unauthorized",
                "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    try:
        pa = PathwayApplication.objects.get(id=id)
    except PathwayApplication.DoesNotExist:
        msg = "PathwayApplication with id {} not found.".format(id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)

    data = PathwayApplicationSerializer(pa).data
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def profile_pathway_application_detail(request, id, format=None):
    try:
        authenticate_request(request)
    except UnauthorizedError as e:
        data = {"error": "unauthorized",
                "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    try:
        sparta_profile = SpartaProfile.objects.get(id=id)
    except SpartaProfile.DoesNotExist:
        msg = "SpartaProfile with id {} not found.".format(id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)

    applications = sparta_profile.applications.filter(status="AP")

    if not applications.exists():
        msg = "No approved PathwayApplications for profile id {} found.".format(id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)

    app = applications.order_by('-created_at')[0]
    data = PathwayApplicationSerializer(app).data
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def grade_list(request, course_id, format=None):
    authenticate_request(request)
    data = {}
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def user_grade_detail(request, profile_id, course_id, format=None):
    try:
        authenticate_request(request)
    except UnauthorizedError as e:
        data = {"error": "unauthorized",
                "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    try:
        sparta_profile = SpartaProfile.objects.get(id=profile_id)
    except SpartaProfile.DoesNotExist:
        msg = "SpartaProfile with id {} not found.".format(profile_id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)
    else:
        user = sparta_profile.user

    try:
        course_key = CourseKey.from_string(course_id)
    except Exception as e:
        msg = str(e)
        err_data = {"error": "course_key_error", "message": msg}
        return Response(err_data, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        enrollment = CourseEnrollment.objects.get(
            user=user,
            course_id=course_key
        )
    except CourseEnrollment.DoesNotExist:
        grade = CourseGradeFactory().read(user, course_key=course_key)
        sections_list = []
        for section in grade.summary[u'section_breakdown']:
            sections_list.append({
                "label": section['label'].encode('utf-8') if six.PY2 else section['label'],
                "percent": "N/A"
            })
        data = {
            "profile_id": profile_id,
            "course_id": course_id,
            "grade": "N/A",
            "sections": sections_list
        }
    else:
        grade = CourseGradeFactory().read(user, course_key=course_key)
        sections_list = []
        for section in grade.summary[u'section_breakdown']:
            sections_list.append({
                "label": section['label'].encode('utf-8') if six.PY2 else section['label'],
                "percent": section.get('percent', "N/A")
            })
        data = {
            "profile_id": profile_id,
            "course_id": course_id,
            "grade": grade.summary.get('percent', "N/A"),
            "sections": sections_list
        }
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def course_list(request, format=None):
    try:
        authenticate_request(request)
    except UnauthorizedError as e:
        data = {"error": "unauthorized",
                "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    queryset = SpartaCourse.objects.all()

    course_id = request.query_params.get('course_id', None)
    pathway = request.query_params.get('pathway', None)

    if course_id is not None:
        queryset = queryset.filter(course_id__icontains=course_id)
    if pathway is not None:
        queryset = queryset.filter(pathway__name__icontains=pathway)

    offset = request.query_params.get('offset', None)
    if offset is not None and offset != '':
        of = int(offset)
        queryset = queryset[of:]
    limit = request.query_params.get('limit', None)
    if limit is not None and limit != '':
        lim = int(limit)
        queryset = queryset[:lim]

    data = SpartaCourseSerializer(queryset, many=True).data
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def pathway_list(request, format=None):
    try:
        authenticate_request(request)
    except UnauthorizedError as e:
        data = {"error": "unauthorized",
                "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    queryset = Pathway.objects.all()

    offset = request.query_params.get('offset', None)
    if offset is not None and offset != '':
        of = int(offset)
        queryset = queryset[of:]
    limit = request.query_params.get('limit', None)
    if limit is not None and limit != '':
        lim = int(limit)
        queryset = queryset[:lim]

    data = PathwaySerializer(queryset, many=True).data
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
def sparta_student_module_timestamps(request, profile_id, course_id, format=None):
    """
    /sparta/api/v1/profiles/:id/courses/:id/timestamps
    """
    try:
        authenticate_request(request)
    except UnauthorizedError as e:
        data = {"error": "unauthorized",
                "error_description": "Request unauthorized: {}".format(str(e))}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    try:
        sparta_profile = SpartaProfile.objects.get(id=profile_id)
    except SpartaProfile.DoesNotExist:
        msg = "SpartaProfile with id {} not found.".format(profile_id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)
    else:
        user = sparta_profile.user

    try:
        course_key = CourseKey.from_string(course_id)
    except Exception as e:
        msg = str(e)
        err_data = {"error": "course_key_error", "message": msg}
        return Response(err_data, status=status.HTTP_400_BAD_REQUEST)

    try:
        enrollment = CourseEnrollment.objects.get(
            user=user,
            course_id=course_key
        )
    except CourseEnrollment.DoesNotExist:
        msg = "CourseEnrollment for SpartaProfile with id {} not found.".format(profile_id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)

    student_modules = StudentModule.objects.filter(
        course_id=course_key, student=user)

    course_module = student_modules.filter(module_type='course').order_by('created').first()
    if course_module:
        earliest_created = course_module.created.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    else:
        earliest_created = None

    latest_student_module = student_modules.order_by('-modified').first()
    if latest_student_module:
        latest_modified = latest_student_module.modified.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    else:
        latest_modified = None

    cert = get_certificate_for_user(user.username, course_key)
    if cert is not None and cert['status'] == "downloadable":
        date_completed = cert['created'].strftime('%Y-%m-%dT%H:%M:%S.000Z')
    else:
        date_completed = None

    data = {
        "earliest_created": earliest_created,
        "latest_modified": latest_modified,
        "date_completed": date_completed
    }
    return Response(data, status=status.HTTP_200_OK)
