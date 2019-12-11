from django.contrib import admin
from .models import Pathway, SpartaCourse, SpartaProfile, PathwayApplication, EducationProfile, EmploymentProfile, TrainingProfile, Event

admin.site.register(Pathway)
admin.site.register(SpartaCourse)
admin.site.register(SpartaProfile)
admin.site.register(PathwayApplication)
admin.site.register(EducationProfile)
admin.site.register(EmploymentProfile)
admin.site.register(TrainingProfile)
admin.site.register(Event)
