from django.urls import path
from django.shortcuts import render
from . import views

app_name = 'blog'
urlpatterns = [
    # 原有路由
    path('', views.image_list, name='image_list'),
    path('upload/', views.upload_image, name='upload_image'),
    path('image/<int:pk>/', views.image_detail, name='image_detail'),
    path('image/<int:pk>/process/', views.process_image, name='process_image'),
    path('masks/', views.mask_list, name='mask_list'),
    path('mask/<int:pk>/', views.mask_detail, name='mask_detail'),
    path('article/upload/', views.article_upload, name='article_upload'),
    path('article/<int:pk>/', views.article_detail, name='article_detail'),
    path('articles/', views.article_list, name='article_list'),
    
    # 数据管理系统路由
    # 数据类型管理
    path('data-types/', views.data_type_list, name='data_type_list'),
    path('data-types/<int:pk>/', views.data_type_detail, name='data_type_detail'),
    path('data-types/create/', views.admin_data_type_create, name='admin_data_type_create'),
    path('data-types/<int:pk>/edit/', views.admin_data_type_edit, name='admin_data_type_edit'),
    
    # 数据源管理
    path('data-sources/', views.data_source_list, name='data_source_list'),
    path('data-sources/<int:pk>/', views.data_source_detail, name='data_source_detail'),
    path('data-sources/create/', views.data_source_create, name='data_source_create'),
    path('data-sources/<int:pk>/edit/', views.data_source_edit, name='data_source_edit'),
    
    # 数据文件管理
    path('data-files/upload/', views.data_file_upload, name='data_file_upload'),
    path('data-files/upload-progress/', views.data_file_upload_with_progress, name='data_file_upload_progress'),
    path('data-files/progress/<str:upload_id>/', views.get_upload_progress, name='get_upload_progress'),
    path('data-files/<int:pk>/', views.data_file_detail, name='data_file_detail'),
    path('data-files/<int:pk>/download/', views.data_file_download, name='data_file_download'),
    path('data-files/<int:pk>/delete/', views.data_file_delete, name='data_file_delete'),
    
    # 演示页面
    path('upload-demo/', lambda request: render(request, 'blog/upload_demo.html'), name='upload_demo'),
    path('progress-test/', lambda request: render(request, 'blog/progress_test.html'), name='progress_test'),
    
    # 用户认证 - 只保留注册功能
    path('register/', views.register, name='register'),  # 注册
] 