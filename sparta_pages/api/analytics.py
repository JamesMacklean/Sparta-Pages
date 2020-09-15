import six

from django.contrib.auth import get_user_model
User = get_user_model()

from courseware.models import StudentModule
from lms.djangoapps.certificates.models import certificate_status_for_student
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment

from rest_framework import status, renderers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import (
    SpartaProfileSerializer, ExtendedSpartaProfileSerializer,
    EmploymentProfileSerializer, EducationProfileSerializer,
    PathwayApplicationSerializer
)
from ..models import (
    Pathway, SpartaCourse, SpartaProfile, PathwayApplication,
    EducationProfile, EmploymentProfile
)


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
        token_key = token_decoded.strip(':')
        if token_key != SECRET_TOKEN:
            return False
        return True
    
    def authenticate(self, request):
        try:
            auth = basic_auth(request)
        except Exception as e:
            data = {"error": "unauthorized",
                    "error_description": "Request unauthorized: {}".format(str(e))}
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        if not auth:
            data = {"error": "unauthorized",
                    "error_description": "Request unauthorized"}
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)

authenticate_request = CustomAuth().authenticate

def merge(d1, d2):
    return (d2.update(d1))

@api_view(['GET'])
def sparta_profiles_list(request, format=None):
    """
    /sparta/api/v1/profiles/
    """
    authenticate_request(request)

    queryset = SpartaProfile.objects.all()

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
        try:
            esp = p.user.extended_sparta_profile
        except:
            esp = {}
        else:
            ext_sparta_prof_data = ExtendedSpartaProfileSerializer(esp).data
        merge(sparta_profile_data, ext_sparta_prof_data)
        result_data.append(ext_sparta_prof_data)

    data = {
        "count": queryset.count(),
        "results": result_data
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def sparta_profiles_detail(request, id, format=None):
    """
    /sparta/api/v1/profiles/:id
    """
    authenticate_request(request)

    try:
        sparta_profile = SpartaProfile.objects.all()
    except SpartaProfile.DoesNotExist:
        msg = "SpartaProfile with id {} not found.".format(id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)

    data = SpartaProfileSerializer(sparta_profile).data
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def education_credentials_list(request, id, format=None):
    """
    /sparta/api/v1/profiles/:id/educationcredentials
    """
    authenticate_request(request)

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
def education_credentials_detail(request, id, format=None):
    """
    /sparta/api/v1/educationcredentials/:id
    """
    authenticate_request(request)

    try:
        e = EducationProfile.objects.get(id=id)
    except EducationProfile.DoesNotExist:
        msg = "EducationProfile with id {} not found.".format(id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)

    data = EducationProfileSerializer(e).data
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def employment_credentials_list(request, id, format=None):
    """
    /sparta/api/v1/profiles/:id/employmentcredentials
    """
    authenticate_request(request)
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
def employment_credentials_detail(request, id, format=None):
    """
    /sparta/api/v1/employmentcredentials/:id
    """
    authenticate_request(request)
    try:
        e = EmploymentProfile.objects.get(id=id)
    except EmploymentProfile.DoesNotExist:
        msg = "EmploymentProfile with id {} not found.".format(id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)

    data = EmploymentProfileSerializer(e).data
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def pathway_application_list(request, format=None):
    """
    /sparta/api/v1/pathwayapplications
    """
    authenticate_request(request)

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
def pathway_application_detail(request, id, format=None):
    authenticate_request(request)

    try:
        pa = PathwayApplication.objects.get(id=id)
    except PathwayApplication.DoesNotExist:
        msg = "PathwayApplication with id {} not found.".format(id)
        err_data = {"error": "not_found", "message": msg}
        return Response(err_data, status=status.HTTP_404_NOT_FOUND)

    data = PathwayApplicationSerializer(pa).data
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def grade_list(request, course_id, format=None):
    authenticate_request(request)
    data = {}
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def user_grade_detail(request, profile_id, course_id, format=None):
    authenticate_request(request)

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

    grade = CourseGradeFactory().read(user, course_key)

    sections_list = []
    for section in grade.summary[u'section_breakdown']:
        sections_list.append({
            "label": section['label'].encode('utf-8') if six.PY2 else section['label'],
            "percent": section.get('percent', 0.0)
        })

    data = {
        "profile_id": profile_id,
        "course_id": course_id,
        "grade": grade.summary.percent,
        "sections": sections_list
    }
    return Response(data, status=status.HTTP_200_OK)
