from django.urls import path
from . import views

app_name = 'blog'
urlpatterns = [
    path('', views.image_list, name='image_list'),
    path('upload/', views.upload_image, name='upload_image'),
    path('image/<int:pk>/', views.image_detail, name='image_detail'),
    path('image/<int:pk>/process/', views.process_image, name='process_image'),
    path('masks/', views.mask_list, name='mask_list'),
    path('mask/<int:pk>/', views.mask_detail, name='mask_detail'),
    path('article/upload/', views.article_upload, name='article_upload'),
    path('article/<int:pk>/', views.article_detail, name='article_detail'),
    path('articles/', views.article_list, name='article_list'),
] 