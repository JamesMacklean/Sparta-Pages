from django.conf import settings
from django.conf.urls import url

from .import api, analytics

urlpatterns = [
    url(r'^sparta/api/v0/pathways$', api.pathway_list_view, name='sparta-api-pathway-list'),
    url(r'^sparta/api/v0/pathways/(?P<id>\d+)$', api.pathway_detail_view, name='sparta-api-pathway-detail'),
    url(r'^sparta/api/v0/courses$', api.course_list_view, name='sparta-api-course-list'),
    url(r'^sparta/api/v0/courses/(?P<id>\d+)$', api.course_detail_view, name='sparta-api-course-detail'),
    url(r'^sparta/api/v0/students$', api.student_list_view, name='sparta-api-student-list'),
    url(r'^sparta/api/v0/students/(?P<id>\d+)$', api.student_detail_view, name='sparta-api-student-detail'),

    url(r'^sparta/api/v0/schema$', api.schema_view, name='sparta-schema'),
    url(r'^sparta/api/v0/redoc$', api.RedocView.as_view(), name='sparta-redoc'),

    url(r'^sparta/api/v1/applicationscount$', api.pathway_applications_count_view, name='sparta-api-'),
    url(r'^sparta/api/v1/enrollmentscount$', api.enrollments_count_view, name='sparta-api-'),
    url(r'^sparta/api/v1/completionrates$', api.completion_rates_view, name='sparta-api-'),
    url(r'^sparta/api/v1/learneractivity$', api.learner_activity_view, name='sparta-api-'),
    url(r'^sparta/api/v1/agescount$', api.ages_count_view, name='sparta-api-'),
    url(r'^sparta/api/v1/gendercount$', api.gender_count_view, name='sparta-api-'),
    url(r'^sparta/api/v1/affiliationcount$', api.affiliation_count_view, name='sparta-api-'),
    url(r'^sparta/api/v1/attainmentcount$', api.attainment_count_view, name='sparta-api-'),
    url(r'^sparta/api/v1/locationcount$', api.location_count_view, name='sparta-api-'),

    url(r'^sparta/api/v1/profiles$', analytics.sparta_profiles_list,
        name='analytics-sparta-profile-list'),
    url(r'^sparta/api/v1/profiles/(?P<id>\d+)$', analytics.sparta_profiles_detail,
        name='analytics-sparta-profile-detail'),
    url(r'^sparta/api/v1/profiles/(?P<id>\d+)/educationcredentials$', analytics.education_credentials_list,
        name='analytics-sparta-education-profiles-list'),
    url(r'^sparta/api/v1/educationcredentials/(?P<id>\d+)$', analytics.education_credentials_detail,
        name='analytics-sparta-education-profiles-detail'),
    url(r'^sparta/api/v1/profile/(?P<id>\d+)/employmentcredentials$', analytics.employment_credentials_list,
        name='analytics-sparta-employment-profiles-list'),
    url(r'^sparta/api/v1/employmentcredentials/(?P<id>\d+)$',
        analytics.employment_credentials_detail, name='analytics-sparta-employment-profiles-detail'),
    url(r'^sparta/api/v1/pathwayapplications$', analytics.pathway_application_list,
        name='analytics-sparta-pathway-application-list'),
    url(r'^sparta/api/v1/pathwayapplications/(?P<id>\d+)$',
        analytics.pathway_application_detail, name='analytics-sparta-pathway-application-detail'),
    url(r'^sparta/api/v1/profiles/(?P<id>\d+)/pathwayapplication$',
        analytics.profile_pathway_application_detail, name='analytics-sparta-profile-pathway-application-detail'),
    url(r'^sparta/api/v1/profiles/(?P<profile_id>\d+)/course/{}/grades'.format(settings.COURSE_ID_PATTERN), analytics.user_grade_detail,
        name='analytics-sparta-user-grade-detail'),
    url(r'^sparta/api/v1/pathways$', analytics.pathway_list,
        name='analytics-sparta-pathway-list'),
    url(r'^sparta/api/v1/courses$', analytics.course_list,
        name='analytics-sparta-course-list'),
    url(r'^sparta/api/v1/profiles/(?P<profile_id>\d+)/course/{}/timestamps'.format(settings.COURSE_ID_PATTERN), analytics.sparta_student_module_timestamps,
        name='analytics-sparta-student-module-timestamps'),
]
