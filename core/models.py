# models.py
from django.contrib.auth.models import User
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


class Application(models.Model):
    # 原有字段保持不变
    app_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)


class AppVersion(models.Model):
    # 原有字段保持不变
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    version = models.CharField(max_length=50)
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    md5_hash = models.CharField(max_length=32)
    upload_time = models.DateTimeField(auto_now_add=True)
    release_notes = models.TextField(blank=True)


class GitHubSocialAuth(models.Model):
    """
    存储与GitHub账户关联的信息
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='github_auth'
    )
    # GitHub用户的唯一ID (不可变)
    github_id = models.PositiveBigIntegerField(unique=True)
    # GitHub用户名
    github_login = models.CharField(max_length=100)
    # GitHub访问令牌 (用于API调用)
    access_token = models.CharField(max_length=100)
    # 令牌过期时间
    token_expiry = models.DateTimeField(null=True, blank=True)
    # 刷新令牌 (如果提供)
    refresh_token = models.CharField(max_length=100, null=True, blank=True)
    # 最后更新时间
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} (GitHub: {self.github_login})"


class UserProfile(models.Model):
    """
    扩展用户个人信息
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    # 从GitHub获取的头像URL
    avatar_url = models.URLField(max_length=255, blank=True, null=True)
    # 从GitHub获取的公开姓名
    full_name = models.CharField(max_length=150, blank=True, null=True)
    # GitHub个人主页URL
    github_profile = models.URLField(max_length=255, blank=True, null=True)
    # 用户注册来源标记
    registration_source = models.CharField(
        max_length=20,
        choices=[('github', 'GitHub'), ('local', 'Local Registration')],
        default='local'
    )


# 信号处理：创建用户时自动创建Profile
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
