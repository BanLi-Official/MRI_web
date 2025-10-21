import os

# ... 现有代码 ...

ALLOWED_HOSTS = ['*']

# 登录相关配置
LOGIN_URL = 'login'  # 使用直接的 URL 名称
LOGIN_REDIRECT_URL = '/'  # 登录后重定向到首页
LOGOUT_REDIRECT_URL = '/'  # 登出后重定向到首页

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'blog',  # 确保这行存在
]

# ... 现有代码 ...

# 添加媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') 