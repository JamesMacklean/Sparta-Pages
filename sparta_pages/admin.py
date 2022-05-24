from django.contrib import admin
from .models import (
    MicroPathwayApplication, Pathway, SpartaCourse, CourseGroup, SpartaEnrollment,
    SpartaProfile, PathwayApplication, ExtendedSpartaProfile,
    EducationProfile, EmploymentProfile, TrainingProfile,
    Event, APIToken,
    SpartaCoupon, StudentCouponRecord,
    SpartaReEnrollment,MicroPathway
)

@admin.register(Pathway)
class PathwayAdmin(admin.ModelAdmin):
    pass


@admin.register(SpartaCourse)
class SpartaCourseAdmin(admin.ModelAdmin):
    list_display = ('pathway', 'course_id')
    list_filter = ('pathway',)
    search_fields = ['pathway__name', 'course_id']


@admin.register(CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'pathway', 'type')
    list_filter = ('pathway', 'type')
    search_fields = ['name', 'pathway__name',]


@admin.register(SpartaProfile)
class SpartaProfileAdmin(admin.ModelAdmin):
    search_fields = ['user__username', 'user__email']


@admin.register(ExtendedSpartaProfile)
class ExtendedSpartaProfileAdmin(admin.ModelAdmin):
    search_fields = ['user__username', 'user__email']


@admin.register(PathwayApplication)
class PathwayApplicationAdmin(admin.ModelAdmin):
    list_display = ('profile', 'pathway', 'status')
    list_filter = ('pathway', 'status', 'created_at')
    search_fields = ['pathway__name', 'profile__user__username', 'profile__user__email']
    readonly_fields = ('created_at',)

@admin.register(MicroPathwayApplication)
class MicroPathwayApplicationAdmin(admin.ModelAdmin):
    list_display = ('profile', 'micropathway', 'status')
    list_filter = ('micropathway', 'status', 'created_at')
    search_fields = ['micropathway__name', 'profile__user__username', 'profile__user__email']
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


@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'is_active')
    search_fields = ['user__username', 'user__email', 'key']


@admin.register(SpartaCoupon)
class SpartaCouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'course_id',)
    search_fields = ['code', 'course_id',]


@admin.register(StudentCouponRecord)
class StudentCouponRecordAdmin(admin.ModelAdmin):
    list_display = ('profile', 'coupon',)
    search_fields = ['profile__user__email', 'profile__user__username', 'coupon__course_id', 'coupon__code']
    readonly_fields = ('profile', 'coupon', 'created', 'modified')

@admin.register(SpartaReEnrollment)
class SpartaReEnrollmentAdmin(admin.ModelAdmin):
    readonly_fields = ('enrollment', 'reenroll_date')
@admin.register(SpartaEnrollment)
class SpartaEnrollmentAdmin(admin.ModelAdmin):
    readonly_fields = ('enrollment', 'enroll_date')

@admin.register(MicroPathway)
class MicroPathwayAdmin(admin.ModelAdmin):
    pass