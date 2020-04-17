from datetime import datetime, timedelta, date

from courseware.models import StudentModule
from lms.djangoapps.certificates.models import certificate_status_for_student
from lms.djangoapps.courseware.courses import get_course_by_id
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment

from ..helpers.helpers import check_if_user_has_completed_course
from ..models import (
    Pathway,
    SpartaCourse,
    SpartaProfile,
    ExtendedSpartaProfile,
    EducationProfile,
    EmploymentProfile,
    TrainingProfile,
    PathwayApplication
)


def get_sparta_course_id_list():
    course_id_list = []
    for course in SpartaCourse.objects.filter(is_active=True):
        if course.course_id not in course_id_list:
            course_id_list.append(course.course_id)
    return course_id_list


def get_sparta_courses(course_id_list=None, course_enrollments=None):
    if course_id_list is None:
        course_id_list = get_sparta_course_id_list()
    if course_enrollments is None:
        course_enrollments = CourseEnrollment.objects.filter(is_active=True)

    courses = []
    for course_id in course_id_list:
        course_key = CourseKey.from_string(course_id)
        courseoverview = CourseOverview.get_from_id(course_key)

        this_course_enrollments = course_enrollments.filter(course=courseoverview)
        audit_enrollments = this_course_enrollments.filter(mode='audit')
        verified_enrollments = this_course_enrollments.filter(mode='verified')

        total_enrollments_count = this_course_enrollments.count()

        cert_count = 0
        for student in this_course_enrollments:
            cert_status = certificate_status_for_student(student.user, course_key)
            if cert_status and cert_status['mode'] == 'verified' or cert_status and cert_status['mode'] == 'honor':
                if cert_status['status'] not in  ['unavailable', 'notpassing', 'restricted', 'unverified']:
                    cert_count += 1

        name = courseoverview.display_name
        data = {
            'course_id': course_id,
            'slug': name.lower().replace(" ", "_").replace("-", "_"),
            'name': name,
            'total_no_of_enrollees': total_enrollments_count,
            'no_of_completed': cert_count,
            'no_of_unfinished': total_enrollments_count - cert_count,
            'percent_completed': str(100*cert_count/total_enrollments_count) if total_enrollments_count > 0 else "0"
        }

        if audit_enrollments.exists():
            data['no_of_audit_enrollees'] = audit_enrollments.count()
        else:
            data['no_of_audit_enrollees'] = 0

        if verified_enrollments.exists():
            data['no_of_verified_enrollees'] = verified_enrollments.count()
        else:
            data['no_of_verified_enrollees'] = 0

        courses.append(data)

    return courses


def get_sparta_enrollees_by_class(profiles=None, extended_profiles=None):
    if profiles is None:
        profiles = SpartaProfile.objects.all()
    if extended_profiles is None:
        extended_profiles = ExtendedSpartaProfile.objects.all()

    others_diff = profiles.count() - extended_profiles.count()

    student_queryset = extended_profiles.filter(affiliation=ExtendedSpartaProfile.STUDENT)
    student_count = student_queryset.count() if student_queryset.exists() else 0

    faculty_queryset = extended_profiles.filter(affiliation=ExtendedSpartaProfile.FACULTY)
    faculty_count = faculty_queryset.count() if faculty_queryset.exists() else 0

    private_queryset = extended_profiles.filter(affiliation=ExtendedSpartaProfile.PRIVATE)
    private_count = private_queryset.count() if private_queryset.exists() else 0

    government_queryset = extended_profiles.filter(affiliation=ExtendedSpartaProfile.GOVERNMENT)
    government_count = government_queryset.count() if government_queryset.exists() else 0

    data = {
        'student': student_count,
        'faculty': faculty_count,
        'private': private_count,
        'government': government_count,
        'others': others_diff if others_diff > 0 else 0
    }
    return data


