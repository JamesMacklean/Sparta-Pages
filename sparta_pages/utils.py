import csv
from datetime import datetime, timedelta
from django.utils import timezone
import logging
import unicodecsv

from django.db import connection
from django.core.mail import send_mail, EmailMessage
from django.shortcuts import render, redirect, get_object_or_404

from courseware.models import StudentModule
from lms.djangoapps.certificates.models import certificate_status_for_student
from lms.djangoapps.certificates.api import get_certificate_for_user
from lms.djangoapps.courseware.courses import get_course_by_id
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from lms.djangoapps.verify_student.services import IDVerificationService
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment, UserProfile
from django.contrib.auth.models import User

from .analytics import OverallAnalytics, PathwayAnalytics
from .api.utils import get_sparta_course_id_list
from .cities import get_region_from_municipality
from .helpers.helpers_utils import get_course_outline_block_tree
from .local_settings import LOCAL_STAFF_EMAIL, LOCAL_COUPON_WARNING_LIMIT, LOCAL_INTRO_COURSE_ID
from .models import (
    Pathway, SpartaCourse, SpartaProfile, ExtendedSpartaProfile,
    EducationProfile, EmploymentProfile, TrainingProfile,
    PathwayApplication, Event,
    SpartaCoupon, StudentCouponRecord
)
from sparta_pages.models import SpartaReEnrollment

logger = logging.getLogger(__name__)


def manage_pathway_applications():
    """"""
    for app in PathwayApplication.objects.filter(status="PE"):
        app.approve()


