import csv
from datetime import datetime
from django.utils import timezone

from django.core.mail import send_mail, EmailMessage

from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment

from .analytics import OverallAnalytics, PathwayAnalytics
from .local_settings import LOCAL_STAFF_EMAIL, LOCAL_COUPON_WARNING_LIMIT
from .models import (
    Pathway, SpartaCourse, SpartaProfile,
    EducationProfile, EmploymentProfile, TrainingProfile,
    PathwayApplication, Event,
    SpartaCoupon, StudentCouponRecord
)


def manage_pathway_applications():
    """"""
    for app in PathwayApplication.objects.filter(status="PE"):
        app.approve()


def manage_sparta_enrollments(date_from=None, date_to=None):
    applications = PathwayApplication.objects.all()

    datefrom_str = ""
    dateto_str = ""

    if date_from:
        applications = applications.filter(created_at__gte=date_from)
        datefrom_str = date_from.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    if date_to:
        applications = applications.filter(created_at__lte=date_to)
        dateto_str = date_to.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    student_list = []
    for app in applications.filter(status="AP"):
        # user_enrollments = CourseEnrollment.enrollments_for_user(app.profile.user
        student_list.append({'user': app.profile.user, 'pathway': app.pathway, 'courses': app.pathway.courses.all()})

    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    file_name = '/home/ubuntu/tempfiles/sparta_applications_file_{}.csv'.format(tnow)
    with open(file_name, mode='w') as apps_file:
        writer = csv.writer(apps_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        writer.writerow(['User_ID', 'Username', 'Email', 'Pathway_ID', 'Pathway_Name', 'Course_Keys'])
        for student in student_list:
            user = student['user']
            pathway = student['pathway']
            courses = student['courses']
            course_keys = ""
            for course in courses:
                course_keys = course_keys + course.course_id + ";"
            writer.writerow([user.id, user.username, user.email, pathway.id, pathway.name, course_keys])

    if datefrom_str or dateto_str:
        date_range = ' for date range: {} to {}'.format(datefrom_str, dateto_str)
    else:
        date_range = ""

    email = EmailMessage(
        'Coursebank - SPARTA Applications - {}'.format(tnow),
        'Attached file of SPARTA Applications{}'.format(date_range),
        'no-reply-sparta-applications@coursebank.ph',
        [LOCAL_STAFF_EMAIL,],
    )
    email.attach_file(file_name)
    email.send()


class SpentCouponsException(Exception):
    pass


def get_first_clean_coupon(coupons):
    for c in coupons:
        if c.get_records():
            continue
        else:
            return c
    raise SpentCouponsException("No more coupons available.")


def check_if_enough_clean_coupons(course):
    coupons = SpartaCoupon.objects.filter(course_id=course.course_id)
    records = StudentCouponRecord.objects.filter(coupon__course_id=course.course_id)
    return coupons.count() - records.count() > LOCAL_COUPON_WARNING_LIMIT


def get_courses_that_need_new_coupons_list():
    courses_that_need_new_coupons_list = []
    coupons = SpartaCoupon.objects.filter(is_active=True)
    for course in SpartaCourse.objects.filter(is_active=True):
        if not check_if_enough_clean_coupons(course):
            if course.course_id not in courses_that_need_new_coupons_list:
                courses_that_need_new_coupons_list.append(course.course_id)
    return courses_that_need_new_coupons_list


def assign_coupons_to_single_student(student):
    applications = PathwayApplication.objects.filter(profile=student).filter(status="AP")
    if applications.exists():
        screcords = StudentCouponRecord.objects.filter(profile=student)

        for a in applications:
            for c in a.pathway.courses.all():
                # check if coupon for this course already assigned for this student
                these_screcords = screcords.filter(coupon__course_id=c.course_id)
                if not these_screcords.exists():
                    # assign clean coupon to student
                    try:
                        coup = get_first_clean_coupon(SpartaCoupon.objects.filter(is_active=True).filter(course_id=c.course_id))
                    except SpentCouponsException as e:
                        raise e

                    StudentCouponRecord.objects.create(
                        profile=student,
                        coupon=coup
                    )


def assign_coupons_to_students():
    """"""
    profiles = SpartaProfile.objects.filter(is_active=True)
    for student in profiles:
        assign_coupons_to_single_student(student)


def email_sparta_student_coupon_records(email=None, pathway=None):
    profiles = SpartaProfile.objects.filter(is_active=True)
    if email:
        profiles = profiles.filter(user__email=email)

    if pathway:
        courses = SpartaCourse.objects.filter(pathway=pathway)
    else:
        courses = SpartaCourse.objects.all()

    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    file_name = '/home/ubuntu/tempfiles/sparta_coupon_records_file_{}.csv'.format(tnow)
    with open(file_name, mode='w') as coupons_file:
        writer = csv.writer(coupons_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        HEAD_ARR = ['Email Address',]
        for c in courses:
            if c.course_id not in HEAD_ARR:
                HEAD_ARR.append(c.course_id)
        writer.writerow(HEAD_ARR)

        for s in profiles:
            ROW_ARR = [s.user.email,]

            student_records = StudentCouponRecord.objects.filter(profile=s)

            for c in HEAD_ARR[1:]:
                c_records = student_records.filter(coupon__course_id=c)
                if c_records.exists():
                    ROW_ARR.append(c_records[0].coupon.code)
                else:
                    ROW_ARR.append("")

            writer.writerow(ROW_ARR)

    email = EmailMessage(
        'Coursebank - SPARTA Assigned Coupons List - {}'.format(tnow),
        'Attached file of SPARTA Assigned Coupons List',
        'no-reply-sparta-coupons-list@coursebank.ph',
        [LOCAL_STAFF_EMAIL,],
    )
    email.attach_file(file_name)
    email.send()


def get_enrollment_status(email=None, pathway=None):
    profiles = SpartaProfile.objects.filter(is_active=True)
    if email:
        profiles = profiles.filter(user__email=email)

    if pathway:
        courses = SpartaCourse.objects.filter(pathway=pathway)
    else:
        courses = SpartaCourse.objects.all()

    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    file_name = '/home/ubuntu/tempfiles/sparta_enrollments_file_{}.csv'.format(tnow)
    with open(file_name, mode='w') as coupons_file:
        writer = csv.writer(coupons_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        HEAD_ARR = ['Email Address',]
        for c in courses:
            if c.course_id not in HEAD_ARR:
                HEAD_ARR.append(c.course_id)
        writer.writerow(HEAD_ARR)

        for s in profiles:
            ROW_ARR = [s.user.email,]

            student_records = StudentCouponRecord.objects.filter(profile=s)

            for c in HEAD_ARR[1:]:
                c_records = student_records.filter(coupon__course_id=c)
                if c_records.exists():
                    status = "True" if c_records[0].is_user_verified else "False"
                    ROW_ARR.append(status)
                else:
                    ROW_ARR.append("False")

            writer.writerow(ROW_ARR)

    email = EmailMessage(
        'Coursebank - SPARTA Enrollments List - {}'.format(tnow),
        'Attached file of SPARTA Enrollments List',
        'no-reply-sparta-enrollments-list@coursebank.ph',
        [LOCAL_STAFF_EMAIL,],
    )
    email.attach_file(file_name)
    email.send()


def email_sparta_overall_reports():
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    analytics = OverallAnalytics()
    overall_no_of_registered_sparta_learners = analytics.profiles.count()
    overall_no_of_enrollees = analytics.overall_no_of_enrollees()
    overall_no_of_learners_in_progress = analytics.overall_no_of_learners_in_progress()
    percent_of_learners_in_progress = analytics.percent_of_learners_in_progress()
    overall_no_of_active_learners = analytics.overall_no_of_active_learners()
    percent_of_active_learners = analytics.percent_of_active_learners()
    overall_no_of_inactive_learners = analytics.overall_no_of_inactive_learners()
    percent_of_inactive_learners = analytics.percent_of_inactive_learners()
    overall_no_of_dropped_out_learners = analytics.overall_no_of_dropped_out_learners()
    overall_dropout_rate = analytics.overall_dropout_rate()
    overall_no_of_graduates = analytics.overall_no_of_graduates()
    overall_graduation_rate = analytics.overall_graduation_rate()

    file_name = '/home/ubuntu/tempfiles/sparta_coupon_records_file_{}.csv'.format(tnow)
    with open(file_name, mode='w') as coupons_file:
        writer = csv.writer(coupons_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            'Timestamp',
            'Overall Number of Registered SPARTA Learners',
            'Overall Number of Enrollees',
            'Overall Number of Learners in Progress',
            'Percent of Learners in Progress',
            'Overall Number of Active Learners',
            'Percent of Active Learners',
            'Overall Number of Inactive Learners',
            'Percent of Inactive Learners',
            'Overall Number of Dropped Out Learners',
            'Overall Dropout Rate',
            'Overall Number of Graduates',
            'Overall Graduation Rate'
            ])
        writer.writerow([
            tnow,
            overall_no_of_registered_sparta_learners,
            overall_no_of_enrollees,
            overall_no_of_learners_in_progress,
            percent_of_learners_in_progress,
            overall_no_of_active_learners,
            percent_of_active_learners,
            overall_no_of_inactive_learners,
            percent_of_inactive_learners,
            overall_no_of_dropped_out_learners,
            overall_dropout_rate,
            overall_no_of_graduates,
            overall_graduation_rate
            ])

    email = EmailMessage(
        'Coursebank - SPARTA Overall Analytics - {}'.format(tnow),
        'Attached file of SPARTA Overall Analytics',
        'no-reply-sparta-overall-analytics@coursebank.ph',
        [LOCAL_STAFF_EMAIL,],
    )
    email.attach_file(file_name)
    email.send()


def email_sparta_pathway_learners_reports(slug):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    pathway = Pathway.objects.get(slug=slug, is_active=True)
    analytics = PathwayAnalytics(pathway)
    learners = analytics.queryset()

    file_name = '/home/ubuntu/tempfiles/sparta_pathway_analytics_file_{}.csv'.format(tnow)
    with open(file_name, mode='w') as coupons_file:
        writer = csv.writer(coupons_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            '#',
            'Affiliation',
            'Highest Educational Attainment',
            'Gender',
            'Area of Residence'
            ])

        count = 0
        for learner in learners:
            count += 1
            if learner.extended_profile:
                affiliation = learner.extended_profile.get_affiliation_display()
                attainment = learner.extended_profile.get_attainment_display()
            else:
                affiliation = ""
                attainment = learner.user.profile.get_level_of_education_display() or ""

            writer.writerow([
                count,
                affiliation,
                attainment,
                learner.user.profile.get_gender_display(),
                learner.user.profile.city
                ])

    email = EmailMessage(
        'Coursebank - SPARTA {} Pathway Analytics - {}'.format(pathway.name, tnow),
        'Attached file of SPARTA Pathway Analytics',
        'no-reply-sparta-pathway-learners-report@coursebank.ph',
        [LOCAL_STAFF_EMAIL,],
    )
    email.attach_file(file_name)
    email.send()


def email_sparta_pathway_reports(slug):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    pathway = Pathway.objects.get(slug=slug, is_active=True)
    analytics = PathwayAnalytics(pathway)

    no_of_pathway_enrollees = analytics.no_of_pathway_enrollees()
    no_of_pathway_learners_in_progress = analytics.no_of_pathway_learners_in_progress()
    percent_of_pathway_learners_in_progress = analytics.percent_of_pathway_learners_in_progress()
    no_of_active_pathway_learners = analytics.no_of_active_pathway_learners()
    percent_of_active_pathway_learners = analytics.percent_of_active_pathway_learners()
    no_of_inactive_pathway_learners = analytics.no_of_inactive_pathway_learners()
    percent_of_inactive_pathway_learners = analytics.percent_of_inactive_pathway_learners()
    no_of_dropped_out_pathway_learners = analytics.no_of_dropped_out_pathway_learners()
    pathway_dropout_rate = analytics.pathway_dropout_rate()
    no_of_pathway_graduates = analytics.no_of_pathway_graduates()
    pathway_graduation_rate = analytics.pathway_graduation_rate()

    file_name = '/home/ubuntu/tempfiles/sparta_pathway_analytics_file_{}.csv'.format(tnow)
    with open(file_name, mode='w') as coupons_file:
        writer = csv.writer(coupons_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            'Timestamp',
            'Pathway',
            'Number of Pathway Enrollees',
            'Number of Pathway Learners in Progress',
            'Percent of Pathway Learners in Progress',
            'Number of Active Pathway Learners',
            'Percent of Active Pathway Learners',
            'Number of Inactive Pathway Learners',
            'Percent of Inactive Pathway Learners',
            'Number of Dropped Out Pathway Learners',
            'Pathway Dropout Rate',
            'Number of Pathway Graduates',
            'Pathway Graduation Rate'
            ])
        writer.writerow([
            tnow,
            pathway.name,
            no_of_pathway_enrollees,
            no_of_pathway_learners_in_progress,
            percent_of_pathway_learners_in_progress,
            no_of_active_pathway_learners,
            percent_of_active_pathway_learners,
            no_of_inactive_pathway_learners,
            percent_of_inactive_pathway_learners,
            no_of_dropped_out_pathway_learners,
            pathway_dropout_rate,
            no_of_pathway_graduates,
            pathway_graduation_rate
            ])

    email = EmailMessage(
        'Coursebank - SPARTA {} Pathway Analytics - {}'.format(pathway.name, tnow),
        'Attached file of SPARTA {} Learning Pathway Analytics'.format(pathway.name),
        'no-reply-sparta-pathways-report@coursebank.ph',
        [LOCAL_STAFF_EMAIL,],
    )
    email.attach_file(file_name)
    email.send()
