import csv
from datetime import datetime
from django.utils import timezone

from django.core.mail import send_mail, EmailMessage

from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment

from .local_settings import LOCAL_STAFF_EMAIL
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


def get_first_clean_coupon(coupons):
    for c in coupons:
        if c.get_records():
            continue
        else:
            return c


def assign_coupons_to_students():
    """"""
    for student in SpartaProfile.objects.filter(is_active=True):
        applications = PathwayApplication.objects.filter(profile=student).filter(status="AP")
        if not applications.exists():
            continue

        screcords = StudentCouponRecord.objects.filter(profile=student)

        for a in applications:
            for c in a.pathway.courses.all():
                #check if coupon for this course already assigned for this student
                these_screcords = screcords.filter(coupon__course_id=c.course_id)
                if these_screcords.exists():
                    continue

                coup = get_first_clean_coupon(SpartaCoupon.objects.filter(is_active=True).filter(course_id=course_id))
                StudentCouponRecord.objects.create(
                    profile=student,
                    coupon=coup
                )


def email_sparta_student_coupon_records(date_from=None, date_to=None):
    records = StudentCouponRecord.objects.all()

    datefrom_str = ""
    dateto_str = ""

    if date_from:
        applications = applications.filter(created_at__gte=date_from)
        datefrom_str = date_from.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    if date_to:
        applications = applications.filter(created_at__lte=date_to)
        dateto_str = date_to.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    file_name = '/home/ubuntu/tempfiles/sparta_coupon_records_file_{}.csv'.format(tnow)
    with open(file_name, mode='w') as apps_file:
        writer = csv.writer(apps_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        HEAD_ARR = ['email',]
        for c in SpartaCourse.objects.all():
            if c.course_id not in HEAD_ARR:
                HEAD_ARR.append(c.course_id)
        writer.writerow(CSV_ARR)

        for s in SpartaProfile.objects.filter(is_active=True):
            ROW_ARR = [s.user.email,]

            student_records = records.filter(profile=s)

            for c in HEAD_ARR[1:]:
                c_records = student_records.filter(coupon__course_id=c)
                if c_records.exists():
                    ROW_ARR.append(c_records[0].coupon.code)
                else:
                    ROW_ARR.append("")

            writer.writerow(ROW_ARR)

    if datefrom_str or dateto_str:
        date_range = ' for date range: {} to {}'.format(datefrom_str, dateto_str)
    else:
        date_range = ""

    email = EmailMessage(
        'Coursebank - SPARTA Assigned Coupons List - {}'.format(tnow),
        'Attached file of SPARTA Assigned Coupons List - {}'.format(date_range),
        'no-reply-sparta-coupons-list@coursebank.ph',
        [LOCAL_STAFF_EMAIL,],
    )
    email.attach_file(file_name)
    email.send()
