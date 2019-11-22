from django.db import models
from django.urls import reverse


class Pathway(models.Model):
    """
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    short_description = models.CharField(max_length=255, blank=True, default="")
    long_description = models.TextField(blank=True, default="")
    image_url = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

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
        return self.course_id
