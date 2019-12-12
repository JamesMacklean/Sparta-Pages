from django.conf import settings
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^sparta/$', views.main, name='sparta-main'),
    url(r'^sparta/register/$', views.RegistrationPageView.as_view(), name='sparta-register'),
    url(r'^sparta/upload/params/$', views.get_upload_params, name='sparta-upload-params'),
    url(r'^sparta/(?P<slug>[-\w]+)/$', views.pathway, name='sparta-pathway'),
]
