from django.conf import settings
from django.db import models
from django.urls import reverse

from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment
from rest_framework.authtoken.models import Token as BaseToken

# Backwards compatible settings.AUTH_USER_MODEL
USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class Pathway(models.Model):
    """
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    short_description = models.CharField(max_length=255, blank=True, default="")
    long_description = models.TextField(blank=True, default="")
    card_description = models.TextField(blank=True, default="")
    image_url = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name_plural = "1. Pathways"

    def get_absolute_url(self):
        return reverse('sparta-pathway', kwargs={'slug': self.slug})

    def __str__(self):
        return self.name


class SpartaCourse(models.Model):
    """
    """
    course_id = models.CharField(max_length=255, null=True, blank=True)
    pathway = models.ForeignKey(
        'Pathway',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="courses"
    )
    short_description = models.CharField(max_length=255, blank=True, default="")
    long_description = models.TextField(blank=True, default="")
    image_url = models.CharField(max_length=255, default="https://coursebank-static-assets.s3-ap-northeast-1.amazonaws.com/sparta+black.png")
    order = models.PositiveSmallIntegerField(default=0)
    display_order = models.CharField(max_length=255, blank=True, default="")
    group = models.ForeignKey(
        'CourseGroup',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="courses"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name_plural = "2. Sparta Courses"

    def __str__(self):
        return "{}: {}".format(self.pathway.name, self.course_id)

    @property
    def related_courses(self):
        pass


class CourseGroup(models.Model):
    """
    """
    CORE = "CO"
    ELECTIVE = "EL"
    GROUP_TYPE = (
        (CORE, "Core"),
        (ELECTIVE, "Elective"),
    )
    type = models.CharField(max_length=2, choices=GROUP_TYPE, default=CORE)
    name = models.CharField(max_length=255, null=True, blank=True)
    pathway = models.ForeignKey(
        'Pathway',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="groups"
    )
    complete_at_least = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "2.2 Course Groups"

    def __str__(self):
        return self.name or "{}: {}".format(self.pathway.name, self.type)


class SpartaProfile(models.Model):
    """
    """
    user = models.OneToOneField(
        USER_MODEL,
        on_delete=models.CASCADE,
        help_text='User referred with this SPARTA User',
        related_name='sparta_profile')
    proof_of_education = models.URLField(max_length=255)
    proof_of_agreement = models.URLField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    first_timer = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "3. Sparta Profiles"

    def __str__(self):
        return self.user.username

    def deactivate(self):
        if self.is_active:
            self.is_active = False
            self.save()


class ExtendedSpartaProfile(models.Model):
    """
    """
    PRIVATE = "PR"
    GOVERNMENT = "GO"
    FACULTY = "FA"
    STUDENT = "ST"
    AFFILIATION_CHOICES = (
        (PRIVATE, "Private" ),
        (GOVERNMENT, "Government"),
        (FACULTY, "Academe/Faculty"),
        (STUDENT, "Academe/Student"),
    )

    DOCTORATE = "DO"
    MASTERS = "MA"
    BACHELORS = "BA"
    ASSOCIATE = "AS"
    SENIOR_HIGH = "SH"
    HIGH_SCHOOL = "HS"
    JUNIOR_HIGH = "JH"
    ELEMENTARY = "EL"
    NO_FORMAL = "NF"
    OTHER_EDUC = "OE"
    ATTAINMENT_CHOICES = (
        (ELEMENTARY, "Elementary/Primary School"),
        (JUNIOR_HIGH, "Junior Secondary/Junior High/Middle School"),
        (SENIOR_HIGH, "Senior High School"),
        (HIGH_SCHOOL, "Secondary/High School"),
        (ASSOCIATE, "Associate Degree"),
        (BACHELORS, "Bachelor's Degree"),
        (MASTERS, "Master's or Professional Degree"),
        (DOCTORATE, "Doctorate"),
        (OTHER_EDUC, "Other Education"),
        (NO_FORMAL, "No Formal Education"),
    )

    YES_MASTER = "YM"
    YES_DOCTOR = "YD"
    NO_DEGREE = "ND"
    GRAD_CHOICES = (
        (NO_DEGREE, "No."),
        (YES_MASTER, "Yes, a Master's degree"),
        (YES_DOCTOR, "Yes, a Doctorate degree."),
    )

    user = models.OneToOneField(
        USER_MODEL,
        on_delete=models.CASCADE,
        help_text='User referred with this SPARTA User',
        related_name='extended_sparta_profile')
    affiliation = models.CharField(max_length=2, choices=AFFILIATION_CHOICES, default=PRIVATE)
    attainment = models.CharField(max_length=2, choices=ATTAINMENT_CHOICES, default=ELEMENTARY)
    other_attain = models.CharField(max_length=255, null=True, blank=True)
    is_employed = models.BooleanField(default=False)
    grad_degree = models.CharField(max_length=2, choices=GRAD_CHOICES, default=NO_DEGREE)


class PathwayApplication(models.Model):
    """
    """
    PENDING = "PE"
    APPROVED = "AP"
    DENIED = "DE"
    WITHDRAWN = "WE"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (DENIED, "Denied"),
        (WITHDRAWN, "Withdrawn")
    )
    pathway = models.ForeignKey(
        'Pathway',
        on_delete=models.CASCADE,
        related_name="applications"
        )
    profile = models.ForeignKey(
        'SpartaProfile',
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name="sparta profile"
        )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default=PENDING)

    class Meta:
        verbose_name_plural = "4. Pathway Applications"

    def __str__(self):
        return "{}: {}".format(self.profile.user.username, self.pathway.name)

    def withdraw(self):
        if self.status != self.WITHDRAWN:
            self.status = self.WITHDRAWN
            self.save()

    def pend(self):
        if self.status != self.PENDING:
            self.status = self.PENDING
            self.save()

    def approve(self):
        if self.status != self.APPROVED:
            self.status = self.APPROVED
            self.save()

    def deny(self):
        if self.status != self.DENIED:
            self.status = self.DENIED
            self.save()


class EducationProfile(models.Model):
    """
    """
    SECONDARY = "SE"
    ASSOCIATE = "AS"
    BACHELOR = "BA"
    MASTER = "MA"
    DOCTORAL = "DO"
    DEGREE_CHOICES = (
        (SECONDARY, "Secondary Education"),
        (ASSOCIATE, "Associate Degree"),
        (BACHELOR, "Bachelor's Degree"),
        (MASTER, "Master's Degree"),
        (DOCTORAL, "Doctoral Degree"),
    )
    profile = models.ForeignKey(
        'SpartaProfile',
        on_delete=models.CASCADE,
        related_name="education_profiles",
        verbose_name="sparta profile"
        )
    degree = models.CharField(max_length=2, choices=DEGREE_CHOICES, null=True, blank=True)
    course = models.CharField(max_length=255)
    school = models.CharField(max_length=255)
    address = models.TextField()
    started_at = models.DateField()
    graduated_at = models.DateField()

    class Meta:
        verbose_name_plural = "5. Education Profiles"

    def __str__(self):
        return self.profile.user.username


class EmploymentProfile(models.Model):
    """
    """
    NOT_APPLICABLE = "NA"
    PRIVATE = "PR"
    GOVERNMENT = "GO"
    ACADEME = "AC"
    AFF_CHOICES = (
        (NOT_APPLICABLE, "Not Applicable"),
        (PRIVATE, "Private"),
        (GOVERNMENT, "Government"),
        (ACADEME, "Academe"),
    )
    profile = models.ForeignKey(
        'SpartaProfile',
        on_delete=models.CASCADE,
        related_name="employment_profiles",
        verbose_name="sparta profile"
        )
    affiliation = models.CharField(max_length=2, choices=AFF_CHOICES, null=True, blank=True)
    occupation = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    employer = models.CharField(max_length=255)
    address = models.TextField()
    started_at = models.DateField()
    ended_at = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "6. Employment Profiles"

    def __str__(self):
        return self.profile.user.username

    @property
    def print_ended_at(self):
        if self.ended_at:
            return self.ended_at
        else:
            return "Present"


class TrainingProfile(models.Model):
    """
    """
    profile = models.ForeignKey(
        'SpartaProfile',
        on_delete=models.CASCADE,
        related_name="training_profiles",
        verbose_name="sparta profile"
        )
    title = models.CharField(max_length=255)
    organizer = models.CharField(max_length=255)
    address = models.TextField()
    started_at = models.DateField()
    ended_at = models.DateField()

    class Meta:
        verbose_name_plural = "7. Training Profiles"

    def __str__(self):
        return self.profile.user.username


class Event(models.Model):
    """
    """
    event = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    profile = models.ForeignKey(
        'SpartaProfile',
        on_delete=models.CASCADE,
        verbose_name="sparta profile"
        )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "8. Events"

    def __str__(self):
        return self.event


class APIToken(BaseToken):
    """
    """
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name = "API Token"
        verbose_name_plural = "API Tokens"


class SpartaCoupon(models.Model):
    """
    Model to record coupons for a course.
    Strictly used for record purposes and is not connected to ecommerce logic.
    Hence, coupon might already be used.
    """
    code = models.CharField(max_length=255, unique=True)
    course_id = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code

    def get_related_pathways(self):
        pathways = Pathway.objects.none()
        for c in SpartaCourse.objects.filter(course_id=self.course_id):
            pathways |= c.pathway
        return pathways

    def get_related_sparta_courses(self):
        return SpartaCourse.objects.filter(course_id=self.course_id)

    def get_records(self):
        return self.records.all()


class StudentCouponRecord(models.Model):
    """
    Model to record student coupon for a course.
    """
    profile = models.ForeignKey(
        'SpartaProfile',
        on_delete=models.CASCADE,
        related_name="coupons",
        )
    coupon = models.ForeignKey(
        'SpartaCoupon',
        on_delete=models.CASCADE,
        related_name="records",
        )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{}: {}".format(self.profile.user.username, self.coupon.code)

    @property
    def is_user_verified(self):
        course_key = CourseKey.from_string(self.coupon.course_id)
        enrollment = CourseEnrollment.get_enrollment(self.profile.user, course_key)
        if enrollment:
            return enrollment.is_active and enrollment.mode == "verified"
        return False
