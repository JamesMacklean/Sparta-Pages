from django.conf import settings
from django.conf.urls import url
from django.views.generic import TemplateView

from . import api
from . import views

urlpatterns = [
    url(r'^$', views.main, name='sparta-main'),
    url(r'^/tos/$', TemplateView.as_view(template_name="sparta_tos.html"), name='sparta-tos'),

    url(r'^/register/$', views.RegistrationPageView.as_view(), name='sparta-register'),
    url(r'^/register/education/$', views.RegisterEducationProfileView.as_view(), name='sparta-register-education'),
    url(r'^/register/employment/$', views.RegisterEmploymentProfileView.as_view(), name='sparta-register-employment'),
    url(r'^/register/training/$', views.RegisterTrainingProfileView.as_view(), name='sparta-register-training'),
    url(r'^/register/success/$', views.register_success_page, name='sparta-register-success'),
    url(r'^/profile/$', views.ProfilePageView.as_view(), name='sparta-profile'),

    url(r'^/profile/education/new/$', views.EducationProfileCreateView.as_view(), name='sparta-education-create'),
    url(r'^/profile/employment/new/$', views.EmploymentProfileCreateView.as_view(), name='sparta-employment-create'),
    url(r'^/profile/training/new/$', views.TrainingProfileCreateView.as_view(), name='sparta-training-create'),
    url(r'^/profile/education/(?P<pk>\d+)/$', views.EducationProfileUpdateView.as_view(), name='sparta-education-update'),
    url(r'^/profile/employment/(?P<pk>\d+)/$', views.EmploymentProfileUpdateView.as_view(), name='sparta-employment-update'),
    url(r'^/profile/training/(?P<pk>\d+)/$', views.TrainingProfileUpdateView.as_view(), name='sparta-training-update'),
    url(r'^/profile/education/(?P<pk>\d+)/delete/$', views.delete_education_profile, name='sparta-education-delete'),
    url(r'^/profile/employment/(?P<pk>\d+)/delete/$', views.delete_employment_profile, name='sparta-employment-delete'),
    url(r'^/profile/training/(?P<pk>\d+)/delete/$', views.delete_training_profile, name='sparta-training-delete'),

    url(r'^/application-page/$', views.PathwayApplicationView.as_view(), name='sparta-application-page'),
    url(r'^/apply/(?P<id>\d+)/$', views.apply, name='sparta-apply'),
    url(r'^/pathway/(?P<slug>[-\w]+)/$', views.pathway, name='sparta-pathway'),
    url(r'^/pathway/(?P<pathway_id>\d+)/progress/$', views.PathwayProgressView.as_view(), name='sparta-pathway-progress'),
    url(r'^/widthraw/(?P<id>\d+)/$', views.widthraw, name='sparta-withdraw'),
    url(r'^/pathway/(?P<pathway_id>\d+)/coupons/$', views.StudentCouponRecordsView.as_view(), name='sparta-pathway-coupons'),

    url(r'^/admin-view/main/$', views.admin_main_view, name='sparta-admin-main'),
    url(r'^/admin-view/profiles/$', views.admin_profiles_view, name='sparta-admin-profiles'),
    url(r'^/admin-view/profiles/(?P<id>\d+)/credentials/$', views.admin_credentials_view, name='sparta-admin-credentials'),
    url(r'^/admin-view/applications/$', views.admin_applications_view, name='sparta-admin-applications'),
    url(r'^/admin-view/applications/approve/(?P<id>\d+)/$', views.admin_approve_application_view, name='sparta-admin-approve'),

    url(r'^/dev/profile/$', views.DeveloperProfileView.as_view(), name='sparta-developer-profile'),
    url(r'^/api/v0/pathways/$', api.pathway_list_view, name='sparta-api-pathway-list'),
    url(r'^/api/v0/pathways/(?P<id>\d+)/$', api.pathway_detail_view, name='sparta-api-pathway-detail'),
    url(r'^/api/v0/courses/$', api.course_list_view, name='sparta-api-course-list'),
    url(r'^/api/v0/courses/(?P<id>\d+)/$', api.course_detail_view, name='sparta-api-course-detail'),
    url(r'^/api/v0/students/$', api.student_list_view, name='sparta-api-student-list'),
    url(r'^/api/v0/students/(?P<id>\d+)/$', api.student_detail_view, name='sparta-api-student-detail'),

    url(r'^/api/v0/schema/$', api.schema_view, name='sparta-schema'),
    url(r'^/api/v0/redoc/$', api.RedocView.as_view(), name='sparta-redoc'),
]
