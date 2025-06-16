import hashlib
import os
import re
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, logger
from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from packaging.version import parse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.renderers import JSONRenderer  # 添加渲染器
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AppVersion, Application
from .serializers import ApplicationSerializer, AppVersionSerializer
from django.contrib.auth.decorators import login_required

# 配置存储路径
STORAGE_PATH = getattr(settings, 'APP_STORAGE', 'app_storage')
storage = FileSystemStorage(location=STORAGE_PATH)


def sanitize_filename(filename):
    """清理文件名中的非法字符"""
    filename = os.path.basename(filename)
    filename = re.sub(r'[\\/*?:"<>|]', '', filename)
    return filename


class CreateApplicationView(APIView):
    """创建新应用"""
    renderer_classes = [JSONRenderer]  # 明确指定渲染器

    def post(self, request, format=None):
        serializer = ApplicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return Response(
                {"success": f"应用 '{serializer.validated_data['name']}' 创建成功!"},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"error": "创建应用失败", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class AppVersionAPI(APIView):
    """应用版本管理"""
    renderer_classes = [JSONRenderer]  # 明确指定渲染器

    def get(self, request, app_id, format=None):
        """获取应用所有版本信息"""
        try:
            application = Application.objects.get(app_id=app_id)
        except Application.DoesNotExist:
            return Response(
                {"error": f"应用ID '{app_id}' 不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        versions = AppVersion.objects.filter(
            application=application
        ).order_by('-upload_time')

        if not versions.exists():
            return Response([], status=status.HTTP_200_OK)

        serializer = AppVersionSerializer(versions, many=True)

        # 按版本号排序（使用packaging.version）
        sorted_versions = sorted(
            serializer.data,
            key=lambda x: parse(x['version']),
            reverse=True
        )

        return Response(sorted_versions, status=status.HTTP_200_OK)

    def post(self, request, app_id, format=None):
        """上传新版本应用"""
        try:
            application = Application.objects.get(app_id=app_id)
        except Application.DoesNotExist:
            return Response(
                {"error": f"应用ID '{app_id}' 不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 验证必需字段
        if 'version' not in request.data:
            return Response(
                {"error": "缺少版本号参数"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if 'file' not in request.FILES:
            return Response(
                {"error": "缺少应用文件"},
                status=status.HTTP_400_BAD_REQUEST
            )

        version = request.data['version']
        release_notes = request.data.get('release_notes', '')
        file = request.FILES['file']
        sanitized_filename = sanitize_filename(file.name)

        # 创建应用目录
        app_dir = os.path.join(STORAGE_PATH, app_id)
        os.makedirs(app_dir, exist_ok=True)

        # 保存文件
        filename = f"{version}_{sanitized_filename}"
        file_path = os.path.join(app_dir, filename)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # 计算文件哈希和大小
        with open(file_path, 'rb') as f:
            content = f.read()
            file_md5 = hashlib.md5(content).hexdigest()
        file_size = os.path.getsize(file_path)

        # 创建版本记录
        app_version = AppVersion.objects.create(
            application=application,
            version=version,
            file_name=sanitized_filename,
            file_size=file_size,
            md5_hash=file_md5,
            release_notes=release_notes
        )

        return Response(
            {
                "success": f"版本 {version} 上传成功!",
                "version": AppVersionSerializer(app_version).data
            },
            status=status.HTTP_201_CREATED
        )


@login_required
@api_view(['GET'])
def download_app_version(request, app_id, version):
    """下载特定版本应用"""
    app_version = get_object_or_404(
        AppVersion,
        application__app_id=app_id,
        version=version
    )

    file_path = os.path.join(STORAGE_PATH, app_id, f"{version}_{app_version.file_name}")
    print(file_path)
    if not os.path.exists(file_path):
        return Response(
            {"error": "文件不存在"},
            status=status.HTTP_404_NOT_FOUND
        )

    return FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=app_version.file_name
    )


class LatestVersionAPI(APIView):
    """获取最新版本信息"""
    renderer_classes = [JSONRenderer]  # 明确指定渲染器

    def get(self, request, app_id, format=None):
        try:
            application = Application.objects.get(app_id=app_id)
        except Application.DoesNotExist:
            return Response(
                {"error": f"应用ID '{app_id}' 不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        version = AppVersion.objects.filter(
            application=application
        ).order_by('-upload_time').first()

        if not version:
            return Response(
                {"error": "该应用暂无可用版本"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AppVersionSerializer(version)
        return Response(serializer.data, status=status.HTTP_200_OK)


def market(request):
    query = request.GET.get('q', '')
    apps = Application.objects.all()

    if query:
        apps = apps.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).distinct()

    paginator = Paginator(apps, 9)  # 每页9个应用
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'market.html', {
        'applications': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages()
    })


def app_detail(request, app_id):
    app = get_object_or_404(Application, pk=app_id)
    app_versions = AppVersion.objects.filter(application=app).order_by('-upload_time')
    return render(request, 'app_detail.html', {'app': app, 'app_versions': app_versions})


def upload_version(request, app_id):
    application = get_object_or_404(Application, app_id=app_id)

    if request.method == 'POST':
        version = request.POST.get('version')
        file = request.FILES.get('file')  # 可能为None
        release_notes = request.POST.get('release_notes', '')

        # 检查必需字段是否提供
        errors = []
        if not version:
            errors.append("版本号不能为空")

        if not file:  # 检查文件是否上传
            errors.append("请选择要上传的文件")

        # 如果存在错误，返回表单并显示错误
        if errors:
            versions = AppVersion.objects.filter(application=application)
            return render(request, 'upload-version.html', {
                'application': application,
                'versions': versions,
                'errors': errors
            })

        # 校验版本号是否已存在
        if AppVersion.objects.filter(application=application, version=version).exists():
            versions = AppVersion.objects.filter(application=application)
            return render(request, 'upload-version.html', {
                'application': application,
                'versions': versions,
                'error': '该版本号已存在'
            })

        # 创建应用目录
        app_dir = os.path.join(STORAGE_PATH, str(app_id))
        os.makedirs(app_dir, exist_ok=True)

        # 计算文件MD5
        md5 = hashlib.md5()
        for chunk in file.chunks():
            md5.update(chunk)
        md5_hash = md5.hexdigest()

        # 保存文件到指定的应用目录
        sanitized_filename = sanitize_filename(file.name)
        filename = f"{version}_{sanitized_filename}"
        file_path = os.path.join(app_dir, filename)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # 创建新版本记录
        AppVersion.objects.create(
            application=application,
            version=version,
            file_name=sanitized_filename,
            file_size=os.path.getsize(file_path),
            md5_hash=md5_hash,
            upload_time=timezone.now(),
            release_notes=release_notes
        )

        return redirect('app_detail', app_id=app_id)

    # GET请求
    versions = AppVersion.objects.filter(application=application).order_by('-upload_time')
    return render(request, 'upload-version.html', {
        'application': application,
        'versions': versions
    })


from django.contrib.auth import authenticate


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # 从 GET 请求中获取 next 参数
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)  # 登录成功后重定向到 next 页面
            return redirect('/')  # 登录成功后重定向到 index 页面
        else:
            # 如果登录失败，仍然从 GET 请求中获取 next 参数以便在模板中显示
            next_url = request.GET.get('next')
            return render(request, 'login.html', {'error': '用户名或密码错误', 'next': next_url})
    else:
        # 如果不是 POST 请求，则直接渲染登录页面，并从 GET 请求中获取 next 参数
        next_url = request.GET.get('next')
        return render(request, 'login.html', {'next': next_url})


def logout_view(request):
    logout(request)
    return redirect('/')  # 注销成功后重定向到index页面


def login_enter(request):
    # 假设你想传递一个next参数
    if request.user.is_authenticated:
        return render(request, 'login.html', {'user_logged_in': True})
    next_url = request.GET.get('next', '/')  # 从请求中获取next参数，如果没有则默认为根目录
    query_string = urlencode({'next': next_url})
    return redirect(f'/accounts/login?{query_string}')


from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout


def register_view(request):
    if request.user.is_authenticated:
        # 用户已登录，提示用户选择继续或切换账户
        return render(request, 'reg.html', {'user_logged_in': True})
    else:
        # 用户未登录，渲染注册页面
        if request.method == 'POST':
            form = UserCreationForm(request.POST)
            if form.is_valid():
                # 处理注册逻辑
                form.save()
                # 注册成功后的行为
                return redirect('login_view')  # 替换为你的成功后要跳转的视图名称
        else:
            form = UserCreationForm()
        return render(request, 'reg.html', {'form': form})


@login_required
def logout_view(request):
    # 登出逻辑
    logout(request)
    return redirect('login_view')  # 或者重定向到其他页面


# GitHub OAuth 配置 (添加到settings.py)
"""
在 settings.py 中添加：
GITHUB_CLIENT_ID = 'your_github_client_id'
GITHUB_CLIENT_SECRET = 'your_github_client_secret'
GITHUB_REDIRECT_URI = 'http://yourdomain.com/github-callback/'
"""


def github_login(request):
    """重定向到GitHub授权页面"""
    base_url = "https://github.com/login/oauth/authorize"
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI
    }
    auth_url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    return redirect(auth_url)


import requests
import logging
from django.shortcuts import redirect, render
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import IntegrityError
from .models import GitHubSocialAuth, UserProfile

logger = logging.getLogger(__name__)


def github_callback(request):
    """处理GitHub回调"""
    code = request.GET.get('code')
    state = request.GET.get('state')

    if not code:
        return render(request, 'error.html', {'error': 'GitHub授权失败: 缺少code参数'})

    # 1. 使用code换取access_token
    token_url = "https://github.com/login/oauth/access_token"
    data = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.GITHUB_REDIRECT_URI
    }
    headers = {"Accept": "application/json"}

    try:
        response = requests.post(token_url, data=data, headers=headers, verify=False)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"获取access_token失败: {str(e)}")
        return render(request, 'error.html', {'error': f'获取access_token失败: {str(e)}'})

    if response.status_code != 200:
        return render(request, 'error.html', {'error': f'获取access_token失败: 状态码{response.status_code}'})

    token_data = response.json()
    access_token = token_data.get('access_token')
    if not access_token:
        return render(request, 'error.html', {'error': '缺少access_token'})

    # 2. 使用access_token获取用户信息
    user_api = "https://api.github.com/user"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        user_response = requests.get(user_api, headers=headers, verify=False)
        user_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        return render(request, 'error.html', {'error': f'获取用户信息失败: {str(e)}'})

    if user_response.status_code != 200:
        return render(request, 'error.html', {'error': f'获取用户信息失败: 状态码{user_response.status_code}'})

    github_user = user_response.json()
    github_id = github_user['id']
    username = github_user['login']
    email = github_user.get('email', '')
    avatar_url = github_user['avatar_url']
    name = github_user.get('name', '')
    html_url = github_user.get('html_url', '')

    logger.info(f"GitHub用户登录: {username} (ID: {github_id})")

    try:
        # 尝试查找现有GitHub关联
        github_auth = GitHubSocialAuth.objects.get(github_id=github_id)
        user = github_auth.user

        # 更新访问令牌
        github_auth.access_token = access_token
        github_auth.save()

        logger.debug(f"找到现有用户: {user.username}")

        # 检查并更新用户资料
        try:
            user_profile = UserProfile.objects.get(user=user)
            user_profile.avatar_url = avatar_url
            if name:
                user_profile.full_name = name
            user_profile.github_profile = html_url
            user_profile.save()
            logger.debug(f"更新用户资料: {user.username}")
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(
                user=user,
                avatar_url=avatar_url,
                full_name=name or '',
                github_profile=html_url,
                registration_source='github'
            )
            logger.info(f"创建用户资料: {user.username}")

        # 关键修复：设置认证后端
        user.backend = 'social_core.backends.github.GithubOAuth2'

        # 登录现有用户
        login(request, user)
        logger.info(f"用户登录成功: {user.username}")
        return redirect('login_view')

    except GitHubSocialAuth.DoesNotExist:
        # 没有找到现有关联，创建新用户
        pass

    # 处理新用户创建
    # 确保有有效的邮箱地址
    if not email:
        try:
            emails_response = requests.get(
                "https://api.github.com/user/emails",
                headers=headers,
                timeout=5,
                verify=False
            )
            if emails_response.status_code == 200:
                emails = emails_response.json()
                primary_emails = [e['email'] for e in emails if e.get('primary') and e.get('verified')]
                verified_emails = [e['email'] for e in emails if e.get('verified')]

                if primary_emails:
                    email = primary_emails[0]
                elif verified_emails:
                    email = verified_emails[0]
                else:
                    email = f"github-{github_id}@users.noreply.github.com"
        except Exception as e:
            logger.warning(f"获取邮箱失败: {str(e)}")
            email = f"github-{github_id}@users.noreply.github.com"

    if not email:
        email = f"github-{github_id}@users.noreply.github.com"

    # 生成唯一用户名
    base_username = f"github_{github_id}"
    username = base_username
    suffix = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}_{suffix}"
        suffix += 1

    # 创建新用户
    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=name.split(' ')[0] if name else '',
            last_name=' '.join(name.split(' ')[1:]) if name and len(name.split(' ')) > 1 else ''
        )
    except IntegrityError as e:
        logger.error(f"创建用户失败: {str(e)}")
        # 尝试使用更简单的用户名
        username = f"github_{github_id}_{suffix}"
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=name.split(' ')[0] if name else '',
                last_name=' '.join(name.split(' ')[1:]) if name and len(name.split(' ')) > 1 else ''
            )
        except Exception as e2:
            logger.error(f"再次创建用户失败: {str(e2)}")
            return render(request, 'error.html', {'error': f'创建用户失败: {str(e2)}'})

    # 创建GitHub认证记录
    try:
        GitHubSocialAuth.objects.create(
            user=user,
            github_id=github_id,
            github_login=github_user['login'],
            access_token=access_token
        )
    except Exception as e:
        logger.error(f"创建GitHub认证记录失败: {str(e)}")
        user.delete()
        return render(request, 'error.html', {'error': f'创建GitHub认证记录失败: {str(e)}'})

    # 创建用户资料
    try:
        UserProfile.objects.create(
            user=user,
            avatar_url=avatar_url,
            full_name=name or '',
            github_profile=html_url,
            registration_source='github'
        )
    except Exception as e:
        logger.warning(f"创建用户资料失败: {str(e)}")

    # 关键修复：设置认证后端
    user.backend = 'django.contrib.auth.backends.ModelBackend'

    # 登录用户
    login(request, user)
    logger.info(f"用户登录成功: {user.username}")
    return redirect('login_view')
