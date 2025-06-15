# serializers.py
from rest_framework import serializers
from .models import Application, AppVersion

class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['app_id', 'name', 'description', 'owner', 'created_at']
        read_only_fields = ['owner', 'created_at']
        extra_kwargs = {
            'app_id': {'required': True},
            'name': {'required': True}
        }

class AppVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppVersion
        fields = [
            'id', 'application', 'version', 'file_name',
            'file_size', 'md5_hash', 'release_notes', 'upload_time'
        ]
        read_only_fields = [
            'id', 'file_name', 'file_size',
            'md5_hash', 'upload_time'
        ]
        extra_kwargs = {
            'version': {'required': True}
        }