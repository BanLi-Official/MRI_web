from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, login, authenticate
from django.contrib import messages
from django.contrib.auth.views import LoginView
from .forms import CustomUserCreationForm

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        # 无论是管理员还是普通用户，都重定向到首页
        return '/'
        
    def get_redirect_url(self):
        # 覆盖父类的重定向逻辑，确保始终使用我们的重定向规则
        return self.get_success_url()
        
    def form_invalid(self, form):
        # # 添加自定义错误消息
        # for field, errors in form.errors.items():
        #     if field == '__all__':  # 非字段错误
        #         messages.error(self.request, '登录失败：用户名或密码错误。')
        #     else:  # 字段特定错误
        #         messages.error(self.request, f'{field}: {", ".join(errors)}')
        return super().form_invalid(form)
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q, Count
from .models import ProcessedImage, Mask, Article, DataType, DataSource, DataFile, UploadProgress
from .forms import ImageUploadForm, ArticleForm, DataTypeForm, DataSourceForm, DataFileUploadForm, DataSourceSearchForm
import os
import numpy as np
from django.conf import settings
import requests
import json
from django.core.files.base import ContentFile
import matplotlib.pyplot as plt
import io
import base64
from django.urls import reverse
import uuid
import time
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator



import os
import numpy as np
import scipy.io as io
import matplotlib.pyplot as plt
from django.conf import settings
import requests
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

@login_required
def upload_image(request):
    # 检查用户是否是管理员
    if not request.user.is_staff:
        messages.error(request, '只有管理员可以上传图片')
        return redirect('blog:image_list')
        
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            processed_image = form.save(commit=False)
            processed_image.uploaded_by = request.user  # 记录上传者
            processed_image.save()
            messages.success(request, '图片上传成功！')
            return redirect('blog:image_list')  # 立即返回列表页
    else:
        form = ImageUploadForm()
    return render(request, 'blog/upload_image.html', {'form': form})

def image_list(request):
    # 所有用户（包括未登录用户）都可以访问列表页
    if request.user.is_authenticated:
        # 已登录用户可以看到所有图片
        images = ProcessedImage.objects.all().order_by('-created_at')
    else:
        # 未登录用户只能看到公开的图片（如果有这个字段的话）
        # 或者显示一个有限的列表
        images = ProcessedImage.objects.all().order_by('-created_at')[:5]  # 比如只显示最新的5张图片
    
    context = {
        'images': images,
        'can_upload': request.user.is_authenticated and request.user.is_staff  # 只有管理员可以看到上传按钮
    }
    return render(request, 'blog/image_list.html', context)

def image_detail(request, pk):
    processed_image = get_object_or_404(ProcessedImage, pk=pk)
    context = {
        'processed_image': processed_image,
        'can_edit': request.user.is_authenticated and request.user.is_staff  # 只有管理员可以编辑
    }
    return render(request, 'blog/image_detail.html', context)

