from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
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

class Mask(models.Model):
    name = models.CharField('名称', max_length=200)
    description = models.TextField('描述', blank=True)
    mask_file = models.FileField('Mask文件', upload_to='masks/')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '欠采样Mask'
        verbose_name_plural = '欠采样Mask'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class ProcessedImage(models.Model):
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败')
    ]
    
    MODEL_CHOICES = [
        ('super_resolution', 'DFAM'),
        ('style_transfer', 'WKGM')
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
    selected_mask = models.ForeignKey(Mask, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='选择的Mask')
    
    # 添加新字段用于存储图像
    input_preview = models.ImageField(upload_to='previews/', blank=True, verbose_name='输入图像预览')
    output_preview = models.ImageField(upload_to='previews/', blank=True, verbose_name='输出图像预览')
    zero_filled_preview = models.ImageField(upload_to='previews/', blank=True, verbose_name='零填充图像预览')
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
            elif field_name == 'zero_filled':
                self.zero_filled_preview.save(image_name, ContentFile(buf.getvalue()), save=False)
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
            #mat_data = io.loadmat(self.original_image)['resESPIRiT_sos']
            mat_content = io.loadmat(self.original_image)
            print("读取成功")


            # 过滤掉 MATLAB 自带的元数据
            valid_keys = [key for key in mat_content if not key.startswith('__')]
            print("过滤成功")
            # 如果有有效 key，返回第一个；否则返回空字典或抛出异常
            if valid_keys:
                first_key = valid_keys[0]
                mat_data = mat_content[first_key]
            else:
                raise ValueError("MAT 文件中没有找到有效数据变量！")
            
            print("保存成功")

            self.save_mat_as_image(mat_data, 'input')
            
            # 准备发送到 API
            with self.original_image.open('rb') as f:
                mat_content = f.read()
            file_size = len(mat_content)
            print(f"文件大小: {file_size/1024/1024:.2f} MB")
            
            files = {
                'image': (
                    os.path.basename(self.original_image.name),
                    mat_content,
                    'application/octet-stream'
                )
            }
            data = {
                'model_type': self.model_type
            }
            if self.selected_mask:
                with self.selected_mask.mask_file.open('rb') as mask_f:
                    files['mask'] = (
                        os.path.basename(self.selected_mask.mask_file.name),
                        mask_f.read(),
                        'application/octet-stream'
                    )
            
            # 根据模型类型选择API配置
            from django.conf import settings
            api_config = settings.API_CONFIG.get(self.model_type, {})
            api_url = api_config.get('url', 'https://b94989ab90bb.ngrok-free.app/process/')
            timeout = api_config.get('timeout', (300, 300))
            description = api_config.get('description', '默认API')
            
            print(f"模型类型: {self.model_type}")
            print(f"API描述: {description}")
            print(f"准备调用 API: {api_url}")
            print(f"超时设置: {timeout}")
            
            session = requests.Session()
            session.verify = False
            
            print("开始发送请求...")
            try:
                response = session.post(
                    api_url,
                    files=files,
                    data=data,
                    timeout=timeout
                )
                print(f"API 响应状态码: {response.status_code}")
            except requests.exceptions.Timeout:
                print(f"API请求超时: {api_url}")
                raise Exception(f"API请求超时: {description}")
            except requests.exceptions.ConnectionError:
                print(f"无法连接到API: {api_url}")
                raise Exception(f"无法连接到API: {description}")
            except Exception as e:
                print(f"API请求失败: {str(e)}")
                raise Exception(f"API请求失败: {description} - {str(e)}")
            
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
                try:
                    output_mat = io.loadmat(python_io.BytesIO(response.content))
                    if 'zeorfilled_data_sos' not in output_mat:
                        print("警告：返回的数据中没有 zeorfilled_data_sos")
                        print("可用的键：", output_mat.keys())
                    else:
                        print("成功读取 zeorfilled_data_sos，形状：", output_mat['zeorfilled_data_sos'].shape)
                        self.save_mat_as_image(output_mat['zeorfilled_data_sos'], 'zero_filled')
                        self.save()  # 保存零填充图像
                    
                    if 'rec_Image_sos' not in output_mat:
                        print("警告：返回的数据中没有 rec_Image_sos")
                        print("可用的键：", output_mat.keys())
                    else:
                        print("成功读取 rec_Image_sos，形状：", output_mat['rec_Image_sos'].shape)
                        self.save_mat_as_image(output_mat['rec_Image_sos'], 'output')
                        self.save()  # 保存重建图像
                except Exception as e:
                    print(f"处理图像时出错: {str(e)}")
                    print(f"错误类型: {type(e)}")
                    print("可用的键：", output_mat.keys() if 'output_mat' in locals() else "无法读取mat文件")
                
                self.processing_status = 'completed'
                print(f"处理完成 - PSNR: {self.psnr_value}, SSIM: {self.ssim_value}")
                
            else:
                error_msg = f"API 返回错误: {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                raise Exception(error_msg)
                
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
    summary = models.TextField('摘要', blank=True)
    keywords = models.CharField('关键字', max_length=200, blank=True, help_text='用逗号分隔多个关键字')
    url = models.URLField('网站连接', blank=True)
    image = models.ImageField('文章图片', upload_to='article_images/', blank=True, null=True)
    content = models.TextField('内容')
    created_time = models.DateTimeField('创建时间', default=timezone.now)
    modified_time = models.DateTimeField('修改时间', auto_now=True)

    class Meta:
        verbose_name = '文章'
        verbose_name_plural = verbose_name
        ordering = ['-created_time']

    def __str__(self):
        return self.title


# 数据类型模型（第一层：MRI、PET、CT等）
class DataType(models.Model):
    TYPE_CHOICES = [
        ('mri', 'MRI'),
        ('pet', 'PET'),
        ('ct', 'CT'),
        ('ultrasound', '超声'),
        ('xray', 'X光'),
        ('other', '其他'),
    ]
    
    name = models.CharField('数据类型', max_length=50, choices=TYPE_CHOICES, unique=True)
    description = models.TextField('类型描述', blank=True, help_text='介绍该数据类型的特点和应用场景')
    icon = models.CharField('图标', max_length=50, default='fa-image', help_text='FontAwesome图标名称')
    color = models.CharField('主题色', max_length=7, default='#007bff', help_text='十六进制颜色代码')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '数据类型'
        verbose_name_plural = '数据类型'
        ordering = ['name']
    
    def __str__(self):
        return self.get_name_display()
    
    def get_file_count(self):
        """获取该类型下的文件总数"""
        return DataFile.objects.filter(data_source__data_type=self).count()
    
    def get_source_count(self):
        """获取该类型下的数据源总数"""
        return DataSource.objects.filter(data_type=self).count()


# 数据源模型（第二层：按数据来源分组）
class DataSource(models.Model):
    data_type = models.ForeignKey(DataType, on_delete=models.CASCADE, verbose_name='数据类型')
    source_name = models.CharField('数据源名称', max_length=200, help_text='如：医院A、研究机构B等')
    source_description = models.TextField('数据源描述', blank=True, help_text='详细介绍该数据源的背景信息')
    contact_person = models.CharField('联系人', max_length=100, blank=True)
    contact_email = models.EmailField('联系邮箱', blank=True)
    institution = models.CharField('机构名称', max_length=200, blank=True)
    collection_date = models.DateField('收集日期', null=True, blank=True)
    data_quality = models.CharField('数据质量', max_length=50, choices=[
        ('excellent', '优秀'),
        ('good', '良好'),
        ('fair', '一般'),
        ('poor', '较差'),
    ], default='good')
    is_public = models.BooleanField('公开访问', default=True, help_text='是否允许所有用户访问')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='创建者')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '数据源'
        verbose_name_plural = '数据源'
        ordering = ['-created_at']
        unique_together = ['data_type', 'source_name']
    
    def __str__(self):
        return f"{self.data_type.get_name_display()} - {self.source_name}"
    
    def get_file_count(self):
        """获取该数据源下的文件总数"""
        return self.datafile_set.count()
    
    def get_total_size(self):
        """获取该数据源下的文件总大小"""
        total_size = 0
        for file in self.datafile_set.all():
            if file.file:
                try:
                    total_size += file.file.size
                except:
                    pass
        return total_size
    
    def get_formatted_size(self):
        """获取格式化的文件大小"""
        size = self.get_total_size()
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"


