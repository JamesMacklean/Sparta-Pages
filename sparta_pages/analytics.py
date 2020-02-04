from decimal import Decimal

from django.utils import timezone

from courseware.models import StudentModule
from lms.djangoapps.certificates.models import certificate_status_for_student
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment

from .models import (
    Pathway, SpartaCourse, SpartaProfile, PathwayApplication,
    EducationProfile, EmploymentProfile, TrainingProfile,
)

def get_average_completion_rate(course_id):
    course_key = CourseKey.from_string(course_id)

    enrollments = CourseEnrollment.objects.filter(
        course_id=course_key,
        is_active=True,
        mode="verified"
    )
    modules = StudentModule.objects.filter(course_id=course_key)

    total_seconds_list = []
    for e in enrollments:
        user = e.user

        cert_status = certificate_status_for_student(user, course_key)
        if cert_status and cert_status['mode'] == 'verified' and cert_status['status'] not in  ['unavailable', 'notpassing', 'restricted', 'unverified']:
            pass
        else:
            continue

        student_modules = modules.filter(student=user)

        course_module = student_modules.filter(module_type='course').order_by('created').first()
        if course_module:
            started_course_at = course_module.created
        else:
            continue

        latest_student_module = student_modules.order_by('-modified').first()
        if latest_student_module:
            ended_course_at = latest_student_module.modified
        else:
            continue

        finish_duration = ended_course_at - started_course_at
        finish_duration_decimal = Decimal(finish_duration.total_seconds())
        total_seconds_list.append(finish_duration_decimal)

    if total_seconds_list:
        return str(sum(total_seconds_list) / len(total_seconds_list))
    else:
        return "unavailable"


def get_student_enrollment_status(student, course_key):
    cert_status = certificate_status_for_student(student.user, course_key)
    if cert_status and cert_status['mode'] == 'verified' and cert_status['status'] not in ['unavailable', 'notpassing', 'restricted', 'unverified']:
        return "completed"

    modules = StudentModule.objects.filter(course_id=course_key, student=student.user)
    if modules.exists():
        latest_student_module = modules.order_by('-modified').first()
        diff_time =  timezone.now() - latest_student_module.modified
        diff_time_secs = diff_time.total_seconds()
        xminute = 60
        xhour = xminute*60
        xday = xhour*24
        xweek = xday*7
        xmonth = xday*30.417
        xyear = xweek*52
        xthirtydays = xday*30
        xoneeightydays = xday*180
        if diff_time_secs <= xthirtydays:
            status = "active"
        elif diff_time_secs <= xoneeightydays:
            status = "inactive"
        else:
            status = "dropped_out"
        return status
    else:
        return "unenrolled"


def get_average_grade_percent(student, courses_enrolled_in):
    grades_list = []
    for course in courses_enrolled_in:
        course_key = CourseKey.from_string(course['course_id'])
        grade = CourseGradeFactory().read(student.user, course_key=course_key)
        grades_list.append(Decimal(grade.percent))
    if grades_list:
        return str(round(sum(grades_list) / len(grades_list), 4))
    else:
        return "unavailable"


def get_course_id_list():
    course_id_list = []
    for course in SpartaCourse.objects.filter(is_active=True):
        if course.course_id not in course_id_list:
            courses.append(course.course_id)
    return course_id_list


