import hashlib
import os
import re
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
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


from django.shortcuts import redirect, render

from django.contrib.auth import authenticate, login, logout


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


from django.shortcuts import render, redirect
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
