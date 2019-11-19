from django.db import models
from django.urls import reverse


class Pathway(models.Model):
    """
    """
    name = model.CharField(max_length=255)
    slug = model.SlugField(max_length=255)
    short_description = models.CharField(max_length=255, blank=True, default="")
    long_description = models.TextField(blank=True, default="")
    image_url = model.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

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
    image_url = model.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.course_id