class LearnerManager:
    """
    Manager for handling 'querysets' of Learners
    """
    def __init__(self):
        self.queryset = None

    def queryset(self):
        return self.queryset

    def all(self):
        self.queryset = self._all()
        return self

    def _all(self):
        learners = []
        for profile in SpartaProfile.objects.filter(is_active=True):
            learners.append(Learner(profile=profile))
        return learners

    def pathway(self, pathway):
        self.queryset = self._pathway(pathway)
        return self

    def _pathway(self, pathway):
        if self.queryset is None:
            self.all()
        learners = []
        for learner in self.queryset:
            learners.append(Learner(profile=learner.profile, pathway=pathway))
        return learners

    def course(self, course):
        self.queryset = self._course(course)
        return self

    def _course(self, course):
        if self.queryset is None:
            self.all()
        learners = []
        for learner in self.queryset:
            learners.append(Learner(profile=learner.profile, course=course))
        return learners

    def filter(self, **kwargs):
        self.queryset = self._filter(**kwargs)
        return self

    def _filter(self, **kwargs):
        if self.queryset is None:
            self.all()
        queryset = self.queryset

        enrolled = self.kwargs.get('enrolled', None)
        enrolled_verified = self.kwargs.get('enrolled_verified', None)
        in_progress = self.kwargs.get('in_progress', None)
        active = self.kwargs.get('active', None)
        inactive = self.kwargs.get('inactive', None)
        dropped_out = self.kwargs.get('dropped_out', None)
        graduated = self.kwargs.get('graduated', None)

        if enrolled is not None:
            newset = []
            for learner in queryset:
                if learner.enrolled:
                    newset.append(learner)
            queryset = newset

        if enrolled_verified is not None:
            newset = []
            for learner in queryset:
                if learner.enrolled_verified:
                    newset.append(learner)
            queryset = newset

        if in_progress is not None:
            newset = []
            for learner in queryset:
                if learner.in_progress:
                    newset.append(learner)
            queryset = newset

        if active is not None:
            newset = []
            for learner in queryset:
                if learner.active:
                    newset.append(learner)
            queryset = newset

        if inactive is not None:
            newset = []
            for learner in queryset:
                if learner.inactive:
                    newset.append(learner)
            queryset = newset

        if dropped_out is not None:
            newset = []
            for learner in queryset:
                if learner.dropped_out:
                    newset.append(learner)
            queryset = newset

        if graduated is not None:
            newset = []
            for learner in queryset:
                if learner.graduated:
                    newset.append(learner)
            queryset = newset

        self.queryset = queryset

        return self.queryset

    def count(self):
        ctr = 0
        for l in self.queryset:
            ctr += 1
        return Decimal(ctr)


