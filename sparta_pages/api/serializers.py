from django.utils import timezone

from rest_framework import serializers

from ..models import (
    Pathway, SpartaCourse,
    SpartaProfile, ExtendedSpartaProfile,
    PathwayApplication,
    EducationProfile, EmploymentProfile
)


class Field(serializers.RelatedField):
    def to_representation(self, value):
        return value


class PathwaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Pathway
        fields = [
            'id', 'name',
        ]
        read_only_fields = fields


class SpartaCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpartaCourse
        fields = [
            'id', 'course_id', 'pathway'
        ]
        read_only_fields = fields


class SpartaProfileSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    discovery = serializers.SerializerMethodField()
    class Meta:
        model = SpartaProfile
        fields = [
            'id',
            'full_name',
            'username',
            'email',
            'age',
            'gender',
            'discovery',
            'org',
            'ccap_sub',
            'lgu_sub',
            'is_active',
            'created_at'
            ]
        read_only_fields = fields

    def get_age(self, obj):
        try:
            yob = obj.user.profile.year_of_birth
        except:
            return None
        if yob is not None:
            return timezone.now().year - yob
        else:
            return None

    def get_gender(self, obj):
        try:
            g = obj.user.profile.get_gender_display()
        except:
            return "Other/Prefer Not to Say"
        else:
            return g

    def get_discovery(self, obj):
        return obj.get_discovery_display()


class ExtendedSpartaProfileSerializer(serializers.ModelSerializer):
    affiliation = serializers.SerializerMethodField()
    attainment = serializers.SerializerMethodField()
    grad_degree = serializers.SerializerMethodField()

    class Meta:
        model = ExtendedSpartaProfile
        fields = [
            'address', 'municipality', 'affiliation', 'attainment',
            'other_attain', 'is_employed', 'grad_degree'
            ]
        read_only_fields = fields

    def get_affiliation(self, obj):
        return obj.get_affiliation_display()

    def get_attainment(self, obj):
        return obj.get_attainment_display()

    def get_grad_degree(self, obj):
        return obj.get_grad_degree_display()


class EducationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationProfile
        fields = [
            'id',
            'profile', 'degree', 'course', 'school', 'address',
            'started_at', 'graduated_at'
            ]
        read_only_fields = fields


class EmploymentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentProfile
        fields = [
            'id',
            'profile', 'affiliation', 'occupation', 'designation',
            'employer', 'address', 'started_at', 'ended_at'
            ]
        read_only_fields = fields


class PathwayApplicationSerializer(serializers.ModelSerializer):
    pathway = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = PathwayApplication
        fields = [
            'profile', 'pathway', 'status', 'created_at'
            ]
        read_only_fields = fields

    def get_pathway(self, obj):
        return obj.pathway.name

    def get_status(self, obj):
        return obj.get_status_display()
