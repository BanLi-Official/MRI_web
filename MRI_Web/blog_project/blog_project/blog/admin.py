from django.contrib import admin
from .models import Article
from django.utils.html import format_html
from .models import ProcessedImage
import os

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_time', 'modified_time')
    list_filter = ('created_time',)
    search_fields = ('title', 'content')
    date_hierarchy = 'created_time'

@admin.register(ProcessedImage)
class ProcessedImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'original_image_name', 'status_with_color', 'created_at']
    list_filter = ['processing_status', 'model_type', 'created_at']
    readonly_fields = ['processing_status', 'created_at', 'processed_image', 
                      'image_preview', 'metrics_display']
    
    def original_image_name(self, obj):
        return os.path.basename(obj.original_image.name)
    original_image_name.short_description = '原始图像'
    
    def status_with_color(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.processing_status, 'black'),
            obj.get_processing_status_display()
        )
    status_with_color.short_description = '状态'
    
    def image_preview(self, obj):
        if obj.input_preview and obj.output_preview:
            return format_html(
                '<div style="display: flex; gap: 20px;">'
                '<div><p>输入图像:</p><img src="{}" style="max-width: 300px;"/></div>'
                '<div><p>输出图像:</p><img src="{}" style="max-width: 300px;"/></div>'
                '</div>',
                obj.input_preview.url,
                obj.output_preview.url
            )
        elif obj.input_preview:
            return format_html(
                '<div><p>输入图像:</p><img src="{}" style="max-width: 300px;"/></div>',
                obj.input_preview.url
            )
        return "无图像预览"
    
    def metrics_display(self, obj):
        if obj.psnr_value is not None and obj.ssim_value is not None:
            return format_html(
                '<div style="margin-top: 10px;">'
                '<p>PSNR: {:.2f}</p>'
                '<p>SSIM: {:.4f}</p>'
                '</div>',
                obj.psnr_value,
                obj.ssim_value
            )
        return "无评价指标"
    
    image_preview.short_description = '图像预览'
    metrics_display.short_description = '评价指标'
