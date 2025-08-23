from django import forms
from .models import ProcessedImage, Mask, Article

class ImageUploadForm(forms.ModelForm):
    class Meta:
        model = ProcessedImage
        fields = ['original_image', 'model_type', 'selected_mask']
        widgets = {
            'selected_mask': forms.Select(attrs={'class': 'form-control'}),
            'model_type': forms.Select(attrs={'class': 'form-control'}),
            'original_image': forms.FileInput(attrs={'class': 'form-control'})
        }
        labels = {
            'original_image': '原始图像3333',
            'model_type': '模型类型'
        }

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'summary', 'keywords', 'url', 'image', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'keywords': forms.TextInput(attrs={'class': 'form-control'}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
        } 