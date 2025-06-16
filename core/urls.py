# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # 创建新应用
    path('apps/', views.CreateApplicationView.as_view(), name='create-application'),

    # 应用版本管理 (列表和创建)
    path('apps/<str:app_id>/versions/', views.AppVersionAPI.as_view(), name='app-versions'),

    # 下载特定版本
    path('apps/<str:app_id>/versions/<str:version>/download/', views.download_app_version, name='download-app-version'),

    # 获取最新版本信息
    path('apps/<str:app_id>/versions/latest/', views.LatestVersionAPI.as_view(), name='latest-version'),

    path('', views.market, name='market'),
    path('details/<str:app_id>/', views.app_detail, name='app_detail'),

    path('apps/versions/upload/<str:app_id>/', views.upload_version, name='upload_app_version'),

    path('register/', views.register_view, name='register_view'),
    path('accounts/login/', views.login_view, name='login_view'),
    path('login/', views.login_enter, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('github-login/', views.github_login, name='github_login'),
    path('github-callback/', views.github_callback, name='github_callback'),

    path('profile/', views.user_profile, name='user_profile'),
]
