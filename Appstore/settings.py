import os
from pathlib import Path
from dotenv import load_dotenv  # 添加 dotenv 支持

# 加载环境变量
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ====================== #
#   安全敏感配置 - 使用环境变量   #
# ====================== #

# 从环境变量获取密钥，如果没有则使用默认值（仅用于开发）
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-development-key')

# 调试模式 - 生产环境必须关闭
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

# 信任的来源 - 从环境变量获取
SECURE_TRUSTED_ORIGINS = os.getenv('DJANGO_TRUSTED_ORIGINS', 'http://localhost,https://127.0.0.1:6015').split(',')

# 允许的主机 - 从环境变量获取
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# CORS 配置 - 从环境变量获取
cors_allowed = os.getenv('DJANGO_CORS_ALLOWED_ORIGINS', 'http://localhost,https://127.0.0.1:6015,http://localhost:6015')
CORS_ALLOWED_ORIGINS = cors_allowed.split(',') if cors_allowed else []

# ====================== #
#       应用配置          #
# ====================== #

INSTALLED_APPS = [
    'simpleui',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'core',
    'social_django',
    'corsheaders',  # 确保已安装并添加
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # 移到最前面
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 生产环境应设置为 False
CORS_ALLOW_ALL_ORIGINS = DEBUG

ROOT_URLCONF = 'Appstore.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # 添加模板目录
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',  # 添加社交登录上下文
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'Appstore.wsgi.application'

# ====================== #
#       数据库配置        #
# ====================== #

# 使用环境变量配置数据库
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
    }
}

# ====================== #
#      密码验证配置       #
# ====================== #

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ====================== #
#      国际化配置         #
# ====================== #

LANGUAGE_CODE = os.getenv('DJANGO_LANGUAGE_CODE', 'zh-hans')
TIME_ZONE = os.getenv('DJANGO_TIME_ZONE', 'Asia/Shanghai')
USE_I18N = True
USE_TZ = True

# ====================== #
#      静态文件配置       #
# ====================== #

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # 添加静态文件根目录

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 应用存储路径
APP_STORAGE = os.getenv('APP_STORAGE_PATH', os.path.join(BASE_DIR, 'app_storage'))

# ====================== #
#      REST 框架配置      #
# ====================== #

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# ====================== #
#      认证后端配置       #
# ====================== #

AUTHENTICATION_BACKENDS = (
    'social_core.backends.github.GithubOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

# ====================== #
#     GitHub OAuth 配置   #
# ====================== #

# 从环境变量获取 GitHub 配置
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
GITHUB_REDIRECT_URI = os.getenv('GITHUB_REDIRECT_URI', 'http://127.0.0.1:8000/github-callback/')

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'core.pipeline.save_github_social_auth',  # 更新为您的应用路径
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

# ====================== #
#      安全增强配置       #
# ====================== #

# 生产环境安全设置
if not DEBUG:
    # HTTPS 重定向
    SECURE_SSL_REDIRECT = True

    # 安全 Cookie
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # HSTS 设置
    SECURE_HSTS_SECONDS = 31536000  # 1年
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # 防止点击劫持
    X_FRAME_OPTIONS = 'DENY'

    # 内容安全策略
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True