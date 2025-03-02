from django import forms
from .models import ProcessedImage

class ImageUploadForm(forms.ModelForm):
    class Meta:
        model = ProcessedImage
        fields = ['original_image', 'model_type']  # 只包含实际存在的字段
        labels = {
            'original_image': '原始图像',
            'model_type': '模型类型'
        } 