from django import forms

from .models import (
    SpartaProfile,
    EducationProfile,
    EmploymentProfile,
    TrainingProfile,
    PathwayApplication
)


class SpartaProfileForm(forms.ModelForm):
    """
    """
    class Meta:
        model = SpartaProfile
        fields = [
            'proof_of_identity', 'proof_of_education', 'proof_of_agreement', 'first_timer'
        ]


class EducationProfileForm(forms.ModelForm):
    """
    """
    class Meta:
        model = EducationProfile
        fields = [
            'degree', 'course', 'school', 'address', 'started_at', 'graduated_at'
        ]


class EmploymentProfileForm(forms.ModelForm):
    """
    """
    class Meta:
        model = EmploymentProfile
        fields = [
            'affiliation', 'occupation', 'designation',
            'employer', 'address', 'started_at', 'ended_at'
        ]


class TrainingProfileForm(forms.ModelForm):
    """
    """
    class Meta:
        model = TrainingProfile
        fields = [
            'title', 'organizer', 'address',
            'started_at', 'ended_at'
        ]


class PathwayApplicationForm(forms.ModelForm):
    """
    """
    class Meta:
        model = PathwayApplication
        fields = [
            'pathway', 'profile', 'status'
        ]
