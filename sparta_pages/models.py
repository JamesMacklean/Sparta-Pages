from django.conf import settings
from django.db import models
from django.urls import reverse

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

    def get_absolute_url(self):
        return reverse('sparta-pathway', kwargs={'slug': self.slug})

    def __str__(self):
        return self.name

    @property
    def courses(self):
        pass


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
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return "{}: {}".format(self.pathway.name, self.course_id)

    @property
    def related_courses(self):
        pass


class SpartaProfile(models.Model):
    """
    """
    user = models.OneToOneField(
        USER_MODEL,
        on_delete=models.CASCADE,
        help_text='User referred with this SPARTA User',
        related_name='sparta_profile')
    proof_of_education = models.URLField(max_length=255)
    proof_of_agreement = models.URLField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    first_timer = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username

    @property
    def pathwaysapproved(self):
        pass

    @property
    def coursesapplied(self):
        pass

    @property
    def enrollmentcodes(self):
        pass

    @property
    def coursesenrolled(self):
        pass


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

    def __str__(self):
        return self.profile.user.username


class EmploymentProfile(models.Model):
    """
    """
    PRIVATE = "PR"
    GOVERNMENT = "GO"
    ACADEME = "AC"
    AFF_CHOICES = (
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

    def __str__(self):
        return self.profile.user.username


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

    def __str__(self):
        return self.event
