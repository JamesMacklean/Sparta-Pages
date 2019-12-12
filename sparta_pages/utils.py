from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment

from .models import Pathway, SpartaCourse, SpartaProfile, EducationProfile, EmploymentProfile, TrainingProfile, PathwayApplication, Event


def manage_pathway_applications():
    """"""
    for app in PathwayApplication.objects.filter(status="PE"):
        app.approve()

        user_enrollments = CourseEnrollment.objects.enrollments_for_user(app.profile.user)
        try:
            course_enrollment = user_enrollments.get(course_id=course_key, mode='verified')
        except CourseEnrollment.DoesNotExist:
            pass
