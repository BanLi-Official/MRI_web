from django.urls import path
from . import views

app_name = 'blog'
urlpatterns = [
    path('', views.image_list, name='image_list'),
    path('upload/', views.upload_image, name='upload_image'),
    path('image/<int:pk>/', views.image_detail, name='image_detail'),
] 