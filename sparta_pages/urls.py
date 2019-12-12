from django.conf import settings
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^sparta/$', views.main, name='sparta-main'),
    url(r'^sparta/register/$', views.RegistrationPageView.as_view(), name='sparta-register'),
    url(r'^sparta/register/success/$', views.register_success_page, name='sparta-register-success'),
    url(r'^sparta/profile/$', views.ProfilePageView.as_view(), name='sparta-profile'),
    url(r'^sparta/apply/$', views.PathwayApplicationView.as_view(), name='sparta-apply'),
    url(r'^sparta/pathway/(?P<slug>[-\w]+)/$', views.pathway, name='sparta-pathway'),
    url(r'^sparta/pathway/(?P<pathway_id>\d+)/progress/$', views.PathwayProgressView.as_view(), name='sparta-pathway-progress'),
    url(r'^sparta/widthraw/(?P<id>\d+)/$', views.widthraw, name='sparta-withdraw'),
]
