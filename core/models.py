# models.py
from django.contrib.auth.models import User
from django.db import models


class Application(models.Model):
    app_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)


class AppVersion(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    version = models.CharField(max_length=50)
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    md5_hash = models.CharField(max_length=32)
    upload_time = models.DateTimeField(auto_now_add=True)
    release_notes = models.TextField(blank=True)
