from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import ProcessedImage, Mask, Article, DataType, DataSource, DataFile
from .models import UserProfile

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


class DataTypeForm(forms.ModelForm):
    class Meta:
        model = DataType
        fields = ['name', 'description', 'icon', 'color']
        widgets = {
            'name': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fa-image'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }


class DataSourceForm(forms.ModelForm):
    class Meta:
        model = DataSource
        fields = ['data_type', 'source_name', 'source_description', 'contact_person', 
                 'contact_email', 'institution', 'collection_date', 'data_quality', 'is_public']
        widgets = {
            'data_type': forms.Select(attrs={'class': 'form-control'}),
            'source_name': forms.TextInput(attrs={'class': 'form-control'}),
            'source_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'institution': forms.TextInput(attrs={'class': 'form-control'}),
            'collection_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_quality': forms.Select(attrs={'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DataFileUploadForm(forms.ModelForm):
    class Meta:
        model = DataFile
        fields = ['data_source', 'file_name', 'file', 'file_type', 'file_description',
                 'patient_id', 'scan_date', 'scan_parameters', 'tags']
        widgets = {
            'data_source': forms.Select(attrs={'class': 'form-control'}),
            'file_name': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.dcm,.nii,.mat,.raw,.jpg,.jpeg,.png,.tiff'}),
            'file_type': forms.Select(attrs={'class': 'form-control'}),
            'file_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'patient_id': forms.TextInput(attrs={'class': 'form-control'}),
            'scan_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'scan_parameters': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '用逗号分隔标签'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 只显示公开的数据源
        self.fields['data_source'].queryset = DataSource.objects.filter(is_public=True)


class DataSourceSearchForm(forms.Form):
    data_type = forms.ModelChoiceField(
        queryset=DataType.objects.all(),
        required=False,
        empty_label="所有数据类型",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '搜索数据源名称、机构或描述...'
        })
    )
    quality_filter = forms.ChoiceField(
        choices=[('', '所有质量等级')] + DataSource._meta.get_field('data_quality').choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '请输入邮箱'})
    )
    identity = forms.ChoiceField(
        label='您的身份',
        choices=UserProfile.IDENTITY_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    institution = forms.CharField(
        label='您所属机构',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入所在学校/单位/公司'})
    )
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    # 其余字段在自定义表单中体现
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 添加 Bootstrap 样式
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '请输入用户名'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '请输入密码'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '请确认密码'
        })
        # 放在末尾展示身份与机构
        self.order_fields(['username', 'email', 'password1', 'password2', 'identity', 'institution'])
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        # 确保用户不是管理员
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            # 保存用户档案信息
            identity = self.cleaned_data.get('identity')
            institution = self.cleaned_data.get('institution', '')
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.identity = identity
            profile.institution = institution
            profile.save()
        return user

    # 放宽密码复杂度（降低最小长度与不强制复杂规则）
    def clean_password2(self):
        pwd1 = self.cleaned_data.get('password1')
        pwd2 = self.cleaned_data.get('password2')
        if pwd1 and pwd2 and pwd1 != pwd2:
            raise forms.ValidationError('两次输入的密码不一致')
        if pwd1 and len(pwd1) < 6:
            raise forms.ValidationError('密码长度至少为 6 位')
        return pwd2