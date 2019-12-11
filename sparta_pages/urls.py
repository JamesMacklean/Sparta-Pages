from django.conf import settings
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^sparta/$', views.main, name='sparta-main'),
    url(r'^sparta/register/$', views.registration_page, name='sparta-main'),
    url(r'^sparta/(?P<slug>[-\w]+)/$', views.pathway, name='sparta-pathway'),
]
