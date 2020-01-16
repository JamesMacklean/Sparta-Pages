import csv
from datetime import datetime
from django.utils import timezone

from django.core.mail import send_mail, EmailMessage

from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment

from .local_settings import LOCAL_STAFF_EMAIL, LOCAL_COUPON_WARNING_LIMIT
from .models import Pathway, SpartaCourse, SpartaProfile, EducationProfile, EmploymentProfile, TrainingProfile, PathwayApplication, Event


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


def check_if_enough_clean_coupons(coupons):
    count = 0
    for c in coupons:
        if c.get_records():
            continue
        else:
            count += 1
    return count > LOCAL_COUPON_WARNING_LIMIT


def get_courses_that_need_new_coupons_list():
    courses_that_need_new_coupons_list = []
    coupons = SpartaCoupon.objects.filter(is_active=True)
    for course in SpartaCourse.objects.filter(is_active=True):
        if not check_if_enough_clean_coupons(coupons.filter(course_id=course.course_id)):
            if course.course_id not in courses_that_need_new_coupons_list:
                courses_that_need_new_coupons_list.append(course.course_id)
    return courses_that_need_new_coupons_list


def assign_coupons_to_single_student(student):
    applications = PathwayApplication.objects.filter(profile=student).filter(status="AP")
    if not applications.exists():
        continue

    screcords = StudentCouponRecord.objects.filter(profile=student)

    for a in applications:
        for c in a.pathway.courses.all():
            # check if coupon for this course already assigned for this student
            these_screcords = screcords.filter(coupon__course_id=c.course_id)
            if these_screcords.exists():
                continue

            # assign clean coupon to student
            try:
                coup = get_first_clean_coupon(SpartaCoupon.objects.filter(is_active=True).filter(course_id=course_id))
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
