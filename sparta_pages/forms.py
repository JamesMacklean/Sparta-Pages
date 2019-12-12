from django import forms

from .models import (
    SpartaProfile,
    EducationProfile,
    EmploymentProfile,
    TrainingProfile,
    PathwayApplication
)


class SpartaProfileForm(forms.Form):
    """
    """
    proof_of_education_file = forms.ImageField(widget=forms.FileInput, required=True,label='Proof of Education',help_text='Select a clear image of your Proof of Education that is no more than 2MB.')
    proof_of_agreement_file = forms.ImageField(widget=forms.FileInput, required=True,label='Proof of Agreement',help_text='Select a clear image of your signed Proof of Agreement that is no more than 2MB.')
    first_timer = forms.BooleanField(label='First Timer?', required=False, initial=False)


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
            'pathway',
        ]
