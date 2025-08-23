from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ProcessedImage, Mask, Article
from .forms import ImageUploadForm, ArticleForm
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
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            processed_image = form.save()
            # 这里可以推送异步任务
            # from .tasks import process_image_task
            # process_image_task.delay(processed_image.pk)
            return redirect('blog:image_list')  # 立即返回列表页
    else:
        form = ImageUploadForm()
    return render(request, 'blog/upload_image.html', {'form': form})

def image_list(request):
    images = ProcessedImage.objects.all().order_by('-created_at')
    return render(request, 'blog/image_list.html', {'images': images})

def image_detail(request, pk):
    processed_image = get_object_or_404(ProcessedImage, pk=pk)
    return render(request, 'blog/image_detail.html', {'processed_image': processed_image})

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
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save()
            return redirect(reverse('blog:article_detail', args=[article.pk]))
    else:
        form = ArticleForm()
    return render(request, 'blog/article_upload.html', {'form': form})

def article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk)
    return render(request, 'blog/article_detail.html', {'article': article})

def article_list(request):
    articles = Article.objects.all().order_by('-created_time')
    return render(request, 'blog/article_list.html', {'articles': articles}) 