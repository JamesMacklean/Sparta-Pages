from datetime import datetime
from datetime import date

from django import forms
from django.forms import formset_factory
from django.utils import timezone

from .models import (
    SpartaProfile,
    ExtendedSpartaProfile,
    EducationProfile,
    EmploymentProfile,
    TrainingProfile,
    PathwayApplication
)


class SpartaProfileForm(forms.Form):
    """
    """
    proof_of_education_file = forms.ImageField(widget=forms.FileInput, required=True,label='Proof of Education',help_text='Select a clear image of your Proof of Education that is no more than 2MB.')
    tos_yes = forms.BooleanField(required=True)
    citizenship = forms.BooleanField(required=True)
    discovery = forms.ChoiceField(required=True, choices=SpartaProfile.DISCOVERY_CHOICES)
    org = forms.ChoiceField(required=True, choices=SpartaProfile.ORG_CHOICES, widget=forms.Select(attrs={"onChange":'changeDropdown(this.value)'}))
    ccap_sub = forms.ChoiceField(required=False, choices=SpartaProfile.CCAP_SUBCHOICES)
    lgu_sub = forms.ChoiceField(required=False, choices=SpartaProfile.LGU_SUBCHOICES)

class EditSpartaProfileForm(forms.Form):
    """
    """
    discovery = forms.ChoiceField(required=False, choices=SpartaProfile.DISCOVERY_CHOICES)
    org = forms.ChoiceField(required=False, choices=SpartaProfile.ORG_CHOICES, widget=forms.Select(attrs={"onChange":'changeDropdown(this.value)'}))
    ccap_sub = forms.ChoiceField(required=False, choices=SpartaProfile.CCAP_SUBCHOICES)
    lgu_sub = forms.ChoiceField(required=False, choices=SpartaProfile.LGU_SUBCHOICES)

class ExtendedSpartaProfileForm(forms.ModelForm):
    """
    """
    address = forms.CharField(
        required=True,
        widget=forms.Textarea
    )
    is_employed = forms.TypedChoiceField(
                   coerce=lambda x: x == 'True',
                   choices=((True, 'Yes'), (False, 'No')),
                   widget=forms.RadioSelect,
                   initial=False
                )
    class Meta:
        model = ExtendedSpartaProfile
        fields = [
            'address',
            'municipality',
            'affiliation',
            'attainment',
            'other_attain','is_employed',
            'grad_degree'
            ]


class EducationProfileForm(forms.ModelForm):
    """
    """
    degree = forms.ChoiceField(required=True, choices=EducationProfile.DEGREE_CHOICES)
    course = forms.CharField(
        required=True,
        error_messages={'required': 'This field is required.Input N/A for None'},
        widget=forms.Textarea
    )
    school = forms.CharField(
        required=True,
        error_messages={'required': 'This field is required.Input N/A for None'},
        widget=forms.Textarea
    )
    address = forms.CharField(
        required=True,
        error_messages={'required': 'This field is required.Input N/A for None'},
        widget=forms.Textarea
    )
    started_at = forms.DateField(
        initial=date.today(),
        widget=forms.SelectDateWidget(
            years=range(1900, int(datetime.now().strftime("%Y"))+1),
            empty_label=("Choose Year", "Choose Month", "Choose Day"),
            ),
        required=True
        )
    graduated_at = forms.DateField(
        initial=date.today(),
        widget=forms.SelectDateWidget(
            years=range(1900, int(datetime.now().strftime("%Y"))+1),
            empty_label=("Choose Year", "Choose Month", "Choose Day"),
            ),
        required=True
        )
    class Meta:
        model = EducationProfile
        fields = [
            'degree', 'course', 'school', 'address', 'started_at', 'graduated_at'
        ]

    def clean(self):
        cleaned_data = super(EducationProfileForm, self).clean()
        started_at = cleaned_data.get('started_at')
        graduated_at = cleaned_data.get('graduated_at')

        if started_at and graduated_at and started_at >= graduated_at:
            msg = "Date for 'started_at' must be before date for 'graduated_at'."
            self.add_error('started_at', msg)
            self.add_error('graduated_at', msg)


