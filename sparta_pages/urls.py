from django.conf import settings
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^sparta/$', views.main, name='sparta-main'),
    url(r'^sparta/(?P<slug>[-\w]+)/$', views.pathway, name='sparta-pathway'),
    url(r'^sparta/upload/params/$', views.get_upload_params, name='sparta-upload-params'),
    url(r'^sparta/register/demo/$', views.demo_registration_page, name='sparta-register-demo'),
    url(r'^sparta/register/$', views.registration_page, name='sparta-register'),
    url(r'^sparta/register/success/$', views.registration_page, name='sparta-register-success'),
]