def manage_sparta_applications_list(email_address=None, date_from=None, date_to=None):
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
        student_list.append({
            'user': app.profile.user,
            'pathway': app.pathway,
            'courses': app.pathway.courses.all(),
            'created': app.created_at.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            })

    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    file_name = '/home/ubuntu/tempfiles/sparta_applications_file_{}.csv'.format(tnow)
    with open(file_name, mode='w') as apps_file:
        writer = csv.writer(apps_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        writer.writerow(['User_ID', 'Username', 'Email', 'Pathway_ID', 'Pathway_Name', 'Course_Keys', 'Time Created'])
        for student in student_list:
            user = student['user']
            pathway = student['pathway']
            courses = student['courses']
            created = student['created']
            course_keys = ""
            for course in courses:
                course_keys = course_keys + course.course_id + ";"
            writer.writerow([user.id, user.username, user.email, pathway.id, pathway.name, course_keys, created])

    if datefrom_str or dateto_str:
        date_range = ' for date range: {} to {}'.format(datefrom_str, dateto_str)
    else:
        date_range = ""

    if email_address:
        email = EmailMessage(
            'Coursebank - SPARTA Applications - {}'.format(tnow),
            'Attached file of SPARTA Applications{}'.format(date_range),
            'no-reply-sparta-applications@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()


class SpentCouponsException(Exception):
    pass


def get_first_clean_coupon(coupons=None, course_id=None, all_sc_records=None):
    try:
        if coupons is None or course_id is None or all_sc_records is None:
            raise Exception("get_first_clean_coupon_error: No coupons or course_id or all_sc_records indicated.")

        if not coupons.exists():
            raise SpentCouponsException("No more coupons available for course_id {}".format(course_id))

        coup = None
        for c in coupons:
            if all_sc_records.filter(coupon=c).exists():
                continue
            else:
                coup = c

        return coup
    except Exception as e:
        raise Exception("get_first_clean_coupon: {}".format(str(e)))

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
    try:
        applications = PathwayApplication.objects.filter(profile=student).filter(status="AP")
        all_sc_records = StudentCouponRecord.objects.all()
        if applications.exists():
            screcords = all_sc_records.filter(profile=student)

            for a in applications:
                for c in a.pathway.courses.all():
                    #skip if intro course
                    if c.course_id == LOCAL_INTRO_COURSE_ID:
                        continue
                    # check if coupon for this course already assigned for this student
                    these_screcords = screcords.filter(coupon__course_id=c.course_id)
                    if not these_screcords.exists():
                        # assign clean coupon to student
                        try:
                            coup = get_first_clean_coupon(
                                coupons=SpartaCoupon.objects.filter(is_active=True).filter(course_id=c.course_id).order_by('-created'),
                                course_id=c.course_id,
                                all_sc_records=all_sc_records
                                )
                        except SpentCouponsException as e:
                            raise e
                        except Exception as e:
                            raise Exception("Error in getting first clean coupon: {}".format(str(e)))

                        if coup is not None:
                            try:
                                StudentCouponRecord.objects.create(
                                    profile=student,
                                    coupon=coup
                                )
                            except Exception as e:
                                raise Exception("Error in creating StudentCouponRecord: {}".format(str(e)))
                        else:
                            logger.info("No more coupons available for {}.".format(c.course_id))

    except Exception as e:
        error_str = "assign_coupons_to_single_student_error: {}".format(str(e))
        logger.info(error_str)
        raise Exception(error_str)


def assign_coupons_to_students():
    """"""
    profiles = SpartaProfile.objects.filter(is_active=True)
    count = 0
    total = profiles.count()
    for student in profiles:
        print('Starting to assign coupons for student {}...'.format(student.user.username))
        assign_coupons_to_single_student(student)
        print('Finished assigning coupons for student {}!'.format(student.user.username))
        count += 1
        print("Progress: {} out of {} students".format(count, total))


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
    overall_no_of_registered_sparta_learners = analytics.learners.profiles.count()
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

    file_name = '/home/ubuntu/tempfiles/sparta_overall_analytics_file_{}.csv'.format(tnow)
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
        'Coursebank - SPARTA Overall Report - {}'.format(tnow),
        'Attached file of SPARTA Overall Report',
        'no-reply-sparta-overall-report@coursebank.ph',
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

    _slug = pathway.slug.replace("-", "_")
    file_name = '/home/ubuntu/tempfiles/sparta_pathway_{}_learners_report_file_{}.csv'.format(_slug, tnow)
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
                attainment = learner.user.profile.get_grad_degree_display() or ""

            writer.writerow([
                count,
                affiliation,
                attainment,
                learner.user.profile.get_gender_display(),
                learner.user.profile.city
                ])

    email = EmailMessage(
        'Coursebank - SPARTA {} Pathway Learners Report - {}'.format(pathway.name, tnow),
        'Attached file of SPARTA Pathway Learners Report',
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

    _slug = pathway.slug.replace("-", "_")
    file_name = '/home/ubuntu/tempfiles/sparta_pathway_{}_report_file_{}.csv'.format(_slug, tnow)
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
        'Coursebank - SPARTA {} Pathway Report - {}'.format(pathway.name, tnow),
        'Attached file of SPARTA {} Learning Pathway Report'.format(pathway.name),
        'no-reply-sparta-pathways-report@coursebank.ph',
        [LOCAL_STAFF_EMAIL,],
    )
    email.attach_file(file_name)
    email.send()


def export_sparta_profiles(email_address=None, is_active=True, *args, **kwargs):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    profiles = SpartaProfile.objects.filter(is_active=is_active)
    if len(kwargs) > 0:
        profiles = profiles.filter(**kwargs)

    file_name = '/home/ubuntu/tempfiles/export_sparta_profiles_{}.csv'.format(tnow)
    with open(file_name, mode='w') as csv_file:
        writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
        writer.writerow([
            'Username', 'Email', 'Is Active', 'Name',
            'Address', 'Municipality', 'Age', 'Gender',
            'Affiliation', 'Attainment',
            'Other', 'Is Employed?', 'Graduate Degree'
            ])

        for profile in profiles:
            is_active = "True" if profile.is_active else "False"
            try:
                eprofile = ExtendedSpartaProfile.objects.get(user=profile.user)
                user_profile = eprofile.user.profile
            except:
                address = municipality = age = gender = affiliation = attainment = other_attain = is_employed = grad_degree = ""
            else:
                address = eprofile.address
                municipality = eprofile.get_municipality_display()
                if user_profile.year_of_birth is not None:
                    age = datetime.now().year - user_profile.year_of_birth
                else:
                    age = None
                gender = user_profile.get_gender_display()
                affiliation = eprofile.get_affiliation_display()
                attainment = eprofile.get_attainment_display()
                other_attain = eprofile.other_attain
                is_employed = "True" if eprofile.is_employed else "False"
                grad_degree = eprofile.get_grad_degree_display()

            writer.writerow([
                profile.user.username, profile.user.email, is_active, profile.user.profile.name,
                address, municipality, age, gender,
                affiliation, attainment,
                other_attain, is_employed, grad_degree
                ])

    if email_address:
        email = EmailMessage(
            'Coursebank - SPARTA Profiles',
            'Attached file of SPARTA Profiles (as of {})'.format(tnow),
            'no-reply-sparta-profiles@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()


def export_sparta_education_credentials(email_address=None, is_active=True, *args, **kwargs):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    profiles = SpartaProfile.objects.filter(is_active=is_active)
    if len(kwargs) > 0:
        profiles = profiles.filter(**kwargs)

    education_profiles = EducationProfile.objects.filter(profile__in=profiles)

    file_name = '/home/ubuntu/tempfiles/export_sparta_education_credentials_{}.csv'.format(tnow)
    with open(file_name, mode='w') as csv_file:
        writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
        writer.writerow([
            'Username', 'Email',
            'Degree', 'Course', 'School',
            'Address', 'Started', 'Graduated'
            ])

        for eprofile in education_profiles:
            started = eprofile.started_at.strftime('%Y-%m-%d')
            graduated = eprofile.graduated_at.strftime('%Y-%m-%d')
            writer.writerow([
                eprofile.profile.user.username, eprofile.profile.user.email,
                eprofile.get_degree_display(), eprofile.course, eprofile.school,
                eprofile.address, started, graduated
                ])

    if email_address:
        email = EmailMessage(
            'Coursebank - SPARTA Education Credentials',
            'Attached file of SPARTA  Education Credentials (as of {})'.format(tnow),
            'no-reply-sparta-education-credentials@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()

def export_sparta_employment_credentials(email_address=None, is_active=True, *args, **kwargs):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    profiles = SpartaProfile.objects.filter(is_active=is_active)
    if len(kwargs) > 0:
        profiles = profiles.filter(**kwargs)

    employment_profiles = EmploymentProfile.objects.filter(profile__in=profiles)

    file_name = '/home/ubuntu/tempfiles/export_sparta_employment_credentials_{}.csv'.format(tnow)
    with open(file_name, mode='w') as csv_file:
        writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
        writer.writerow([
            'Username', 'Email',
            'Affiliation', 'Occupation', 'Designation',
            'Employer', 'Address', 'Started', 'Ended'])

        for eprofile in employment_profiles:
            started = eprofile.started_at.strftime('%Y-%m-%d')
            ended = eprofile.ended_at
            if ended is not None:
                ended = eprofile.ended_at.strftime('%Y-%m-%d')

            writer.writerow([
                eprofile.profile.user.username, eprofile.profile.user.email,
                eprofile.get_affiliation_display(), eprofile.occupation, eprofile.designation,
                eprofile.employer, eprofile.address, started, ended
                ])

    if email_address:
        email = EmailMessage(
            'Coursebank - SPARTA Employment Credentials',
            'Attached file of SPARTA Employment Credentials (as of {})'.format(tnow),
            'no-reply-sparta-employment-credentials@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()

def export_sparta_training_credentials(email_address=None, is_active=True, *args, **kwargs):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    profiles = SpartaProfile.objects.filter(is_active=is_active)
    if len(kwargs) > 0:
        profiles = profiles.filter(**kwargs)

    training_profiles = TrainingProfile.objects.filter(profile__in=profiles)

    file_name = '/home/ubuntu/tempfiles/export_sparta_training_credentials_{}.csv'.format(tnow)
    with open(file_name, mode='w') as csv_file:
        writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
        writer.writerow([
            'Username', 'Email',
            'Title', 'Organizer', 'Address',
            'Started', 'Ended'])

        for tprofile in training_profiles:
            writer.writerow([
                tprofile.profile.user.username, tprofile.profile.user.email,
                tprofile.title, tprofile.organizer, tprofile.address,
                tprofile.started_at.strftime('%Y-%m-%d'),
                tprofile.ended_at.strftime('%Y-%m-%d')
                ])

    if email_address:
        email = EmailMessage(
            'Coursebank - SPARTA Training Credentials',
            'Attached file of SPARTA Training Credentials (as of {})'.format(tnow),
            'no-reply-sparta-training-credentials@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()


def export_sparta_completed_courses(email_address=None, course_id=None, is_active=True):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    course_id_list = []
    if course_id is not None:
        course_id_list.append(course_id)
    else:
        for course in SpartaCourse.objects.filter(is_active=is_active):
            if course.course_id not in course_id_list:
                course_id_list.append(course.course_id)

    course_list = []
    for course_id in course_id_list:
        data = {}
        data['course_id'] = course_id

        course_key = CourseKey.from_string(course_id)
        courseoverview = CourseOverview.get_from_id(course_key)
        data['course_name'] = courseoverview.display_name

        enrollments = CourseEnrollment.objects.filter(course=courseoverview).filter(is_active=True).filter(mode__in=['verified', 'honor'])

        cert_count = 0
        for student in enrollments:
            cert_status = certificate_status_for_student(student.user, course_key)
            if cert_status and cert_status['mode'] == 'verified' or cert_status and cert_status['mode'] == 'honor':
                if cert_status['status'] not in  ['unavailable', 'notpassing', 'restricted', 'unverified']:
                    cert_count += 1
        data['completed_count'] = cert_count

        course_list.append(data)

    file_name = '/home/ubuntu/tempfiles/export_sparta_course_completion{}.csv'.format(tnow)
    with open(file_name, mode='w') as csv_file:
        writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
        writer.writerow(['Course ID', 'Course Name', 'No. of Learners Completed'])

        for course_data in course_list:
            writer.writerow([
                course_data['course_id'], course_data['course_name'], course_data['completed_count']
            ])

    if email_address:
        email = EmailMessage(
            'Coursebank - SPARTA Course Completion',
            'Attached file of SPARTA Course Completion (as of {})'.format(tnow),
            'no-reply-sparta-course-completion@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()


def export_sparta_user_logins(email_address=None):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    user_list = []
    for p in  SpartaProfile.objects.all():
        user_list.append({
            "username": p.user.username,
            "email": p.user.email,
            "name": p.user.profile.name,
            "last_login": p.user.last_login.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        })

    file_name = '/home/ubuntu/tempfiles/export_sparta_user_logins_{}.csv'.format(tnow)
    with open(file_name, mode='w') as csv_file:
        writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
        writer.writerow([
            'username',
            'email',
            'name',
            'last_login'
            ])

        for u in user_list:
            writer.writerow([
                u['username'],
                u['email'],
                u['name'],
                u['last_login'],
            ])

    if email_address:
        email = EmailMessage(
            'Coursebank - SPARTA User Logins',
            'Attached file of SPARTA User Logins (as of {})'.format(tnow),
            'no-reply-sparta-user-logins@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()


def export_sparta_student_module_timestamps(course_id, email_address=None):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    course_key = CourseKey.from_string(course_id)
    modules = StudentModule.objects.filter(course_id=course_key)
    enrollments = CourseEnrollment.objects.filter(
        course_id=course_key,
        is_active=True
    )
    profiles = SpartaProfile.objects.all()

    user_list = []
    for e in enrollments:
        if not profiles.filter(user=e.user).exists():
            continue

        student_modules = modules.filter(student=e.user)

        course_module = student_modules.filter(module_type='course').order_by('created').first()
        if course_module:
            earliest_created = course_module.created.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        else:
            earliest_created = None

        latest_student_module = student_modules.order_by('-modified').first()
        if latest_student_module:
            latest_modified = latest_student_module.modified.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        else:
            latest_modified = None

        cert = get_certificate_for_user(e.user.username, course_key)
        if cert is not None and cert['status'] == "downloadable":
            date_completed = cert['created'].strftime('%Y-%m-%dT%H:%M:%S.000Z')
        else:
            date_completed = None

        user_list.append({
            "username": e.user.username,
            "email": e.user.email,
            "earliest_created": earliest_created,
            "latest_modified": latest_modified,
            "date_completed": date_completed
        })

    file_name = '/home/ubuntu/tempfiles/export_sparta_activity_timestamps{}.csv'.format(tnow)
    with open(file_name, mode='w') as csv_file:
        writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
        writer.writerow([
            'username',
            'email',
            'earliest_created',
            'latest_modified',
            'date_completed'
            ])

        for u in user_list:
            writer.writerow([
                u['username'],
                u['email'],
                u['earliest_created'],
                u['latest_modified'],
                u['date_completed'],
            ])

    if email_address:
        email = EmailMessage(
            'Coursebank - SPARTA Activity Timestamps - {}'.format(course_id),
            'Attached file of SPARTA Activity Timestamps for course {} (as of {})'.format(course_id, tnow),
            'no-reply-sparta-activity-timestamps@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()


def get_course_graded_problems_progress(user, course_id):
    try:
        course_block_tree = get_course_outline_block_tree(user, course_id)
    except Exception as e:
        raise Exception("get_course_graded_problems_progress.ERROR: {}".format(str(e)))

    if not course_block_tree:
        raise Exception("get_course_graded_problems_progress.ERROR: Course outline missing X_X")

    total_problems = 0
    completed_problems = 0

    for section in course_block_tree.get('children', []):
        for subsection in section.get('children', []):
            for vertical in subsection.get('children', []):
                for unit in vertical.get('children', []):
                    if 'type@problem' in unit.get('id') and unit.get('graded'):
                        total_problems += 1
                    if unit.get('complete'):
                        completed_problems += 1

    return completed_problems, total_problems


def export_sparta_data_for_dashboard(email_address=None):
    """"""
    student_list = []

    for application in PathwayApplication.objects.all():
        user = application.profile.user
        student_id = user.id

        for course in application.pathway.courses.filter(is_active=True):
            course_id = course.course_id

            if any(d['COURSE'] == course_id and d['STUDENT_ID'] == student_id for d in student_list):
                continue

            try:
                eprofile = ExtendedSpartaProfile.objects.get(user=user)
                user_profile = user.profile
            except:
                municipality = region = None
            else:
                municipality = eprofile.municipality
                region = get_region_from_municipality(municipality)

            pathway_name = application.pathway.name
            application_status = application.get_status_display()

            try:
                course_key = CourseKey.from_string(course_id)
            except Exception as e:
                logger.info("export_sparta_data_for_dashboard.CourseKeyError: " + str(e))
                continue

            try:
                enrollment = CourseEnrollment.objects.get(course_id=course_key, user=user)
            except:
                enrollment_track = None
            else:
                enrollment_track = enrollment.mode

            verification_status = IDVerificationService.verification_status_for_user(user, enrollment_track)

            course_grade = CourseGradeFactory().read(user, get_course_by_id(course_key))
            grade_summary = course_grade.summary
            course_grade_percent = grade_summary['percent']

            completed_problems, total_problems = get_course_graded_problems_progress(user, course_id)
            if total_problems != 0:
                progress = completed_problems / total_problems
            else:
                progress = 0

            is_active = enrollment.is_active

            data = {}
            data['STUDENT_ID'] = student_id
            data['MUNICIPALITY'] = municipality
            data['REGION'] = region
            data['PATHWAY'] = pathway_name
            data['APPLICATION_STATUS'] = application_status
            data['ENROLLMENT_TRACK'] = enrollment_track
            data['VERIFICATION_STATUS'] = verification_status
            data['COURSE'] = course_id
            data['PROGRESS'] = progress
            data['GRADE'] = course_grade_percent
            data['IS_ACTIVE'] = is_active

            student_list.append(data)

    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
    file_name = '/home/ubuntu/tempfiles/export_sparta_data_for_dashboard_{}.csv'.format(tnow)
    with open(file_name, mode='w') as csv_file:
        writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
        writer.writerow([
            'STUDENT_ID',
            'MUNICIPALITY',
            'REGION',
            'PATHWAY',
            'APPLICATION_STATUS',
            'ENROLLMENT_TRACK',
            'VERIFICATION_STATUS',
            'COURSE',
            'PROGRESS',
            'GRADE',
            'IS_ACTIVE'
            ])

        for student in student_list:
            writer.writerow([
                student['STUDENT_ID'],
                student['MUNICIPALITY'],
                student['REGION'],
                student['PATHWAY'],
                student['APPLICATION_STATUS'],
                student['ENROLLMENT_TRACK'],
                student['VERIFICATION_STATUS'],
                student['COURSE'],
                student['PROGRESS'],
                student['GRADE'],
                student['IS_ACTIVE'],
            ])

    if email_address:
        email = EmailMessage(
            'Coursebank - SPARTA Data for Dashboard',
            'Attached file of SPARTA Data for Dashboard (as of {})'.format(tnow),
            'no-reply-sparta-data-for-dashboard@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()

def export_learner_pathway_progress(email_address=None, date_from=None, date_to=None):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    profiles = SpartaProfile.objects.prefetch_related('applications')

    datefrom_str = ""
    dateto_str = ""

    pathway_dict = {}
    for pathway in Pathway.objects.all():
        pathway_dict[pathway.name] = SpartaCourse.objects.filter(pathway=pathway).count()

    user_list = []
    for p in profiles:
        if date_from:
            applications = p.applications.filter(created_at__gte=date_from,status="AP")
            datefrom_str = date_from.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        if date_to:
            applications = p.applications.filter(created_at__lte=date_to,status="AP")
            dateto_str = date_to.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        if applications.exists():
            application = applications.order_by('created_at').first()

            total_count = pathway_dict[application.pathway.name]
            finished = 0

            for course in application.pathway.courses.all():
                course_key = CourseKey.from_string(course.course_id)

                cert = get_certificate_for_user(p.user.username, course_key)

                if cert is not None:
                    finished += 1

            user_list.append({
                "name": p.full_name,
                "username": p.user.username,
                "email": p.user.email,
                "pathway": application.pathway.name,
                "progress": str(finished) + " out of " + str(total_count)
            })
        else:
            user_list.append({
                "name": p.full_name,
                "username": p.user.username,
                "email": p.user.email,
                "pathway": "No Approved Application",
                "progress": "N/A"
            })

    file_name = '/home/ubuntu/tempfiles/export_learner_pathway_progress_{}.csv'.format(tnow)
    with open(file_name, mode='w') as csv_file:
        writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
        writer.writerow([
            'name',
            'username',
            'email',
            'pathway',
            'progress'
            ])

        for u in user_list:
            writer.writerow([
                u['name'],
                u['username'],
                u['email'],
                u['pathway'],
                u['progress'],
            ])

    if datefrom_str or dateto_str:
        date_range = ' for date range: {} to {}'.format(datefrom_str, dateto_str)
    else:
        date_range = ""

    if email_address:
        email = EmailMessage(
            'Coursebank - SPARTA Learner Pathway Progress',
            'Attached file of SPARTA Learner Pathway Progress (as of {})'.format(date_range),
            'no-reply-sparta-user-logins@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()

def export_learner_account_information(course_id, email_address=None):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
    course_key = CourseKey.from_string(course_id)
    users = User.objects.filter(courseenrollment__course__id=course_key).select_related('sparta_profile').prefetch_related('courseenrollment_set')

    user_list = []
    for u in users:
        if u.is_active == True:
            acc_status = "Activated"

            try:
                profile = u.sparta_profile
                applications = profile.applications.all()

                if applications.exists():
                    application = applications.order_by('-created_at').last()
                    sparta_status = application.status
                    pathway = application.pathway.name

                else:
                    sparta_status = "No Pathway Application"
                    pathway = ""

            except SpartaProfile.DoesNotExist:
                sparta_status = "No SPARTA Account"
                pathway = ""

            try:
                enrollments = u.courseenrollment_set.filter(course__id=course_key)
                try:
                    cert = get_certificate_for_user(u.username, course_key)
                except Exception as e:
                    raise Exception("Cert error: {}".format(str(e)))

                try:
                    grade = CourseGradeFactory().read(u, course_key=course_key)
                except Exception as e:
                    raise Exception("Grade error: {}".format(str(e)))

                if cert is not None:
                    course_status = "Complete"
                    final_grade = str(grade.summary.get('percent', 0.0))
                    cert_status = "Generated"

                elif cert is None and enrollments.exists():
                    course_status = "In Progress"
                    final_grade = str(grade.summary.get('percent', 0.0))
                    cert_status = ""

            except CourseEnrollment.DoesNotExist:
                course_status = "Not Enrolled"
                final_grade = ""
                cert_status = ""
        else:
            acc_status = "Not Activated"
            sparta_status = ""
            pathway = ""
            course_status = ""
            final_grade = ""
            cert_status = ""

        user_list.append({
            "username": u.username,
            "email": u.email,
            "account status": acc_status,
            "sparta status": sparta_status,
            "pathway": pathway,
            "course status": course_status,
            "final grade": final_grade,
            "cert status": cert_status
        })



    file_name = '/home/ubuntu/tempfiles/export_learner_account_information_{}.csv'.format(tnow)
    with open(file_name, mode='w') as csv_file:
        writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
        writer.writerow([
            'Username',
            'Email',
            'Account Status',
            'SPARTA Status',
            'Pathway',
            'Course Status',
            'Grade',
            'Certificate',
            ])

        for u in user_list:
            writer.writerow([
                u['username'],
                u['email'],
                u['account status'],
                u['sparta status'],
                u['pathway'],
                u['course status'],
                u['final grade'],
                u['cert status'],
            ])

    if email_address:
        email = EmailMessage(
            'Coursebank - Learner Account Information',
            'Attached file of Learner Account Information for {} (as of {})'.format(course_key,tnow),
            'no-reply-sparta-user-logins@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()

def export_six_month_access_users(course_id, email_address=None):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
    course_key = CourseKey.from_string(course_id)
    users = User.objects.filter(courseenrollment__course__id=course_key).select_related('sparta_profile').prefetch_related('sparta_profile__applications')
    sec = 183*24*60*60

    tnow = timezone.now()
    date_filter = tnow - timedelta(seconds=sec)

    user_list = []
    for u in users:
        cert = get_certificate_for_user(u.username, course_key)
        if cert is not None:
            continue

        enrollments = CourseEnrollment.objects.filter(
            course_id=course_key,
            is_active=True,
            created__lt=date_filter,
        )
        try:
            profile = u.sparta_profile

        except SpartaProfile.DoesNotExist:
            continue

        applications = profile.applications.filter(status="AP")

        if applications.exists():
            application = applications.order_by('-created_at').last()
            pathway = application.pathway.name

        for e in enrollments:
            reenrollments = SpartaReEnrollment.objects.filter(enrollment=e)
            if reenrollments.exists():
                lastest_reenrollment = reenrollments.order_by('-reenroll_date').first()
                check_date = lastest_reenrollment.reenroll_date
            else:
                check_date = e.created

            tdelta = tnow - check_date

            if tdelta.seconds >= sec and cert is None:
                user_list.append({
                    "name": e.user.name,
                    "email": e.user.email,
                    "username": e.user.username,
                    "pathway": pathway,
                    "access date": check_date.strftime("%Y-%m-%d"),
                })

    file_name = '/home/ubuntu/tempfiles/export_six_month_access_users_{}.csv'.format(tnow)
    with open(file_name, mode='w') as csv_file:
        writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
        writer.writerow([
            'Name',
            'Email',
            'Username',
            'Pathway',
            'Initial Access Date'
            ])

        for u in user_list:
            writer.writerow([
                u['name'],
                u['email'],
                u['username'],
                u['pathway'],
                u['access date'],
            ])

    if email_address:
        email = EmailMessage(
            'Coursebank - Six Month Access List',
            'Attached file of Six Month Access List for {} (as of {})'.format(course_key,tnow),
            'no-reply-sparta-user-logins@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()

def export_three_month_inactive_users(course_id, email_address=None):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
    course_key = CourseKey.from_string(course_id)
    users = User.objects.filter(courseenrollment__course__id=course_key).select_related('sparta_profile').prefetch_related('sparta_profile__applications')
    sec = 92*24*60*60

    tnow = timezone.now()
    date_filter = tnow - timedelta(seconds=sec)

    user_list = []
    for u in users:
        cert = get_certificate_for_user(u.username, course_key)
        if cert is not None:
            continue

        enrollments = CourseEnrollment.objects.filter(
            course_id=course_key,
            is_active=True,
            created__lt=date_filter,
        )
        try:
            profile = u.sparta_profile

        except SpartaProfile.DoesNotExist:
            continue

        applications = profile.applications.filter(status="AP")

        if applications.exists():
            application = applications.order_by('-created_at').last()
            pathway = application.pathway.name

        check_date = u.last_login

        tdelta = tnow - check_date

        if tdelta.seconds >= sec and cert is None:
            user_list.append({
                "name": u.profile.name,
                "email": u.email,
                "username": u.username,
                "pathway": pathway,
                "last login": u.last_login.strftime("%Y-%m-%d"),
            })

    file_name = '/home/ubuntu/tempfiles/export_three_month_inactive_users_{}.csv'.format(tnow)
    with open(file_name, mode='w') as csv_file:
        writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
        writer.writerow([
            'Name',
            'Email',
            'Username',
            'Pathway',
            'Last Login Date'
            ])

        for u in user_list:
            writer.writerow([
                u['name'],
                u['email'],
                u['username'],
                u['pathway'],
                u['last login'],
            ])

    if email_address:
        email = EmailMessage(
            'Coursebank - Three Month Inactive List',
            'Attached file of Three Month Inactive List for {} (as of {})'.format(course_key,tnow),
            'no-reply-sparta-user-logins@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()

def export_graduation_candidates(path_way=None, email_address=None, date_from=None, date_to=None):
    """"""
    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    profiles = SpartaProfile.objects.prefetch_related('applications')
    core_courses = []
    elective_courses = []
    certdate_list =[]

    if path_way:
      if path_way == 1:
          pathway_name = "Data Associate"
      elif path_way == 2:
          pathway_name = "Data Scientist"
      elif path_way == 3:
          pathway_name = "Data Engineer"
      elif path_way == 4:
          pathway_name = "Data Steward"
      elif path_way == 5:
          pathway_name = "Data Analyst"
      elif path_way == 6:
          pathway_name = "Analytics Manager"

      if path_way >= 1 and path_way <= 6:
         with connection.cursor() as cursor:
               cursor.execute("Select sparta_pages_spartacourse.course_id from sparta_pages_spartacourse INNER JOIN sparta_pages_coursegroup where sparta_pages_spartacourse.group_id=sparta_pages_coursegroup.id AND sparta_pages_coursegroup.type='CO' AND sparta_pages_spartacourse.pathway_id = %s", [path_way])
               corecourse = cursor.fetchall()
         with connection.cursor() as cursor:
               cursor.execute("Select sparta_pages_spartacourse.course_id from sparta_pages_spartacourse INNER JOIN sparta_pages_coursegroup where sparta_pages_spartacourse.group_id=sparta_pages_coursegroup.id AND sparta_pages_coursegroup.type='EL' AND sparta_pages_spartacourse.pathway_id = %s", [path_way])
               electcourse = cursor.fetchall()
         with connection.cursor() as cursor:
               cursor.execute("Select complete_at_least from sparta_pages_coursegroup where type='EL' AND pathway_id = %s", [path_way])
               data = cursor.fetchone()
               elect_total = data[0]

         for data in corecourse:
             result = data[0]
             core_courses.append(result)
         for data in electcourse:
             result = data[0]
             elective_courses.append(result)

         core_total = len(core_courses)



    else:
       profiles = None

    datefrom_str = ""
    dateto_str = ""

    pathway_dict = {}
    for pathway in Pathway.objects.all():
        pathway_dict[pathway.name] = SpartaCourse.objects.filter(pathway=pathway).count()

    user_list = []
    for p in profiles:
        if date_from:
            applications = p.applications.filter(created_at__gte=date_from,status="AP")
            datefrom_str = date_from.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        if date_to:
            applications = p.applications.filter(created_at__lte=date_to,status="AP")
            dateto_str = date_to.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        if applications.exists():
            application = applications.order_by('created_at').first()

            total_count = pathway_dict[application.pathway.name]
            finished = 0
            core_count = 0
            elect_count = 0

            for course in application.pathway.courses.all():
                course_key = CourseKey.from_string(course.course_id)

                cert = get_certificate_for_user(p.user.username, course_key)

                if cert is not None:
                    finished += 1

                if path_way:
                    for pathcourse in core_courses:
                        if unicode(course_key) == unicode(pathcourse) and cert is not None:
                           date_completed = cert['created'].strftime('%Y-%m-%dT%H:%M:%S.000Z')
                           certdate_list.append(date_completed)
                           core_count += 1

                    for pathcourse in elective_courses:
                        if unicode(course_key) == unicode(pathcourse) and cert is not None:
                           date_completed = cert['created'].strftime('%Y-%m-%dT%H:%M:%S.000Z')
                           certdate_list.append(date_completed)
                           elect_count += 1

            certdate_list.sort(reverse=True)

            if application.pathway.name == pathway_name and core_count == core_total and elect_count >= elect_total:
               user_list.append({
                   "name": p.full_name,
                   "username": p.user.username,
                   "email": p.user.email,
                   "pathway": application.pathway.name,
                   "created": p.created_at,
                   "progress": str(finished) + " out of " + str(total_count),
                   "core_progress": str(core_count) + "out of" + str(core_total),
                   "elective_progress": str(elect_count) + "out of" + str(elect_total),
                   "completion_date": certdate_list[0]
            })
               del certdate_list[:]
            else:
               del certdate_list[:]

    file_name = '/home/ubuntu/tempfiles/export_learner_pathway_progress_{}.csv'.format(tnow)
    with open(file_name, mode='w') as csv_file:
        writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
        writer.writerow([
            'name',
            'username',
            'email',
            'pathway',
            'created',
            'progress',
            'core_progress',
            'elective_progress',
            'completion_date'
            ])

        for u in user_list:
            writer.writerow([
                u['name'],
                u['username'],
                u['email'],
                u['pathway'],
                u['created'],
                u['progress'],
                u['core_progress'],
                u['elective_progress'],
                u['completion_date'],
            ])

    if datefrom_str or dateto_str:
        date_range = ' for date range: {} to {}'.format(datefrom_str, dateto_str)
    else:
        date_range = ""

    if email_address:
        email = EmailMessage(
            'Coursebank - SPARTA Learner Pathway Progress',
            'Attached file of SPARTA Graduation Candidates (as of {})'.format(date_range),
            'no-reply-sparta-user-logins@coursebank.ph',
            [email_address,],
        )
        email.attach_file(file_name)
        email.send()