class Learner:
    """
    Class object for learner analytics

    Initialize by setting SpartaProfile of learner
    ex. Learner(SpartaProfile.objects.get(id=id))

    Optional pathway argument to filter learner info
    ex. Learner(profile, pathway=Pathway.objects.get(id=id))

    Optional course argument to filter learner info
    *Info will be filtered only by course_id of the SpartaCourse indicated
    ex. Learner(profile, course=SpartaCourse.objects.get(id=id))
    """
    xminute = 60
    xhour = xminute*60
    xday = xhour*24
    xweek = xday*7
    xmonth = xday*30.417
    xyear = xweek*52
    xthirtydays = xday*30
    xoneeightydays = xday*180
    timezone_now = timezone.now()

    def __init__(self, profile, pathway=None, course=None, *args, **kwargs):
        self.profile = profile
        self.pathway = pathway
        self.course = course

        self.user = profile.user
        self.extended_profile = self._extended_sparta_profile()

        self.enrollments = self._enrollments()
        self.verified_enrollments = self._verified_enrollments()
        self.applications = self._applications()
        self.approved_applications = self._approved_applications()
        self.current_courses = self._current_courses()

        self.enrolled = self._enrolled()
        self.enrolled_verified = self._enrolled_verified()
        self.in_progress = self._in_progress()
        self.active = self._active()
        self.inactive = self._inactive()
        self.dropped_out = self._dropped_out()
        self.graduated = self._graduated()
        self.completed_pathway = self._completed_pathway()
        self.completed_course = self._completed_course()

    def _extended_sparta_profile(self):
        try:
            p = self.user.extended_sparta_profile
        except:
            p = None
        return p

    def _enrollments(self):
        courses = SpartaCourse.objects.filter(is_active=True)
        if self.pathway is not None:
            courses = courses.filter(pathway=self.pathway)
        if self.course is not None:
            courses = courses.filter(course_id=self.course.course_id)
        enrollments = CourseEnrollment.objects.none()
        for c in courses:
            course_key = CourseKey.from_string(c.course_id)
            try:
                get_course = CourseOverview.get_from_id(course_key)
            except CourseOverview.DoesNotExist:
                continue
            else:
                enrollments |= CourseEnrollment.objects.filter(course=get_course)
        return enrollments

    def _verified_enrollments(self):
        enrollments = self.enrollments
        if enrollments:
            return enrollments.filter(mode="verified")
        else:
            return None

    def _applications(self):
        applications = self.profile.applications.all()
        if self.pathway is not None:
            applications = applications.filter(pathway=self.pathway)
        return applications

    def _approved_applications(self):
        return self.applications.filter(status='AP')

    def _current_courses(self):
        courses = SpartaCourse.objects.none()
        for app in self.approved_applications:
            course_set = app.courses.all().filter(is_active=True)
            if self.course is not None:
                course_set = course_set.filter(course_id=self.course.course_id)
            courses |= course_set
        return courses

    def _enrolled_verified(self):
        return self.verified_enrollments is not None

    def _enrolled(self):
        return self.enrollments is not None

    def _in_progress(self):
        """in-progress in at least one (1) course"""
        for course in self.current_courses:
            if StudentModule.objects.filter(course_id=CourseKey.from_string(course.course_id), student=self.user).exists():
                return True
        return False

    def _latest_modules(self):
        modules = StudentModule.objects.none()
        for course in self.current_courses:
            get_modules = StudentModule.objects.filter(course_id=CourseKey.from_string(course.course_id), student=self.user)
            if get_modules.exists():
                modules |= get_modules.order_by('-modified').first()
        return modules

    def _get_latest_module(self):
        modules = self._latest_modules()
        if modules:
            return modules[0]
        return None

    def _get_activity(active=False, inactive=False, dropped_out=False):
        module = self._get_latest_module()
        if module:
            diff_time =  timezone_now - module.modified
            diff_time_secs = diff_time.total_seconds()
            if active:
                return diff_time_secs <= xthirtydays
            elif inactive:
                return diff_time_secs > xthirtydays and diff_time_secs <= xoneeightydays
            elif dropped_out:
                return diff_time_secs > xoneeightydays
        return False

    def _active(self):
        """in-progress in at least one (1) course and whose last session is at most thirty (30) days ago"""
        return _self._get_activity(active=True)

    def _inactive(self):
        """in-progress in at least 1 course and whose last session is over 30 days ago but at most 180 days ago"""
        return _self._get_activity(inactive=True)

    def _dropped_out(self):
        """in-progress in at least 1 course and whose last session is over 180 days ago"""
        return _self._get_activity(dropped_out=True)

    def _graduated(self):
        """completed at least 1 pathway"""
        for app in self.applications:
            groups = app.pathway.groups.all().filter(is_active=True)
            groups_completed = CourseGroup.objects.none()
            for group in groups:
                group_courses = group.courses.all().filter(is_active=True)
                complete_at_least = group_courses.count() if group.type == 'CO' else group.complete_at_least
                group_courses = app.pathway.courses.all().filter(is_active=True)
                group_ctr = 0
                for course in group_courses:
                    course_key = CourseKey.from_string(course.course_id)
                    cert_status = certificate_status_for_student(self.user, course_key)
                    if cert_status and cert_status['mode'] == 'verified' and cert_status['status'] not in ['unavailable', 'notpassing', 'restricted', 'unverified']:
                        group_ctr += 1
                if group_courses and group_ctr == complete_at_least:
                    groups_completed |= group
            if groups.count() == groups_completed.count():
                return True
        return False

    def _completed_pathway(self, pathway=None):
        if pathway is None:
            pathway = self.pathway

        groups = self.pathway.groups.all().filter(is_active=True)
        groups_completed = CourseGroup.objects.none()
        for group in groups:
            group_courses = group.courses.all().filter(is_active=True)
            complete_at_least = group_courses.count() if group.type == 'CO' else group.complete_at_least
            group_courses = app.pathway.courses.all().filter(is_active=True)
            group_ctr = 0
            for course in group_courses:
                course_key = CourseKey.from_string(course.course_id)
                cert_status = certificate_status_for_student(self.user, course_key)
                if cert_status and cert_status['mode'] == 'verified' and cert_status['status'] not in ['unavailable', 'notpassing', 'restricted', 'unverified']:
                    group_ctr += 1
            if group_courses and group_ctr == complete_at_least:
                groups_completed |= group
        return groups.count() == groups_completed.count()

    def _completed_course(self, course=None):
        if course is None:
            course = self.course

        course_key = CourseKey.from_string(self.course.course_id)
        cert_status = certificate_status_for_student(self.user, course_key)
        return cert_status and cert_status['mode'] == 'verified' and cert_status['status'] not in ['unavailable', 'notpassing', 'restricted', 'unverified']

    manager = LearnerManager()