@login_required
def process_image(request, pk):
    processed_image = get_object_or_404(ProcessedImage, pk=pk)
    
    if processed_image.status == 'completed':
        return JsonResponse({'status': 'already_processed'})
    
    try:
        # 准备图像数据
        image_path = processed_image.original_image.path
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # 准备mask数据
        mask_data = None
        if processed_image.selected_mask:
            mask_path = processed_image.selected_mask.mask_file.path
            with open(mask_path, 'rb') as f:
                mask_data = f.read()
        
        # 准备请求数据
        files = {
            'image': ('image.mat', image_data, 'application/octet-stream')
        }
        
        if mask_data:
            files['mask'] = ('mask.mat', mask_data, 'application/octet-stream')
        
        data = {
            'model_type': processed_image.model_type
        }
        
        # 发送请求到FastAPI服务器
        response = requests.post(
            'http://localhost:8001/process/',
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            # 保存处理后的结果
            result_data = response.content
            result_path = os.path.join(settings.MEDIA_ROOT, 'processed', f'result_{pk}.mat')
            os.makedirs(os.path.dirname(result_path), exist_ok=True)
            
            with open(result_path, 'wb') as f:
                f.write(result_data)
            
            # 读取处理结果
            result = io.loadmat(result_path)
            
            # 保存零填充图像
            zero_filled = result['zeorfilled_data_sos']
            zero_filled_path = os.path.join(settings.MEDIA_ROOT, 'processed', f'zero_filled_{pk}.png')
            plt.imsave(zero_filled_path, zero_filled, cmap='gray')
            processed_image.zero_filled_image = f'processed/zero_filled_{pk}.png'
            
            # 保存重建图像
            reconstructed = result['rec_Image_sos']
            reconstructed_path = os.path.join(settings.MEDIA_ROOT, 'processed', f'reconstructed_{pk}.png')
            plt.imsave(reconstructed_path, reconstructed, cmap='gray')
            processed_image.reconstructed_image = f'processed/reconstructed_{pk}.png'
            
            # 更新指标
            processed_image.psnr = float(result['psnr'])
            processed_image.ssim = float(result['ssim'])
            processed_image.status = 'completed'
            processed_image.save()
            
            return JsonResponse({
                'status': 'success',
                'psnr': processed_image.psnr,
                'ssim': processed_image.ssim
            })
        else:
            processed_image.status = 'failed'
            processed_image.save()
            return JsonResponse({
                'status': 'error',
                'message': f'处理失败: {response.text}'
            })
            
    except Exception as e:
        processed_image.status = 'failed'
        processed_image.save()
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

def mask_list(request):
    masks = Mask.objects.all().order_by('-created_at')
    return render(request, 'blog/mask_list.html', {'masks': masks})

def mask_detail(request, pk):
    mask = get_object_or_404(Mask, pk=pk)
    return render(request, 'blog/mask_detail.html', {'mask': mask})

def upload_view(request):
    if request.method == 'POST':
        # 处理文件上传逻辑
        pass
    return render(request, 'upload.html')

@login_required
def article_upload(request):
    # 检查用户是否是管理员
    if not request.user.is_staff:
        messages.error(request, '只有管理员可以发布文章')
        return redirect('blog:article_list')
        
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user  # 设置作者为当前管理员
            article.save()
            messages.success(request, '文章发布成功！')
            return redirect(reverse('blog:article_detail', args=[article.pk]))
    else:
        form = ArticleForm()
    return render(request, 'blog/article_upload.html', {'form': form})

def article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk)
    return render(request, 'blog/article_detail.html', {'article': article})

def article_list(request):
    articles = Article.objects.all().order_by('-created_time')
    
    context = {
        'articles': articles,
        'can_upload': request.user.is_authenticated and request.user.is_staff
    }
    return render(request, 'blog/article_list.html', context)


# ==================== 数据管理系统视图 ====================

def data_type_list(request):
    """数据类型列表页面"""
    data_types = DataType.objects.annotate(
        source_count=Count('datasource'),
        file_count=Count('datasource__datafile')
    ).order_by('name')
    return render(request, 'blog/data_type_list.html', {'data_types': data_types})


def data_type_detail(request, pk):
    """数据类型详情页面"""
    data_type = get_object_or_404(DataType, pk=pk)
    data_sources = DataSource.objects.filter(data_type=data_type).order_by('-created_at')
    
    # 分页
    paginator = Paginator(data_sources, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'blog/data_type_detail.html', {
        'data_type': data_type,
        'page_obj': page_obj
    })


def data_source_list(request):
    """数据源列表页面"""
    search_form = DataSourceSearchForm(request.GET)
    data_sources = DataSource.objects.filter(is_public=True).select_related('data_type').order_by('-created_at')
    
    # 应用搜索过滤
    if search_form.is_valid():
        data_type = search_form.cleaned_data.get('data_type')
        search_query = search_form.cleaned_data.get('search_query')
        quality_filter = search_form.cleaned_data.get('quality_filter')
        
        if data_type:
            data_sources = data_sources.filter(data_type=data_type)
        if search_query:
            data_sources = data_sources.filter(
                Q(source_name__icontains=search_query) |
                Q(source_description__icontains=search_query) |
                Q(institution__icontains=search_query)
            )
        if quality_filter:
            data_sources = data_sources.filter(data_quality=quality_filter)
    
    # 分页
    paginator = Paginator(data_sources, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'blog/data_source_list.html', {
        'page_obj': page_obj,
        'search_form': search_form
    })