class EmploymentProfileForm(forms.ModelForm):
    """
    """
    affiliation = forms.ChoiceField(required=True, choices=EmploymentProfile.AFF_CHOICES)
    occupation = forms.CharField(
        required=True,
        error_messages={'required': 'This field is required.Input N/A for None'},
        widget=forms.Textarea
    )
    designation = forms.CharField(
        required=True,
        error_messages={'required': 'This field is required.Input N/A for None'},
        widget=forms.Textarea
    )
    started_at = forms.DateField(
        initial=date.today(),
        widget=forms.SelectDateWidget(
            years=range(1900, int(datetime.now().strftime("%Y"))+1),
            empty_label=("Choose Year", "Choose Month", "Choose Day"),
            ),
        required=True
        )
    ended_at = forms.DateField(
        widget=forms.SelectDateWidget(
            years=range(1900, int(datetime.now().strftime("%Y"))+1),
            empty_label="Present",
            ),
        required=False
        )
    employer = forms.CharField(
        required=True,
        error_messages={'required': 'This field is required.Input N/A for None'},
        widget=forms.Textarea
    )
    address = forms.CharField(
        required=True,
        error_messages={'required': 'This field is required.Input N/A for None'},
        widget=forms.Textarea
    )
    class Meta:
        model = EmploymentProfile
        fields = [
            'affiliation', 'occupation', 'designation', 'started_at', 'ended_at',
            'employer', 'address',
        ]

    def clean(self):
        cleaned_data = super(EmploymentProfileForm, self).clean()
        started_at = cleaned_data.get('started_at')
        ended_at = cleaned_data.get('ended_at', None)

        if ended_at is not None and started_at and ended_at and started_at >= ended_at:
            msg = "Date for 'started_at' must be before date for 'ended_at'."
            self.add_error('started_at', msg)
            self.add_error('ended_at', msg)


class TrainingProfileForm(forms.ModelForm):
    """
    """
    title = forms.CharField(
        required=True,
        error_messages={'required': 'This field is required.Input N/A for None'},
        widget=forms.Textarea
    )
    organizer = forms.CharField(
        required=True,
        error_messages={'required': 'This field is required.Input N/A for None'},
        widget=forms.Textarea
    )
    address = forms.CharField(
        required=True,
        error_messages={'required': 'This field is required.Input N/A for None'},
        widget=forms.Textarea
    )
    started_at = forms.DateField(
        initial=date.today(),
        widget=forms.SelectDateWidget(
            years=range(1900, int(datetime.now().strftime("%Y"))+1),
            empty_label=("Choose Year", "Choose Month", "Choose Day"),
            ),
        required=True
        )
    ended_at = forms.DateField(
        initial=date.today(),
        widget=forms.SelectDateWidget(
            years=range(1900, int(datetime.now().strftime("%Y"))+1),
            empty_label=("Choose Year", "Choose Month", "Choose Day"),
            ),
        required=True
        )
    class Meta:
        model = TrainingProfile
        fields = [
            'title', 'organizer', 'address', 'started_at', 'ended_at'
        ]

    def clean(self):
        cleaned_data = super(TrainingProfileForm, self).clean()
        started_at = cleaned_data.get('started_at')
        ended_at = cleaned_data.get('ended_at')

        if started_at and ended_at and started_at > ended_at:
            msg = "Date for 'started_at' must be the same or before date for 'ended_at'."
            self.add_error('started_at', msg)
            self.add_error('ended_at', msg)


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


class ExportAppsForm(forms.Form):
    """
    """
    ALL = "all"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    CHOICES = (
        (ALL, "All"),
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (DENIED, "Denied"),
        (WITHDRAWN, "Withdrawn")
    )
    selection = forms.ChoiceField(choices=CHOICES)

class GenerateCourseForm(forms.Form):
    """
    """
    SP101 = "course-v1:DAP+SP101+2020_Q1"
    SP201 = "course-v1:DAP+SP201+2020_Q1"
    SP202 = "course-v1:DAP+SP202+2020_Q1"
    SP301 = "course-v1:DAP+SP301+2020_Q1"
    SP401 = "course-v1:CirroLytix+CX101+2019_T4"
    SP501 = "course-v1:DAP+SP501+2020_Q1"
    
    CHOICES = (
        (SP202, "SP202"),
        (SP101, "SP101"),
        (SP201, "SP201"),
        (SP301, "SP301"),
        (SP401, "SP401"),
        (SP501, "SP501")
    )
    course = forms.ChoiceField(choices=CHOICES)

class ExportProfilesForm(forms.Form):
    """
    """


class ExportAnalyticsForm(forms.Form):
    """
    """

class ExportPathwayAnalyticsForm(forms.Form):
    """
    """
    TOTALS = "Totals"
    LEARNERS = "Learners"
    CHOICES = (
        (TOTALS, "Totals"),
        (LEARNERS, "Learners")
    )
    choice = forms.ChoiceField(choices=CHOICES)


class FilterForm(forms.Form):
    """
    """
    date_from = forms.DateField(
        initial=timezone.now().date(),
        widget=forms.SelectDateWidget(
            years=range(2019, 2024),
            empty_label=("Choose Year", "Choose Month", "Choose Day"),
            ),
        required=False
        )
    date_to = forms.DateField(
        initial=timezone.now().date(),
        widget=forms.SelectDateWidget(
            years=range(2019, int(datetime.now().strftime("%Y"))+1),
            empty_label=("Choose Year", "Choose Month", "Choose Day"),
            ),
        required=False
        )