class OverallAnalytics:
    """
    Class helper for getting overall data
    """

    def __init__(self, *args, **kwargs):
        self.learners = Learner.manager.all()
        self.total = self.learners.count()

    def overall_no_of_enrollees(self):
        """
        Number of learners who enrolled as SPARTA scholars
        """
        return self.learners.filter(enrolled=True).count()

    def overall_no_of_learners_in_progress(self):
        """
        Number of enrolled learners who are in-progress in at least 1 course
        """
        return self.learners.filter(in_progress=True).count()

    def percent_of_learners_in_progress(self):
        """
        Percentage of enrollees who are in-progress in at least 1 course
        """
        return self.overall_no_of_learners_in_progress() / self.total

    def overall_no_of_active_learners(self):
        """
        Number of learners who are in-progress in at least 1 course and whose last session is at most 30 days ago
        """
        return self.learners.filter(active=True).count()

    def percent_of_active_learners(self):
        """
        Percentage of learners who are in-progress in at least 1 course and whose last session is at most 30 days ago
        """
        return self.overall_no_of_active_learners() / self.total

    def overall_no_of_inactive_learners(self):
        """
        Number of learners who are in-progress in at least 1 course and whose last session is over 30 days ago but at most 180 days ago
        """
        return self.learners.filter(inactive=True).count()

    def percent_of_inactive_learners(self):
        """
        Percentage of learners who are in-progress in at least 1 course and whose last session is over 30 days ago but at most 180 days ago
        """
        return self.overall_no_of_inactive_learners() / self.total

    def overall_no_of_dropped_out_learners(self):
        """
        Number of learners who are in-progress in at least 1 course and whose last session is over 180 days ago
        """
        return self.learners.filter(dropped_out=True).count()

    def overall_dropout_rate(self):
        """
        Percentage of learners who are in-progress in at least 1 course and whose last session is over 180 days ago
        """
        return self.overall_no_of_dropped_out_learners() / self.total

    def overall_no_of_graduates(self):
        """
        Number of learners who completed at least 1 pathway
        """
        return self.learners.filter(graduated=True).count()

    def overall_graduation_rate(self):
        """
        Percentage of learners completed at least 1 pathway
        """
        return self.overall_no_of_graduates() / self.total

    def overall_average_session_duration(self):
        """
        Total duration of all sessions divided by total number of sessions
        """

    def overall_course_units_session(self):
        """
        Average number of course units viewed during a session in the Coursebank Studio
        """


class PathwayAnalytics:
    """
    Initialize with pathway argument
    ex. PathwayAnalytics(pathway)
    """
    def __init__(self, pathway, *args, **kwargs):
        self.pathway = pathway
        self.learners = Learner.manager.pathway(pathway)
        self.total = self.learners.count()

    def no_of_pathway_enrollees(self):
        """
        Number of learners who enrolled as SPARTA scholars (pathway-level)
        """
        return self.learners.filter(enrolled=True).count()

    def no_of_pathway_learners_in_progress(self):
        """
        Number of enrolled learners who are in-progress in at least 1 course (pathway-level)
        """
        return self.learners.filter(in_progress=True).count()

    def percent_of_pathway_learners_in_progress(self):
        """
        Percentage of enrollees who are in-progress in at least 1 course (pathway-level)
        """
        return self.no_of_pathway_learners_in_progress() / self.total

    def no_of_active_pathway_learners(self):
        """
        Number of learners who are in-progress in at least 1 course and whose last session is at most 30 days ago (pathway-level)
        """
        return self.learners.filter(active=True).count()

    def percent_of_active_pathway_learners(self):
        """
        Percentage of learners who are in-progress in at least 1 course and whose last session is at most 30 days ago (pathway-level)
        """
        return self.no_of_active_pathway_learners() / self.total

    def no_of_inactive_pathway_learners(self):
        """
        Number of learners who are in-progress in at least 1 course and whose last session is over 30 days ago but at most 180 days ago (pathway-level)
        """
        return self.learners.filter(inactive=True).count()

    def percent_of_inactive_pathway_learners(self):
        """
        Percentage of learners who are in-progress in at least 1 course and whose last session is over 30 days ago but at most 180 days ago (pathway-level)
        """
        return self.no_of_inactive_pathway_learners() / self.total

    def no_of_dropped_out_pathway_learners(self):
        """
        Number of learners who are in-progress in at least 1 course and whose last session is over 180 days ago (pathway-level)
        """
        return self.learners.filter(dropped_out=True).count()

    def pathway_dropout_rate(self):
        """
        Percentage of learners who are in-progress in at least 1 course and whose last session is over 180 days ago (pathway-level)
        """
        return self.no_of_dropped_out_pathway_learners() / self.total

    def no_of_pathway_graduates(self):
        """
        Number of learners who completed the pathway
        """
        return self.learners.filter(completed_pathway=True).count()

    def pathway_graduation_rate(self):
        """
        Percentage of learners completed the pathway
        """
        return self.no_of_pathway_graduates() / self.total

    def pathway_average_session_duration(self):
        """
        Total duration of all sessions divided by total number of sessions (pathway-level)
        """

    def pathway_course_units_session(self):
        """
        Average number of course units viewed during a session in the Coursebank Studio(?) (pathway-level)
        """


