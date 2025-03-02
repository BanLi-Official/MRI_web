from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import ProcessedImage
from .forms import ImageUploadForm

@login_required
def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.user = request.user
            image.save()
            image.process_image()  # 处理图像
            return redirect('image_list')
    else:
        form = ImageUploadForm()
    return render(request, 'blog/upload_image.html', {'form': form})

def image_list(request):
    images = ProcessedImage.objects.all().order_by('-upload_date')
    return render(request, 'blog/image_list.html', {'images': images})

def image_detail(request, pk):
    image = ProcessedImage.objects.get(pk=pk)
    return render(request, 'blog/image_detail.html', {'image': image})

def upload_view(request):
    if request.method == 'POST':
        # 处理文件上传逻辑
        pass
    return render(request, 'upload.html') 