# 数据文件模型（存储实际文件）
class DataFile(models.Model):
    FILE_TYPE_CHOICES = [
        ('dicom', 'DICOM'),
        ('nifti', 'NIfTI'),
        ('mat', 'MATLAB'),
        ('raw', '原始数据'),
        ('image', '图像文件'),
        ('other', '其他'),
    ]
    
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, verbose_name='数据源')
    file_name = models.CharField('文件名', max_length=255)
    file = models.FileField('文件', upload_to='data_files/', help_text='支持DICOM、NIfTI、MAT等格式')
    file_type = models.CharField('文件类型', max_length=20, choices=FILE_TYPE_CHOICES, default='other')
    file_size = models.BigIntegerField('文件大小', default=0, help_text='字节')
    file_description = models.TextField('文件描述', blank=True)
    patient_id = models.CharField('患者ID', max_length=100, blank=True, help_text='匿名化患者标识')
    scan_date = models.DateTimeField('扫描日期', null=True, blank=True)
    scan_parameters = models.TextField('扫描参数', blank=True, help_text='如：TR、TE、层厚等参数信息')
    tags = models.CharField('标签', max_length=500, blank=True, help_text='用逗号分隔的标签')
    download_count = models.PositiveIntegerField('下载次数', default=0)
    is_active = models.BooleanField('激活状态', default=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='上传者')
    created_at = models.DateTimeField('上传时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '数据文件'
        verbose_name_plural = '数据文件'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.file_name} ({self.data_source})"
    
    def save(self, *args, **kwargs):
        # 自动计算文件大小
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    def get_formatted_size(self):
        """获取格式化的文件大小"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def increment_download_count(self):
        """增加下载计数"""
        self.download_count += 1
        self.save(update_fields=['download_count'])


# 文件上传进度跟踪模型
class UploadProgress(models.Model):
    STATUS_CHOICES = [
        ('uploading', '上传中'),
        ('processing', '处理中'),
        ('completed', '完成'),
        ('failed', '失败'),
    ]
    
    upload_id = models.CharField('上传ID', max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    filename = models.CharField('文件名', max_length=255)
    file_size = models.BigIntegerField('文件大小', default=0)
    uploaded_size = models.BigIntegerField('已上传大小', default=0)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='uploading')
    progress = models.FloatField('进度百分比', default=0.0)
    upload_speed = models.FloatField('上传速度', default=0.0, help_text='KB/s')
    estimated_time = models.IntegerField('预计剩余时间', default=0, help_text='秒')
    error_message = models.TextField('错误信息', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '上传进度'
        verbose_name_plural = '上传进度'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.filename} - {self.get_status_display()}"
    
    def update_progress(self, uploaded_size):
        """更新上传进度"""
        self.uploaded_size = uploaded_size
        if self.file_size > 0:
            self.progress = (uploaded_size / self.file_size) * 100
        
        # 计算上传速度
        time_elapsed = (timezone.now() - self.created_at).total_seconds()
        if time_elapsed > 0:
            self.upload_speed = (uploaded_size / 1024) / time_elapsed  # KB/s
            
            # 计算预计剩余时间
            if self.upload_speed > 0:
                remaining_bytes = self.file_size - uploaded_size
                self.estimated_time = int((remaining_bytes / 1024) / self.upload_speed)
        
        self.save(update_fields=['uploaded_size', 'progress', 'upload_speed', 'estimated_time', 'updated_at'])
    
    def get_formatted_speed(self):
        """获取格式化的上传速度"""
        if self.upload_speed < 1024:
            return f"{self.upload_speed:.1f} KB/s"
        else:
            return f"{self.upload_speed/1024:.1f} MB/s"
    
    def get_formatted_size(self, size_bytes):
        """获取格式化的文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def get_uploaded_size_formatted(self):
        """获取已上传大小的格式化显示"""
        return self.get_formatted_size(self.uploaded_size)
    
    def get_file_size_formatted(self):
        """获取文件大小的格式化显示"""
        return self.get_formatted_size(self.file_size)


# ========== 用户扩展信息（注册填写：身份/机构） ==========
class UserProfile(models.Model):
    IDENTITY_CHOICES = [
        ('student', '学生'),
        ('researcher', '研究者'),
        ('employee', '企业员工'),
        ('hobbyist', '爱好者'),
        ('other', '其他'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile', verbose_name='用户')
    identity = models.CharField('身份', max_length=20, choices=IDENTITY_CHOICES, default='student')
    institution = models.CharField('所属机构', max_length=255, blank=True)

    class Meta:
        verbose_name = '用户档案'
        verbose_name_plural = '用户档案'

    def __str__(self):
        return f"{self.user.username} - {self.get_identity_display()} - {self.institution or '未填写'}"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """自动为新用户创建档案，或在保存时确保存在。"""
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # 确保老用户也有档案
        UserProfile.objects.get_or_create(user=instance)