class CourseAnalytics:
    """
    Initialize with course argument
    ex. CourseAnalytics(course)
    """
    def __init__(self, course, *args, **kwargs):
        self.course = course
        self.learners = Learner.manager.course(course)
        self.total = self.learners.count()

    def no_of_learners_in_progress(self):
        """
        Number of learners who are in-progress in the course
        """
        return self.learners.filter(in_progress=True).count()

    def percent_of_learners_in_progress(self):
        """
        Percentage of enrollees who are in-progress in the course
        """
        return self.no_of_learners_in_progress() / self.total

    def no_of_active_learners(self):
        """
        Number of learners who are in-progress in the course and whose last session is at most 30 days ago
        """
        return self.learners.filter(active=True).count()

    def percent_of_active_learners(self):
        """
        Percentage of learners who are in-progress in the course and whose last session is at most 30 days ago
        """
        return self.no_of_active_learners() / self.total

    def no_of_inactive_learners(self):
        """
        Number of learners who are in-progress in the course and whose last session is over 30 days ago but at most 180 days ago
        """
        return self.learners.filter(inactive=True).count()

    def percent_of_inactive_learners(self):
        """
        Percentage of learners who are in-progress in the course and whose last session is over 30 days ago but at most 180 days ago
        """
        return self.no_of_inactive_learners() / self.total

    def no_of_dropped_out_learners(self):
        """
        Number of learners who are in-progress in the course and whose last session is over 180 days ago
        """
        return self.learners.filter(dropped_out=True).count()

    def dropout_rate(self):
        """
        Percentage of learners who are in-progress in the course and whose last session is over 180 days ago
        """
        return self.no_of_dropped_out_learners() / self.total

    def no_of_completed_learners(self):
        """
        Number of learners who completed the course
        """
        return self.learners.filter(completed_course=True).count()

    def completion_rate(self):
        """
        Percentage of learners who completed the course
        """
        return self.no_of_completed_learners() / self.total

    def average_session_duration(self):
        """
        Total duration of all sessions divided by total number of sessions (course-level)
        """

    def course_units_session(self):
        """
        Average number of course units viewed during a session in the Coursebank Studio  (course-level)
        """

    def net_promoter_score(self):
        """
        Net promoter score.  Computed as percentage of respondents who gave a rating of 8-10 minus the percentage of respondents who gave a rating of 1-3
        """

    def course_objectives_and_expectations_average_rating(self):
        """
        Computed as the average  of the average rating per survey question under Course Objectives and Expectations
        """

    def selection_sequencing_and_organization_average_rating(self):
        """
        Computed as the average  of the average rating per survey question under Selection, Sequencing, and Organization
        """

    def subject_matter_average_rating(self):
        """
        Computed as the average of the average rating per survey question under Subject Matter
        """

    def subject_matter_expert_average_rating(self):
        """
        Computed as the average of the average rating per survey question under Subject Matter Expert
        """


################
# COURSE UNIT #
###############


def course_unit():
    """
    Course Unit Label
    """

def average_rating():
    """
    Average Rating
    """

def average_session_duration():
    """
    Average Session Duration per Course Unit
    """