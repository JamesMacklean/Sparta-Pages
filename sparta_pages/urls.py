from django.conf import settings
from django.conf.urls import url
from django.views.generic import TemplateView

from . import api
from .views import views, admin_views

urlpatterns = [
    url(r'^sparta$', views.main, name='sparta-main'),
    url(r'^sparta/tos$', TemplateView.as_view(template_name="sparta_tos.html"), name='sparta-tos'),

    url(r'^sparta/register$', views.RegistrationPageView.as_view(), name='sparta-register'),
    url(r'^sparta/register/next$', views.ExtendedRegistrationPageView.as_view(), name='sparta-register-extended'),
    url(r'^sparta/register/education$', views.RegisterEducationProfileView.as_view(), name='sparta-register-education'),
    url(r'^sparta/register/employment$', views.RegisterEmploymentProfileView.as_view(), name='sparta-register-employment'),
    url(r'^sparta/register/training$', views.RegisterTrainingProfileView.as_view(), name='sparta-register-training'),
    url(r'^sparta/register/success$', views.register_success_page, name='sparta-register-success'),
    url(r'^sparta/profile$', views.ProfilePageView.as_view(), name='sparta-profile'),

    url(r'^sparta/profile/info/new$', views.ExtendedRegistrationCreateView.as_view(), name='sparta-extended-profile-create'),
    url(r'^sparta/profile/education/new$', views.EducationProfileCreateView.as_view(), name='sparta-education-create'),
    url(r'^sparta/profile/employment/new$', views.EmploymentProfileCreateView.as_view(), name='sparta-employment-create'),
    url(r'^sparta/profile/training/new$', views.TrainingProfileCreateView.as_view(), name='sparta-training-create'),
    url(r'^sparta/profile/info/(?P<pk>\d+)$', views.ExtendedSpartaProfileUpdateView.as_view(), name='sparta-extended-profile-update'),
    url(r'^sparta/profile/education/(?P<pk>\d+)$', views.EducationProfileUpdateView.as_view(), name='sparta-education-update'),
    url(r'^sparta/profile/employment/(?P<pk>\d+)$', views.EmploymentProfileUpdateView.as_view(), name='sparta-employment-update'),
    url(r'^sparta/profile/training/(?P<pk>\d+)$', views.TrainingProfileUpdateView.as_view(), name='sparta-training-update'),
    url(r'^sparta/profile/education/(?P<pk>\d+)/delete$', views.delete_education_profile, name='sparta-education-delete'),
    url(r'^sparta/profile/employment/(?P<pk>\d+)/delete$', views.delete_employment_profile, name='sparta-employment-delete'),
    url(r'^sparta/profile/training/(?P<pk>\d+)/delete$', views.delete_training_profile, name='sparta-training-delete'),

    url(r'^sparta/application-page$', views.PathwayApplicationView.as_view(), name='sparta-application-page'),
    url(r'^sparta/apply/(?P<id>\d+)$', views.apply, name='sparta-apply'),
    url(r'^sparta/pathway/(?P<slug>[-\w]+)$', views.pathway, name='sparta-pathway'),
    url(r'^sparta/pathway/(?P<pathway_id>\d+)/progress$', views.PathwayProgressView.as_view(), name='sparta-pathway-progress'),
    url(r'^sparta/widthraw/(?P<id>\d+)$', views.widthraw, name='sparta-withdraw'),
    url(r'^sparta/pathway/(?P<pathway_id>\d+)/coupons$', views.StudentCouponRecordsView.as_view(), name='sparta-pathway-coupons'),

    url(r'^sparta/admin-view/main$', admin_views.admin_main_view, name='sparta-admin-main'),
    url(r'^sparta/admin-view/profiles$', admin_views.admin_profiles_view, name='sparta-admin-profiles'),
    url(r'^sparta/admin-view/profiles/(?P<id>\d+)/credentials$', admin_views.admin_credentials_view, name='sparta-admin-credentials'),
    url(r'^sparta/admin-view/applications$', admin_views.admin_applications_view, name='sparta-admin-applications'),
    url(r'^sparta/admin-view/applications/approve/(?P<id>\d+)$', admin_views.admin_approve_application_view, name='sparta-admin-approve'),
    url(r'^sparta/admin-view/analytics/overall$', admin_views.admin_overall_analytics_view, name='sparta-admin-overall-analytics'),
    url(r'^sparta/admin-view/analytics/pathways/(?P<slug>[-\w]+)$', admin_views.admin_pathway_analytics_view, name='sparta-admin-pathway-analytics'),
    url(r'^sparta/admin-view/analytics/courses/(?P<course_id>[-:+\w]+)$', admin_views.admin_course_analytics_view, name='sparta-admin-course-analytics'),

    url(r'^sparta/admin/dashboard/main$', admin_views.data_dashboard_main_view, name='sparta-data-dashboard-main'),
    url(r'^sparta/admin/dashboard/profiles$', admin_views.data_dashboard_profiles_view, name='sparta-data-dashboard-profiles'),
    url(r'^sparta/admin/dashboard/education/credentials$', admin_views.data_dashboard_education_credentials_view, name='sparta-data-dashboard-education-credentials'),
    url(r'^sparta/admin/dashboard/employment/credentials$', admin_views.data_dashboard_employment_credentials_view, name='sparta-data-dashboard-employment-credentials'),
    url(r'^sparta/admin/dashboard/training/credentials$', admin_views.data_dashboard_training_credentials_view, name='sparta-data-dashboard-training-credentials'),
    url(r'^sparta/admin/dashboard/courses$', admin_views.data_dashboard_courses_view, name='sparta-data-dashboard-courses'),

    url(r'^sparta/dev/profile$', admin_views.DeveloperProfileView.as_view(), name='sparta-developer-profile'),
    url(r'^sparta/api/v0/pathways$', api.pathway_list_view, name='sparta-api-pathway-list'),
    url(r'^sparta/api/v0/pathways/(?P<id>\d+)$', api.pathway_detail_view, name='sparta-api-pathway-detail'),
    url(r'^sparta/api/v0/courses$', api.course_list_view, name='sparta-api-course-list'),
    url(r'^sparta/api/v0/courses/(?P<id>\d+)$', api.course_detail_view, name='sparta-api-course-detail'),
    url(r'^sparta/api/v0/students$', api.student_list_view, name='sparta-api-student-list'),
    url(r'^sparta/api/v0/students/(?P<id>\d+)$', api.student_detail_view, name='sparta-api-student-detail'),

    url(r'^sparta/api/v0/schema$', api.schema_view, name='sparta-schema'),
    url(r'^sparta/api/v0/redoc$', api.RedocView.as_view(), name='sparta-redoc'),
]