def get_sparta_enrollees_by_age(profiles=None):
    if profiles is None:
        profiles = SpartaProfile.objects.all()

    this_year = datetime.now().year

    data = {}
    data['no_age'] = 0
    for profile in profiles:
        try:
            year_of_birth = profile.user.profile.year_of_birth
        except:
            data['no_age'] += 1
        else:
            if year_of_birth is not None:
                age = this_year - year_of_birth
                if age not in data:
                    data[str(age)] = 0
                data[str(age)] += 1
            else:
                data['no_age'] += 1

    list_data = []
    for a in data:
        list_data.append({
            'age': str(a),
            'count': data[a]
        })

    # return list_data[::-1]
    return sorted(list_data, key = lambda i: i['age'])


def get_sparta_enrollees_by_gender(profiles=None):
    if profiles is None:
        profiles = SpartaProfile.objects.all()

    male_count = 0
    female_count = 0
    other_count = 0
    for profile in profiles:
        try:
            gender = profile.user.profile.gender
        except:
            other_count += 1
        else:
            if gender == 'm':
                male_count += 1
            elif gender == 'f':
                female_count += 1
            else:
                other_count += 1
    return {
        'male': male_count,
        'female': female_count,
        'other': other_count
    }


def get_sparta_enrollees_by_location(profiles=None, extended_profiles=None):
    if profiles is None:
        profiles = SpartaProfile.objects.all()
    if extended_profiles is None:
        extended_profiles = ExtendedSpartaProfile.objects.all()

    others_diff = profiles.count() - extended_profiles.count()

    data = {}
    for profile in extended_profiles:
        municipality = profile.municipality
        if municipality not in data:
            data[municipality] = 0
        data[municipality] += 1

    list_data = []
    for m in data:
        if m == "---":
            continue
        list_data.append({
            'city': m,
            'count': data[m]
        })
    return sorted(list_data, key = lambda i: i['count'], reverse=True)[:10]


def get_sparta_enrollees_by_affiliation(profiles=None, extended_profiles=None):
    if profiles is None:
        profiles = SpartaProfile.objects.all()
    if extended_profiles is None:
        extended_profiles = ExtendedSpartaProfile.objects.all()

    others_diff = profiles.count() - extended_profiles.count()

    private_count = 0
    government_count = 0
    student_count = 0
    faculty_count = 0
    unknown_count = others_diff

    for eprofile in extended_profiles:
        if eprofile.affiliation == ExtendedSpartaProfile.PRIVATE:
            private_count += 1
        elif eprofile.affiliation == ExtendedSpartaProfile.GOVERNMENT:
            government_count += 1
        elif eprofile.affiliation == ExtendedSpartaProfile.STUDENT:
            student_count += 1
        elif eprofile.affiliation == ExtendedSpartaProfile.FACULTY:
            faculty_count += 1
        else:
            unknown_count += 1

    return {
        "private": private_count,
        "government": government_count,
        "student": student_count,
        "faculty": faculty_count,
        "unknown": unknown_count
    }


def get_sparta_enrollees_by_attainment(profiles=None, extended_profiles=None):
    if profiles is None:
        profiles = SpartaProfile.objects.all()
    if extended_profiles is None:
        extended_profiles = ExtendedSpartaProfile.objects.all()

    others_diff = profiles.count() - extended_profiles.count()

    doctorate_count = 0
    masters_count = 0
    bachelors_count = 0
    associate_count = 0
    senior_count = 0
    high_count = 0
    junior_count = 0
    elementary_count = 0
    other_count = 0
    no_formal_count = 0
    unknown_count = others_diff

    for eprofile in extended_profiles:
        if eprofile.attainment == ExtendedSpartaProfile.DOCTORATE:
            doctorate_count += 1
        elif eprofile.attainment == ExtendedSpartaProfile.MASTERS:
            masters_count += 1
        elif eprofile.attainment == ExtendedSpartaProfile.BACHELORS:
            bachelors_count += 1
        elif eprofile.attainment == ExtendedSpartaProfile.ASSOCIATE:
            associate_count += 1
        elif eprofile.attainment == ExtendedSpartaProfile.SENIOR_HIGH:
            senior_count += 1
        elif eprofile.attainment == ExtendedSpartaProfile.HIGH_SCHOOL:
            high_count += 1
        elif eprofile.attainment == ExtendedSpartaProfile.JUNIOR_HIGH:
            junior_count += 1
        elif eprofile.attainment == ExtendedSpartaProfile.ELEMENTARY:
            elementary_count += 1
        elif eprofile.attainment == ExtendedSpartaProfile.NO_FORMAL:
            others_count += 1
        elif eprofile.attainment == ExtendedSpartaProfile.OTHER_EDUC:
            no_formal_count += 1
        else:
            unknown_count += 1

    return {
        "doctorate": doctorate_count,
        "masters": masters_count,
        "bachelors": bachelors_count,
        "associate": associate_count,
        "senior": senior_count,
        "high": high_count,
        "junior": junior_count,
        "elementary": elementary_count,
        "other": other_count,
        "no_formal": no_formal_count,
        "unknown": unknown_count
    }