def data_source_detail(request, pk):
    """数据源详情页面"""
    data_source = get_object_or_404(DataSource, pk=pk)
    data_files = DataFile.objects.filter(data_source=data_source, is_active=True).order_by('-created_at')
    
    # 分页
    paginator = Paginator(data_files, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'blog/data_source_detail.html', {
        'data_source': data_source,
        'page_obj': page_obj
    })


@login_required
def data_source_create(request):
    """创建数据源（仅管理员）"""
    if not request.user.is_staff:
        messages.error(request, '只有管理员可以创建数据源')
        return redirect('blog:data_source_list')
    
    if request.method == 'POST':
        form = DataSourceForm(request.POST)
        if form.is_valid():
            data_source = form.save(commit=False)
            data_source.created_by = request.user
            data_source.save()
            messages.success(request, f'数据源 "{data_source.source_name}" 创建成功！')
            return redirect('blog:data_source_detail', pk=data_source.pk)
    else:
        form = DataSourceForm()
    
    return render(request, 'blog/data_source_form.html', {
        'form': form,
        'title': '创建数据源'
    })


@login_required
def data_source_edit(request, pk):
    """编辑数据源（仅管理员）"""
    if not request.user.is_staff:
        messages.error(request, '只有管理员可以编辑数据源')
        return redirect('blog:data_source_detail', pk=pk)
    
    data_source = get_object_or_404(DataSource, pk=pk)
    
    if request.method == 'POST':
        form = DataSourceForm(request.POST, instance=data_source)
        if form.is_valid():
            form.save()
            messages.success(request, '数据源更新成功！')
            return redirect('blog:data_source_detail', pk=pk)
    else:
        form = DataSourceForm(instance=data_source)
    
    return render(request, 'blog/data_source_form.html', {
        'form': form,
        'title': '编辑数据源',
        'data_source': data_source
    })


@login_required
def data_file_upload(request):
    """上传数据文件（仅管理员）"""
    if not request.user.is_staff:
        messages.error(request, '只有管理员可以上传文件')
        return redirect('blog:data_source_list')
    
    if request.method == 'POST':
        form = DataFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            data_file = form.save(commit=False)
            data_file.uploaded_by = request.user
            # 如果文件名为空，使用上传的文件名
            if not data_file.file_name:
                data_file.file_name = request.FILES['file'].name
            data_file.save()
            messages.success(request, f'文件 "{data_file.file_name}" 上传成功！')
            return redirect('blog:data_source_detail', pk=data_file.data_source.pk)
    else:
        form = DataFileUploadForm()
    
    return render(request, 'blog/data_file_upload.html', {'form': form})


