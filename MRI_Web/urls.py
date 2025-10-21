from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Django 认证系统的 URLs
    path('', include([
        path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
        path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
        path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
        path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    ])),
    # 放在最后，因为它可能包含一些通配符URL
    path('', include('blog.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 