def weeklydates(start_date, end_date, weekday=2):
    d = start_date
    d += timedelta(days = weekday - d.weekday())
    while d <= end_date:
        yield d
        d += timedelta(days = 7)


def get_increase_in_enrollees(course_id_list=None, course_enrollments=None, start_date=None):
    if profiles is None:
        profiles = SpartaProfile.objects.all()
    if course_id_list is None:
        course_id_list = get_sparta_course_id_list()
    if course_enrollments is None:
        course_enrollments = CourseEnrollment.objects.filter(is_active=True)

    datetime_list = []
    if start_date is None:
        start_date = date(2020,1,1)
    end_date = datetime.now().date()
    for d in weeklydates(start_date, end_date):
        datetime_list.append(d)

    list_data = []
    for d in datetime_list:
        interval_enrollments = course_enrollments.filter(created__lte=d)
        enrollment_counter = 0
        for course_id in course_id_list:
            course_key = CourseKey.from_string(course_id)
            courseoverview = CourseOverview.get_from_id(course_key)
            this_course_enrollments = interval_enrollments.filter(course=courseoverview)
            enrollment_counter += this_course_enrollments.count()
        list_data.append({
            'date': d.strftime('%Y-%m-%d'),
            'count': enrollment_counter
        })

    return list_data


def get_applications_count_per_pathway(applications=None):
    if applications is None:
        applications = PathwayApplication.objects.all()

    return {
        "data_associate": applications.filter(pathway__slug="data-associate").count(),
        "data_steward": applications.filter(pathway__slug="data-steward").count(),
        "data_engineer": applications.filter(pathway__slug="data-engineer").count(),
        "data_scientist": applications.filter(pathway__slug="data-scientist").count(),
        "data_analyst": applications.filter(pathway__slug="functional-analyst").count(),
        "analytics_manager": applications.filter(pathway__slug="analytics-manager").count()
    }


def get_applications_count_per_status(applications=None):
    if applications is None:
        applications = PathwayApplication.objects.all()

    return {
        "approved": applications.filter(status="AP").count(),
        "pending": applications.filter(status="PE").count(),
        "widthrew": applications.filter(status="WE").count(),
        "disapproved": applications.filter(status="DE").count()
    }


def get_applications_count_per_week(applications=None, start_date=None):
    if applications is None:
        applications = PathwayApplication.objects.all()

    datetime_list = []
    if start_date is None:
        start_date = date(2020,1,1)
    end_date = datetime.now().date()
    for d in weeklydates(start_date, end_date):
        datetime_list.append(d)

    data = []
    for d in datetime_list:
        data.append({
            'date': d.strftime('%Y-%m-%d'),
            'count': applications.filter(created_at__lte=d).count()
        })

    return data


