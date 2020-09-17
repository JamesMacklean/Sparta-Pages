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
    discovery = serializers.SerializerMethodField()
    class Meta:
        model = SpartaProfile
        fields = [
            'id', 'is_active', 'discovery'
            ]
        read_only_fields = fields
    
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
            'profile', 'degree', 'course', 'school', 'address',
            'started_at', 'graduated_at'
            ]
        read_only_fields = fields


class EmploymentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentProfile
        fields = [
            'profile', 'affiliation', 'occupation', 'designation',
            'employer', 'address', 'started_at', 'ended_at'
            ]
        read_only_fields = fields


class PathwayApplicationSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = PathwayApplication
        fields = [
            'profile', 'pathway', 'status', 'created_at'
            ]
        read_only_fields = fields
    
    def get_status(self, obj):
        return obj.get_status_display()
