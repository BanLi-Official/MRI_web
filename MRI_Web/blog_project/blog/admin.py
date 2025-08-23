from django.contrib import admin
from .models import Article
from django.utils.html import format_html
from .models import ProcessedImage, Mask
import os

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_time', 'modified_time')
    list_filter = ('created_time',)
    search_fields = ('title', 'content')
    date_hierarchy = 'created_time'

@admin.register(Mask)
class MaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description')
        }),
        ('Mask文件', {
            'fields': ('mask_file',)
        }),
        ('时间信息', {
            'fields': ('created_at',)
        }),
    )

@admin.register(ProcessedImage)
class ProcessedImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_image_preview', 'zero_filled_image_preview', 'reconstructed_preview', 
                   'psnr_value', 'ssim_value', 'processing_status', 'created_at')
    readonly_fields = ('psnr_value', 'ssim_value', 'processing_status', 'created_at', 'all_previews')
    list_filter = ('processing_status', 'created_at')
    search_fields = ('id',)
    
    def original_image_preview(self, obj):
        if obj.input_preview:
            return format_html('<img src="{}" width="100" height="100" />', obj.input_preview.url)
        return "无图像"
    original_image_preview.short_description = '原始图像11'
    original_image_preview.allow_tags = True
    
    def zero_filled_image_preview(self, obj):
        if obj.zero_filled_preview:
            return format_html('<img src="{}" width="100" height="100" />', obj.zero_filled_preview.url)
        return "无图像"
    zero_filled_image_preview.short_description = '零填充图像'
    zero_filled_image_preview.allow_tags = True
    
    def reconstructed_preview(self, obj):
        if obj.output_preview:
            return format_html('<img src="{}" width="100" height="100" />', obj.output_preview.url)
        return "无图像"
    reconstructed_preview.short_description = '重建图像'
    reconstructed_preview.allow_tags = True

    def all_previews(self, obj):
        imgs = []
        if obj.input_preview:
            imgs.append(f'<div style="text-align:center;"><div>输入图像</div><img src="{obj.input_preview.url}" width="400" /></div>')
        if obj.zero_filled_preview:
            imgs.append(f'<div style="text-align:center;"><div>零填充图像</div><img src="{obj.zero_filled_preview.url}" width="400" /></div>')
        if obj.output_preview:
            imgs.append(f'<div style="text-align:center;"><div>输出图像</div><img src="{obj.output_preview.url}" width="400" /></div>')
        return format_html(
            '<div style="display:flex;gap:30px;justify-content:center;">{}</div>',
            format_html(''.join(imgs))
        )
    all_previews.short_description = '图像预览'

    exclude = ('processed_image','input_preview', 'output_preview', 'zero_filled_preview')

