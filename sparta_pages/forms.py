from django import forms
from django.forms import formset_factory

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
    # first_timer = forms.BooleanField(label='First Timer?', required=False, initial=False)


class EducationProfileForm(forms.ModelForm):
    """
    """
    started_at = forms.DateField(
        widget=forms.SelectDateWidget(
            empty_label=("Choose Year", "Choose Month", "Choose Day"),
            ),
        )
    graduated_at = forms.DateField(
        widget=forms.SelectDateWidget(
            empty_label=("Choose Year", "Choose Month", "Choose Day"),
            ),
        )
    class Meta:
        model = EducationProfile
        fields = [
            'degree', 'course', 'school', 'address',
        ]


class EmploymentProfileForm(forms.ModelForm):
    """
    """
    started_at = forms.DateField(
        widget=forms.SelectDateWidget(
            empty_label=("Choose Year", "Choose Month", "Choose Day"),
            ),
        )
    ended_at = forms.DateField(
        widget=forms.SelectDateWidget(
            empty_label=("Choose Year", "Choose Month", "Choose Day"),
            ),
        )
    class Meta:
        model = EmploymentProfile
        fields = [
            'affiliation', 'occupation', 'designation',
            'employer', 'address',
        ]


class TrainingProfileForm(forms.ModelForm):
    """
    """
    started_at = forms.DateField(
        widget=forms.SelectDateWidget(
            empty_label=("Choose Year", "Choose Month", "Choose Day"),
            ),
        )
    ended_at = forms.DateField(
        widget=forms.SelectDateWidget(
            empty_label=("Choose Year", "Choose Month", "Choose Day"),
            ),
        )
    class Meta:
        model = TrainingProfile
        fields = [
            'title', 'organizer', 'address',
        ]


EducationProfileFormset = formset_factory(EducationProfileForm, extra=1)
EmploymentProfileFormset = formset_factory(EmploymentProfileForm, extra=1)
TrainingProfileFormset = formset_factory(TrainingProfileForm, extra=1)


class PathwayApplicationForm(forms.ModelForm):
    """
    """
    class Meta:
        model = PathwayApplication
        fields = [
            'pathway',
        ]