@csrf_exempt
@login_required
def data_file_upload_with_progress(request):
    """支持进度跟踪的文件上传（仅管理员）"""
    if not request.user.is_staff:
        return JsonResponse({'error': '只有管理员可以上传文件'}, status=403)
    
    if request.method == 'POST':
        try:
            # 检查是否有文件上传
            if 'file' not in request.FILES:
                return JsonResponse({'error': '没有选择文件'}, status=400)
            
            file = request.FILES['file']
            
            # 验证表单数据
            form = DataFileUploadForm(request.POST, request.FILES)
            if not form.is_valid():
                return JsonResponse({'error': '表单数据无效', 'details': form.errors}, status=400)
            
            # 保存文件
            data_file = form.save(commit=False)
            data_file.uploaded_by = request.user
            if not data_file.file_name:
                data_file.file_name = file.name
            data_file.save()
            
            return JsonResponse({
                'status': 'completed',
                'message': f'文件 "{data_file.file_name}" 上传成功！',
                'redirect_url': reverse('blog:data_source_detail', args=[data_file.data_source.pk])
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': '只支持POST请求'}, status=405)


@login_required
def get_upload_progress(request, upload_id):
    """获取上传进度（仅管理员）"""
    if not request.user.is_staff:
        return JsonResponse({'error': '只有管理员可以查看上传进度'}, status=403)
    
    try:
        progress = UploadProgress.objects.get(upload_id=upload_id, user=request.user)
        return JsonResponse({
            'status': progress.status,
            'progress': progress.progress,
            'uploaded_size': progress.uploaded_size_formatted(),
            'file_size': progress.get_file_size_formatted(),
            'upload_speed': progress.get_formatted_speed(),
            'estimated_time': progress.estimated_time,
            'error_message': progress.error_message
        })
    except UploadProgress.DoesNotExist:
        return JsonResponse({'error': '上传记录不存在'}, status=404)


def data_file_download(request, pk):
    """下载数据文件"""
    data_file = get_object_or_404(DataFile, pk=pk, is_active=True)
    
    # 检查访问权限
    if not data_file.data_source.is_public and not request.user.is_authenticated:
        messages.error(request, '请先登录以访问此文件')
        return redirect('login')
    
    # 增加下载计数
    data_file.increment_download_count()
    
    # 返回文件下载响应
    response = HttpResponse(data_file.file.read(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{data_file.file_name}"'
    return response


def data_file_detail(request, pk):
    """数据文件详情页面"""
    data_file = get_object_or_404(DataFile, pk=pk, is_active=True)
    
    # 检查访问权限
    if not data_file.data_source.is_public and not request.user.is_authenticated:
        messages.error(request, '请先登录以访问此文件')
        return redirect('blog:login')
    
    return render(request, 'blog/data_file_detail.html', {'data_file': data_file})


@login_required
def data_file_delete(request, pk):
    """删除数据文件（仅管理员）"""
    if not request.user.is_staff:
        messages.error(request, '只有管理员可以删除文件')
        return redirect('blog:data_file_detail', pk=pk)
    
    data_file = get_object_or_404(DataFile, pk=pk)
    data_source_pk = data_file.data_source.pk
    file_name = data_file.file_name
    
    # 软删除：设置is_active为False
    data_file.is_active = False
    data_file.save()
    
    messages.success(request, f'文件 "{file_name}" 已删除')
    return redirect('blog:data_source_detail', pk=data_source_pk)


# ==================== 管理员专用视图 ====================

@login_required
def admin_data_type_create(request):
    """管理员创建数据类型"""
    if not request.user.is_staff:
        messages.error(request, '只有管理员可以创建数据类型')
        return redirect('blog:data_type_list')
    
    if request.method == 'POST':
        form = DataTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '数据类型创建成功！')
            return redirect('blog:data_type_list')
    else:
        form = DataTypeForm()
    
    return render(request, 'blog/data_type_form.html', {
        'form': form,
        'title': '创建数据类型'
    })


@login_required
def admin_data_type_edit(request, pk):
    """管理员编辑数据类型"""
    if not request.user.is_staff:
        messages.error(request, '只有管理员可以编辑数据类型')
        return redirect('blog:data_type_list')
    
    data_type = get_object_or_404(DataType, pk=pk)
    
    if request.method == 'POST':
        form = DataTypeForm(request.POST, instance=data_type)
        if form.is_valid():
            form.save()
            messages.success(request, '数据类型更新成功！')
            return redirect('blog:data_type_detail', pk=pk)
    else:
        form = DataTypeForm(instance=data_type)
    
    return render(request, 'blog/data_type_form.html', {
        'form': form,
        'title': '编辑数据类型',
        'data_type': data_type
    })


from django.views.decorators.http import require_http_methods

def register(request):
    """用户注册视图"""
    if request.user.is_authenticated:
        messages.warning(request, '您已经登录，无需注册')
        return redirect('blog:image_list')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # 注册成功后自动登录
            messages.success(request, f'欢迎加入，{user.username}！')
            return redirect('blog:image_list')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

@login_required
@require_http_methods(["GET", "POST"])
def user_logout(request):
    """用户登出视图，同时支持GET和POST请求"""
    # 检查来源
    is_admin = request.path.startswith('/admin/')
    
    # 清除所有会话数据
    request.session.flush()
    
    # 调用Django的logout函数
    logout(request)
    
    # 获取next参数
    next_url = None
    if request.method == 'POST':
        next_url = request.POST.get('next')
    elif request.method == 'GET':
        next_url = request.GET.get('next')
    
    # 如果没有next参数，设置默认重定向
    if not next_url:
        if is_admin:
            next_url = '/admin/login/?next=/admin/'
        elif request.path.startswith('/accounts/'):
            next_url = '/'  # 对于accounts路径的请求，重定向到首页
        else:
            next_url = 'blog:image_list'
    
    # 添加成功消息
    if is_admin:
        messages.success(request, '您已成功退出管理后台')
    else:
        messages.success(request, '您已成功退出登录，欢迎再次访问！')
    
    # 执行重定向
    return redirect(next_url)