from django.conf import settings
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^sparta/$', views.main, name='sparta-main'),
    url(r'^sparta/(?P<pathway_name>[a-zA-Z\d-]+)/$', views.pathway, name='sparta-pathway'),
]
