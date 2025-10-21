from django.contrib import admin
from .models import Article, ProcessedImage, Mask, DataType, DataSource, DataFile, UploadProgress, UserProfile
from django.utils.html import format_html
import os
from django.contrib.auth.models import User
from django.contrib import admin as dj_admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
 

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


# ==================== 数据管理系统Admin配置 ====================

@admin.register(DataType)
class DataTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon_display', 'color_display', 'source_count', 'file_count', 'created_at')
    list_filter = ('name', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description')
        }),
        ('显示设置', {
            'fields': ('icon', 'color')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def icon_display(self, obj):
        return format_html('<i class="{} fa-lg"></i> {}', obj.icon, obj.icon)
    icon_display.short_description = '图标'
    
    def color_display(self, obj):
        return format_html('<span style="color: {};">●</span> {}', obj.color, obj.color)
    color_display.short_description = '颜色'
    
    def source_count(self, obj):
        return obj.get_source_count()
    source_count.short_description = '数据源数量'
    
    def file_count(self, obj):
        return obj.get_file_count()
    file_count.short_description = '文件数量'


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('source_name', 'data_type', 'institution', 'data_quality', 'is_public', 'file_count_display', 'created_at')
    list_filter = ('data_type', 'data_quality', 'is_public', 'created_at')
    search_fields = ('source_name', 'source_description', 'institution', 'contact_person')
    readonly_fields = ('created_at', 'updated_at', 'file_count_display', 'total_size_display')
    fieldsets = (
        ('基本信息', {
            'fields': ('data_type', 'source_name', 'source_description')
        }),
        ('联系信息', {
            'fields': ('contact_person', 'contact_email', 'institution')
        }),
        ('数据信息', {
            'fields': ('collection_date', 'data_quality', 'is_public')
        }),
        ('统计信息', {
            'fields': ('file_count_display', 'total_size_display'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_count_display(self, obj):
        return obj.get_file_count()
    file_count_display.short_description = '文件数量'
    
    def total_size_display(self, obj):
        return obj.get_formatted_size()
    total_size_display.short_description = '总大小'


@admin.register(DataFile)
class DataFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'data_source', 'file_type', 'file_size_display', 'download_count', 'is_active', 'created_at')
    list_filter = ('file_type', 'is_active', 'created_at', 'data_source__data_type')
    search_fields = ('file_name', 'file_description', 'patient_id', 'tags')
    readonly_fields = ('file_size', 'download_count', 'created_at', 'updated_at')
    fieldsets = (
        ('基本信息', {
            'fields': ('data_source', 'file_name', 'file', 'file_type')
        }),
        ('医学信息', {
            'fields': ('patient_id', 'scan_date', 'scan_parameters'),
            'classes': ('collapse',)
        }),
        ('描述信息', {
            'fields': ('file_description', 'tags')
        }),
        ('统计信息', {
            'fields': ('file_size', 'download_count', 'is_active'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        return obj.get_formatted_size()
    file_size_display.short_description = '文件大小'
    
    def save_model(self, request, obj, form, change):
        # 自动设置上传者
        if not change:  # 新建时
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UploadProgress)
class UploadProgressAdmin(admin.ModelAdmin):
    list_display = ('filename', 'user', 'status', 'progress_display', 'upload_speed_display', 'created_at')
    list_filter = ('status', 'created_at', 'user')
    search_fields = ('filename', 'upload_id', 'user__username')
    readonly_fields = ('upload_id', 'file_size', 'uploaded_size', 'progress', 'upload_speed', 'estimated_time', 'created_at', 'updated_at')
    fieldsets = (
        ('基本信息', {
            'fields': ('upload_id', 'user', 'filename', 'status')
        }),
        ('进度信息', {
            'fields': ('file_size', 'uploaded_size', 'progress', 'upload_speed', 'estimated_time')
        }),
        ('错误信息', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def progress_display(self, obj):
        return f"{obj.progress:.1f}%"
    progress_display.short_description = '进度'
    
    def upload_speed_display(self, obj):
        return obj.get_formatted_speed()
    upload_speed_display.short_description = '上传速度'
    
    def has_add_permission(self, request):
        return False  # 不允许手动添加上传进度记录


# ========== 用户档案与统计 ==========
class UserProfileInline(dj_admin.StackedInline):
    model = UserProfile
    can_delete = False
    fk_name = 'user'
    extra = 0
    fields = ('identity', 'institution')


class CustomUserAdmin(AuthUserAdmin):
    list_display = ('username', 'email', 'is_staff', 'date_joined', 'last_login', 'get_identity', 'get_institution')
    search_fields = ('username', 'email', 'userprofile__institution')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    inlines = [UserProfileInline]

    def get_identity(self, obj):
        if hasattr(obj, 'userprofile') and obj.userprofile.identity:
            return obj.userprofile.get_identity_display()
        return '*'
    get_identity.short_description = '身份'
    get_identity.admin_order_field = 'userprofile__identity'

    def get_institution(self, obj):
        if hasattr(obj, 'userprofile') and obj.userprofile.institution:
            return obj.userprofile.institution
        return '*'
    get_institution.short_description = '所属机构'
    get_institution.admin_order_field = 'userprofile__institution'

    class Media:
        css = {
            'all': (
                'admin/custom_user_columns.css',
            )
        }

    # 使用默认的变更列表视图（不显示自定义统计）

# 替换系统内置的 User Admin
try:
    dj_admin.site.unregister(User)
except dj_admin.sites.NotRegistered:
    pass
dj_admin.site.register(User, CustomUserAdmin)

