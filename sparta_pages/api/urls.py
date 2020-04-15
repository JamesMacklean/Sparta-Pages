from django.conf.urls import url

from .import api

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
]
