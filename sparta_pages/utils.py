import csv
from datetime import datetime

from django.core.mail import send_mail, EmailMessage

from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment

from .models import Pathway, SpartaCourse, SpartaProfile, EducationProfile, EmploymentProfile, TrainingProfile, PathwayApplication, Event


def manage_pathway_applications():
    """"""
    for app in PathwayApplication.objects.filter(status="PE"):
        app.approve()

def manage_sparta_enrollments():
    student_list = []
    for app in PathwayApplication.objects.filter(status="AP"):
        user_enrollments = CourseEnrollment.objects.enrollments_for_user(app.profile.user)
        course_enrollment = user_enrollments.filter(course_id=course_key).filter(mode='verified')
        if course_enrollment.exists():
            continue
        else:
            student_list.append({'user': app.profile.user, 'pathway': app.pathway})

    tnow = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
    file_name = '/home/ubuntu/files/sparta_applications_file_{}.csv'.format(tnow)
    with open(file_name, mode='w') as apps_file:
        writer = csv.writer(apps_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        writer.writerow(['User_ID', 'Username', 'Email', 'Pathway_ID', 'Pathway_Name'])
        for student in student_list:
            user = student['user']
            pathway = student['pathway']
            writer.writerow([user.id, user.username, user.email, pathway.id, pathway.name])

    email = EmailMessage(
        'Coursebank - SPARTA Applications - {}'.format(tnow),
        'Attached file of SPARTA Applications - {}'.format(tnow),
        'no-reply-sparta-applications@coursebank.ph',
        ['learn@coursebank.ph',],
    )
    email.attach_file(file_name)
    email.send()
