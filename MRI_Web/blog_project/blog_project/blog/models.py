from django.db import models
from django.contrib.auth.models import User
from PIL import Image
import os
from django.utils import timezone
import io
from django.core.files.base import ContentFile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import scipy.io as io
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 在导入 pyplot 之前设置后端
import matplotlib.pyplot as plt
import io as python_io
from django.core.files.uploadedfile import InMemoryUploadedFile

class ProcessedImage(models.Model):
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败')
    ]
    
    MODEL_CHOICES = [
        ('super_resolution', '超分辨率'),
        ('style_transfer', '风格迁移')
    ]
    
    original_image = models.FileField(upload_to='original/', verbose_name='原始图像')
    processed_image = models.FileField(upload_to='processed/', blank=True, verbose_name='处理后图像')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    processing_status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='处理状态'
    )
    model_type = models.CharField(
        max_length=50,
        choices=MODEL_CHOICES,
        default='super_resolution',
        verbose_name='模型类型'
    )
    
    # 添加新字段用于存储图像
    input_preview = models.ImageField(upload_to='previews/', blank=True, verbose_name='输入图像预览')
    output_preview = models.ImageField(upload_to='previews/', blank=True, verbose_name='输出图像预览')
    psnr_value = models.FloatField(null=True, blank=True, verbose_name='PSNR')
    ssim_value = models.FloatField(null=True, blank=True, verbose_name='SSIM')
    
    class Meta:
        verbose_name = '图像处理'
        verbose_name_plural = '图像处理'
    
    def __str__(self):
        return f"{self.original_image.name} - {self.get_processing_status_display()}"

    def save_mat_as_image(self, mat_data, field_name):
        try:
            # 创建一个新的图形
            fig = plt.figure(figsize=(8, 8))
            plt.imshow(np.abs(mat_data), cmap='gray')
            plt.axis('off')
            
            # 保存到内存
            buf = python_io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
            plt.close(fig)  # 明确关闭图形
            
            # 创建 Django 图像字段
            image_name = f"{field_name}_{self.id}.png"
            if field_name == 'input':
                self.input_preview.save(image_name, ContentFile(buf.getvalue()), save=False)
            else:
                self.output_preview.save(image_name, ContentFile(buf.getvalue()), save=False)
            
            buf.close()
        except Exception as e:
            print(f"保存图像时出错: {str(e)}")

    def process_image(self):
        try:
            print("开始处理图像...")
            self.processing_status = 'processing'
            self.save(update_fields=['processing_status'])
            
            # 读取输入 mat 文件并显示
            print(f"正在读取文件: {self.original_image.name}")
            mat_data = io.loadmat(self.original_image)['resESPIRiT_sos']
            self.save_mat_as_image(mat_data, 'input')
            
            # 准备发送到 API
            with self.original_image.open('rb') as f:
                mat_content = f.read()
            file_size = len(mat_content)
            print(f"文件大小: {file_size/1024/1024:.2f} MB")
            
            files = {
                'file': (
                    os.path.basename(self.original_image.name),
                    mat_content,
                    'application/octet-stream'
                )
            }
            
            api_url = 'https://7eca-220-175-48-224.ngrok-free.app/process_image/super_resolution'
            print(f"准备调用 API: {api_url}")
            
            session = requests.Session()
            session.verify = False
            
            print("开始发送请求...")
            response = session.post(
                api_url,
                files=files,
                timeout=(30, 300)
            )
            
            print(f"API 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                print("请求成功，正在处理响应...")
                # 保存评价指标
                self.psnr_value = float(response.headers.get('X-PSNR', 0))
                self.ssim_value = float(response.headers.get('X-SSIM', 0))
                
                # 保存处理后的 mat 文件
                output_filename = f'processed_{self.model_type}_{os.path.basename(self.original_image.name)}'
                self.processed_image.save(
                    output_filename,
                    ContentFile(response.content),
                    save=False
                )
                
                # 显示处理后的图像
                output_mat = io.loadmat(python_io.BytesIO(response.content))
                self.save_mat_as_image(output_mat['rec_Image_sos'], 'output')
                
                self.processing_status = 'completed'
                print(f"处理完成 - PSNR: {self.psnr_value}, SSIM: {self.ssim_value}")
                
            else:
                raise Exception(f"API 返回错误: {response.status_code}")
                
        except Exception as e:
            print(f"处理出错: {str(e)}")
            print(f"错误类型: {type(e)}")
            self.processing_status = 'failed'
        finally:
            self.save()

    def save(self, *args, **kwargs):
        if not self.pk and not self.processed_image:  # 新创建的实例
            super().save(*args, **kwargs)
            self.process_image()
        else:
            super().save(*args, **kwargs)

class Article(models.Model):
    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容')
    created_time = models.DateTimeField('创建时间', default=timezone.now)
    modified_time = models.DateTimeField('修改时间', auto_now=True)

    class Meta:
        verbose_name = '文章'
        verbose_name_plural = verbose_name
        ordering = ['-created_time']

    def __str__(self):
        return self.title 