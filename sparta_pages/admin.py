from django.contrib import admin
from .models import Pathway, SpartaCourse, SpartaProfile, PathwayApplication, EducationProfile, EmploymentProfile, TrainingProfile, Event


@admin.register(Pathway)
class PathwayAdmin(admin.ModelAdmin):
    pass


@admin.register(SpartaCourse)
class SpartaCourseAdmin(admin.ModelAdmin):
    list_display = ('pathway', 'course_id')
    list_filter = ('pathway',)
    search_fields = ['pathway__name', 'course_id']


@admin.register(SpartaProfile)
class SpartaProfileAdmin(admin.ModelAdmin):
    search_fields = ['user__username', 'user__email']


@admin.register(PathwayApplication)
class PathwayApplicationAdmin(admin.ModelAdmin):
    list_display = ('profile', 'pathway', 'status')
    list_filter = ('pathway', 'status', 'created_at')
    search_fields = ['pathway__name', 'profile__user__username', 'profile__user__email']
    readonly_fields = ('created_at',)

@admin.register(EducationProfile)
class EducationProfileAdmin(admin.ModelAdmin):
    list_display = ('profile', 'course')
    search_fields = ['profile__user__username', 'profile__user__email', 'degree', 'course', 'school', 'address']


@admin.register(EmploymentProfile)
class EmploymentProfileAdmin(admin.ModelAdmin):
    list_display = ('profile', 'occupation')
    search_fields = [
        'profile__user__username', 'profile__user__email',
        'affiliation', 'occupation', 'designation', 'employer', 'address'
    ]


@admin.register(TrainingProfile)
class TrainingProfileAdmin(admin.ModelAdmin):
    list_display = ('profile', 'title')
    search_fields = ['profile__user__username', 'profile__user__email', 'title', 'organizer', 'address']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('profile', 'event')
    search_fields = ['profile__user__username', 'profile__user__email', 'event', 'description']
