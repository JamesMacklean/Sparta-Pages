import csv
import unicodecsv

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

UserModel = get_user_model()

from rest_framework import status
from rest_framework.test import APITestCase

from sparta_pages.models import (
    Pathway,
    SpartaCourse,
    SpartaProfile,
    PathwayApplication,
    SpartaCoupon,
    StudentCouponRecord,
)
from sparta_pages.utils import assign_coupons_to_single_student, assign_coupons_to_students


def create_user(username):
    user = UserModel(username=username)
    user.set_unusable_password()
    user.save()
    return user

class CouponTests(TestCase):
    """
    """

    def setUp(self):
        """"""
        self.user1 = create_user("testuser1")
        self.user2 = create_user("testuser2")
        self.user3 = create_user("testuser3")
        self.user4 = create_user("testuser4")
        self.user5 = create_user("testuser5")

        self.profile1 = SpartaProfile.objects.create(user=self.user1, proof_of_education="N/A")
        self.profile2 = SpartaProfile.objects.create(user=self.user2, proof_of_education="N/A")
        self.profile3 = SpartaProfile.objects.create(user=self.user3, proof_of_education="N/A")
        self.profile4 = SpartaProfile.objects.create(user=self.user4, proof_of_education="N/A")
        self.profile5 = SpartaProfile.objects.create(user=self.user5, proof_of_education="N/A")

        self.pathway1 = Pathway.objects.create(name="Test Pathway 1", slug="pathway-1", image_url="N/A")

        self.course11 = SpartaCourse.objects.create(pathway=self.pathway1, course_id="test-course-11")
        SpartaCoupon.objects.create(code="test-code-111", course_id=self.course11.course_id)
        SpartaCoupon.objects.create(code="test-code-112", course_id=self.course11.course_id)
        SpartaCoupon.objects.create(code="test-code-113", course_id=self.course11.course_id)
 
        self.course12 = SpartaCourse.objects.create(pathway=self.pathway1, course_id="test-course-12")
        SpartaCoupon.objects.create(code="test-code-121", course_id=self.course12.course_id)
        SpartaCoupon.objects.create(code="test-code-122", course_id=self.course12.course_id)
        SpartaCoupon.objects.create(code="test-code-123", course_id=self.course12.course_id)

        self.course13 = SpartaCourse.objects.create(pathway=self.pathway1, course_id="test-course-13")
        SpartaCoupon.objects.create(code="test-code-131", course_id=self.course13.course_id)
        SpartaCoupon.objects.create(code="test-code-132", course_id=self.course13.course_id)
        SpartaCoupon.objects.create(code="test-code-133", course_id=self.course13.course_id)

        self.course_list1 = [self.course11.course_id, self.course12.course_id, self.course13.course_id]

        self.pathway2 = Pathway.objects.create(name="Test Pathway 2", slug="pathway-2", image_url="N/A")

        self.course21 = SpartaCourse.objects.create(pathway=self.pathway2, course_id="test-course-21")
        SpartaCoupon.objects.create(code="test-code-211", course_id=self.course21.course_id)
        SpartaCoupon.objects.create(code="test-code-212", course_id=self.course21.course_id)
        SpartaCoupon.objects.create(code="test-code-213", course_id=self.course21.course_id)

        self.course22 = SpartaCourse.objects.create(pathway=self.pathway2, course_id="test-course-22")
        SpartaCoupon.objects.create(code="test-code-221", course_id=self.course22.course_id)
        SpartaCoupon.objects.create(code="test-code-222", course_id=self.course22.course_id)
        SpartaCoupon.objects.create(code="test-code-223", course_id=self.course22.course_id)

        self.course23 = SpartaCourse.objects.create(pathway=self.pathway2, course_id="test-course-23")
        SpartaCoupon.objects.create(code="test-code-231", course_id=self.course23.course_id)
        SpartaCoupon.objects.create(code="test-code-232", course_id=self.course23.course_id)
        SpartaCoupon.objects.create(code="test-code-233", course_id=self.course23.course_id)

        self.course_list2 = [self.course21.course_id, self.course22.course_id, self.course23.course_id]

        self.couponsfilepath = "/home/ubuntu/tempfiles/testcouponsfilefortesting.csv"
        with open(self.couponsfilepath, mode='w') as csv_file:
            writer = unicodecsv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,  encoding='utf-8')
            writer.writerow(['code', 'course_id'])
            for course in SpartaCourse.objects.all():
                for i in range(0,2):
                    code = "code-{}-{}".format(course.course_id, i)
                    writer.writerow([code, course.course_id])

        self.application11 = PathwayApplication.objects.create(profile=self.profile1, pathway=self.pathway1, status=PathwayApplication.APPROVED)
        self.application12 = PathwayApplication.objects.create(profile=self.profile1, pathway=self.pathway2, status=PathwayApplication.APPROVED)
        
        self.application21 = PathwayApplication.objects.create(profile=self.profile2, pathway=self.pathway1, status=PathwayApplication.APPROVED)
        self.application22 = PathwayApplication.objects.create(profile=self.profile2, pathway=self.pathway2, status=PathwayApplication.DENIED)

        self.application31 = PathwayApplication.objects.create(profile=self.profile3, pathway=self.pathway1, status=PathwayApplication.APPROVED)
        self.application32 = PathwayApplication.objects.create(profile=self.profile3, pathway=self.pathway2, status=PathwayApplication.PENDING)
        
        self.application41 = PathwayApplication.objects.create(profile=self.profile4, pathway=self.pathway1, status=PathwayApplication.PENDING)        
        self.application42 = PathwayApplication.objects.create(profile=self.profile4, pathway=self.pathway2, status=PathwayApplication.APPROVED)        

        self.application51 = PathwayApplication.objects.create(profile=self.profile5, pathway=self.pathway1, status=PathwayApplication.WITHDRAWN)        
        self.application52 = PathwayApplication.objects.create(profile=self.profile5, pathway=self.pathway2, status=PathwayApplication.APPROVED)        
    
    def test_migrate(self):
        out = StringIO()
        call_command(
            'migrate_sparta_coupons',
            '--coupons-file={}'.format(self.couponsfilepath),
            stdout=out)
        self.assertIn('Successfully updated', out.getvalue())

    def test_single_student(self):
        assign_coupons_to_single_student(self.profile1)
        self.assertTrue(StudentCouponRecord.objects.filter(profile=self.profile1).exists())

    def test_all_students(self):
        assign_coupons_to_students()
        self.assertEqual(
            StudentCouponRecord.objects.filter(coupon__course_id__in=self.course_list1).count(),
            PathwayApplication.objects.filter(pathway=self.pathway1, status=PathwayApplication.APPROVED).count()
        )
        self.assertEqual(
            StudentCouponRecord.objects.filter(coupon__course_id__in=self.course_list2).count(),
            PathwayApplication.objects.filter(pathway=self.pathway2, status=PathwayApplication.APPROVED).count()
        )