def get_course_weekly_enrollments(course_id, course_enrollments=None, start_date=None):
    """"""
    if course_enrollments is None:
        course_enrollments = CourseEnrollment.objects.filter(is_active=True)

    course_key = CourseKey.from_string(course_id)
    courseoverview = CourseOverview.get_from_id(course_key)
    this_course_enrollments = course_enrollments.filter(course=courseoverview)
    enrollments_count = this_course_enrollments.count()

    datetime_list = []
    if start_date is None:
        start_date = date(2020,1,1)
    end_date = datetime.now().date()
    for d in weeklydates(start_date, end_date):
        datetime_list.append(d)

    list_data = []
    for i in range(0, len(datetime_list)):
        start_date = datetime_list[i]
        interval_enrollments = course_enrollments.filter(created__gte=start_date)

        i_plus_one = i + 1
        if i_plus_one < len(datetime_list):
            end_date = datetime_list[i+1]
            interval_enrollments = interval_enrollments.filter(created__lte=end_date)
            end_date_str = end_date.strftime('%Y-%m-%d')
        else:
            end_date_str = ""

        enrollment_counter = 0
        course_key = CourseKey.from_string(course_id)
        courseoverview = CourseOverview.get_from_id(course_key)
        this_course_enrollments = interval_enrollments.filter(course=courseoverview)

        list_data.append({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date_str,
            'count': this_course_enrollments.count()
        })

    return list_data


def get_course_completion_rates(course_id, course_enrollments=None):
    """"""
    course_key = CourseKey.from_string(course_id)

    if course_enrollments is None:
        course_enrollments = CourseEnrollment.objects.filter(is_active=True).filter(course=CourseOverview.get_from_id(course_key))

    course = get_course_by_id(course_key)

    completed_count = 0
    completion_75_to_99_percent_count = 0
    completion_50_to_74_percent_count = 0
    completion_25_to_49_percent_count = 0
    completion_10_to_24_percent_count = 0
    completion_less_10_percent_count = 0

    for student_enrollment in course_enrollments:
        student = student_enrollment.user
        if check_if_user_has_completed_course(student.username, course_id):
            completed_count += 1
        else:
            course_grade = CourseGradeFactory().read(student, course)
            grade_summary = course_grade.summary
            course_grade_percent = grade_summary['percent']
            if course_grade_percent >= 0.75:
                completion_75_to_99_percent_count += 1
            elif course_grade_percent >= 0.5:
                completion_50_to_74_percent_count += 1
            elif course_grade_percent >= 0.25:
                completion_25_to_49_percent_count += 1
            elif course_grade_percent >= 0.10:
                completion_10_to_24_percent_count += 1
            else:
                completion_less_10_percent_count += 1

    return {
        "completed": completed_count,
        "completion_75_to_99_percent": completion_75_to_99_percent_count,
        "completion_50_to_74_percent": completion_50_to_74_percent_count,
        "completion_25_to_49_percent": completion_25_to_49_percent_count,
        "completion_10_to_24_percent": completion_10_to_24_percent_count,
        "completion_less_10_percent": completion_less_10_percent_count
    }


def get_learner_activity_status(user, course_key, modules=None):
    if modules is None:
        modules = StudentModule.objects.filter(course_id=course_key, student=user)

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
        else:
            status = "inactive"
    else:
        status = "inactive"

    return status


def get_course_learner_activity(course_id, course_enrollments=None, modules=None):
    """"""
    course_key = CourseKey.from_string(course_id)

    if course_enrollments is None:
        course_enrollments = CourseEnrollment.objects.filter(is_active=True).filter(course=CourseOverview.get_from_id(course_key))

    if modules is None:
        modules = StudentModule.objects.filter(course_id=course_key)

    active_count = 0
    inactive_count = 0
    for student_enrolled in course_enrollments:
        this_modules = modules.filter(student=student_enrolled.user)
        status = get_learner_activity_status(student_enrolled.user, course_key, modules=this_modules)
        if status == "active":
            active_count += 1
        else:
            inactive_count += 1

    return {
        "active": active_count,
        "inactive": inactive_count
    }


def get_weekly_enrollments_count_by_pathway(pathway, course_enrollments=None):
    if course_enrollments is None:
        course_enrollments = CourseEnrollment.objects.filter(is_active=True)

    course_id_list = []
    for course in pathway.courses.all().filter(is_active=True):
        if course.course_id not in course_id_list:
            course_id_list.append(course.course_id)

    return get_increase_in_enrollees(
        course_id_list=course_id_list,
        course_enrollments=course_enrollments
        )
